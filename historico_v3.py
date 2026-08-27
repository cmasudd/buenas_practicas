"""Blueprint V3 para consultar y descargar históricos por dispositivo.

Este módulo no reemplaza rutas legacy. Se registra con un prefijo /v3 y usa:

* filtros obligatorios por dispositivo y fecha;
* paginación keyset por (id_sensor, fecha, id_dato);
* lotes pequeños y acotados;
* streaming NDJSON con checkpoints reanudables.
"""

from __future__ import annotations

import base64
import calendar
import csv
import fcntl
import hashlib
import heapq
import io
import itertools
import json
import os
import re
import secrets
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Iterator

import decimal
import mysql.connector
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash
from portal_users import (
    DuplicatePortalUserError,
    LastAdministratorError,
    PortalUserError,
    authenticate_user as authenticate_portal_user,
    create_user as create_portal_user,
    get_user_by_email,
    list_users as list_portal_users,
    update_user as update_portal_user,
)
from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
    stream_with_context,
)


DEFAULT_PAGE_SIZE = 500
MAX_PAGE_SIZE = 1000
SESSION_COOKIE = "historico_session"
SESSION_MAX_AGE = 8 * 60 * 60
EXPORT_LOCK_PATH = "/tmp/api-sensores-historico.lock"
POWERBI_LOCK_PATH = "/tmp/api-sensores-powerbi.lock"
MAX_POWERBI_PROJECT_DEVICES = 25
MICROSOFT_JWKS_URL = (
    "https://login.microsoftonline.com/common/discovery/v2.0/keys"
)
DEFAULT_MICROSOFT_CLIENT_ID = "8e94a7e7-a878-4e6d-9021-8231737ebec5"
WIDE_BASE_COLUMNS = [
    "fecha",
    "fecha_insercion",
    "id_sesion",
    "sesion_descripcion",
    "fecha_inicio",
    "ubicacion",
    "id_proyecto",
    "codigo_interno",
    "dispositivo_descripcion",
]


def _encode_cursor(id_sensor: int, fecha: datetime | str, id_dato: int) -> str:
    value = fecha.isoformat() if isinstance(fecha, datetime) else str(fecha)
    payload = json.dumps(
        [int(id_sensor), value, int(id_dato)],
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(value: str | None) -> tuple[int, datetime, int] | None:
    if not value:
        return None
    try:
        padding = "=" * (-len(value) % 4)
        id_sensor, fecha, id_dato = json.loads(
            base64.urlsafe_b64decode(value + padding).decode()
        )
        return int(id_sensor), datetime.fromisoformat(fecha), int(id_dato)
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("cursor inválido") from error


def _preview_row_key(row: dict[str, Any]) -> tuple[str, ...]:
    """Clave estable para ordenar y paginar filas anchas recientes."""
    return (
        str(_serialize(row.get("fecha"))),
        str(_serialize(row.get("codigo_interno"))),
        str(_serialize(row.get("fecha_insercion"))),
        str(_serialize(row.get("id_sesion"))),
        str(_serialize(row.get("id_dato_concatenado"))),
    )


def _encode_preview_cursor(row: dict[str, Any]) -> str:
    payload = json.dumps(
        list(_preview_row_key(row)),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_preview_cursor(value: str | None) -> tuple[str, ...] | None:
    if not value:
        return None
    try:
        padding = "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(value + padding).decode())
        if (
            not isinstance(payload, list)
            or len(payload) != 5
            or not all(isinstance(item, str) for item in payload)
        ):
            raise ValueError
        datetime.fromisoformat(payload[0])
        return tuple(payload)
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("cursor de vista previa inválido") from error


def _parse_date(value: str | None, field: str) -> date:
    if not value:
        raise ValueError(f"{field} es obligatorio")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError(f"{field} debe usar YYYY-MM-DD") from error


def _serialize(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    return str(value)


def _safe_filename_part(value: Any) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-._")
    return cleaned or "dispositivo"


def _api_key_matches(provided: str, expected_hash: str) -> bool:
    """Compara una API key con su SHA-256 sin guardar el secreto en código."""
    if not provided or len(provided) > 256:
        return False
    normalized_hash = expected_hash.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized_hash):
        return False
    calculated_hash = hashlib.sha256(provided.encode("utf-8")).hexdigest()
    return secrets.compare_digest(calculated_hash, normalized_hash)


def _validate_microsoft_issuer(claims: dict[str, Any]) -> None:
    """Valida que el emisor corresponda exactamente al tenant del token."""
    tenant_id = str(claims.get("tid", ""))
    try:
        uuid.UUID(tenant_id)
    except ValueError as error:
        raise ValueError("tenant de Microsoft inválido") from error

    version = str(claims.get("ver", "2.0"))
    expected = (
        f"https://sts.windows.net/{tenant_id}/"
        if version == "1.0"
        else f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    )
    if not secrets.compare_digest(str(claims.get("iss", "")), expected):
        raise ValueError("emisor de Microsoft inválido")


def _descending_row_key(row: dict[str, Any], stream_index: int) -> tuple[Any, ...]:
    return (-row["fecha"].timestamp(), -int(row["id_dato"]), stream_index)


def _merge_wide_rows(
    streams: list[Iterator[dict[str, Any]]],
    device: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    """Fusiona series indexadas por sensor y pivota una fecha a una fila."""
    heap: list[tuple[Any, ...]] = []
    for stream_index, stream in enumerate(streams):
        row = next(stream, None)
        if row is not None:
            heapq.heappush(
                heap,
                (*_descending_row_key(row, stream_index), row, stream),
            )

    while heap:
        current_date = heap[0][3]["fecha"]
        same_date: list[dict[str, Any]] = []
        while heap and heap[0][3]["fecha"] == current_date:
            _, _, stream_index, row, stream = heapq.heappop(heap)
            same_date.append(row)
            following = next(stream, None)
            if following is not None:
                heapq.heappush(
                    heap,
                    (*_descending_row_key(following, stream_index), following, stream),
                )

        groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for row in same_date:
            group_key = (
                row["fecha"],
                row.get("fecha_insercion"),
                row.get("id_sesion") or "Sin sesión",
                row.get("sesion_descripcion") or "",
                row.get("fecha_inicio") or "",
                row.get("ubicacion") or "",
            )
            groups.setdefault(group_key, []).append(row)

        for group_key in sorted(
            groups,
            key=lambda key: tuple(str(_serialize(value)) for value in key),
            reverse=True,
        ):
            rows = groups[group_key]
            output: dict[str, Any] = {
                "fecha": group_key[0],
                "fecha_insercion": group_key[1] or "",
                "id_sesion": group_key[2],
                "sesion_descripcion": group_key[3],
                "fecha_inicio": group_key[4],
                "ubicacion": group_key[5],
                "id_proyecto": device["id_proyecto"],
                "codigo_interno": device["codigo_interno"],
                "dispositivo_descripcion": device.get("descripcion") or "",
            }
            values: dict[str, list[Any]] = {}
            for row in rows:
                column = row.get("unidad_medida") or (
                    f"Sensor {row['id_sensor']} "
                    f"[Variable {row['id_variable']}]"
                )
                values.setdefault(column, []).append(row["valor"])
            for column, column_values in values.items():
                output[column] = ", ".join(
                    str(_serialize(value)) for value in column_values
                )
            output["id_dato_concatenado"] = ", ".join(
                str(row["id_dato"]) for row in rows
            )
            yield output


def create_historico_v3_blueprint(db_config: dict[str, Any]) -> Blueprint:
    blueprint = Blueprint("historico_v3", __name__, url_prefix="/v3")
    microsoft_jwks = PyJWKClient(
        MICROSOFT_JWKS_URL,
        lifespan=24 * 60 * 60,
        timeout=5,
    )

    def connect():
        connection = mysql.connector.connect(**db_config)
        connection.autocommit = True
        return connection

    def serializer() -> URLSafeTimedSerializer:
        secret = os.getenv("HISTORICO_SESSION_SECRET")
        if not secret:
            raise RuntimeError("HISTORICO_SESSION_SECRET no configurado")
        return URLSafeTimedSerializer(secret, salt="historico-v3")

    def authenticated_identity() -> dict[str, str] | None:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        try:
            payload = serializer().loads(token, max_age=SESSION_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return None
        if not isinstance(payload, dict):
            return None
        username = payload.get("sub")
        if not isinstance(username, str):
            return None
        provider = str(payload.get("provider") or "local")
        role = str(payload.get("role") or (
            "administrador" if provider == "microsoft" else "visita"
        ))
        if role not in {"visita", "administrador"}:
            role = "visita"
        return {"username": username, "provider": provider, "role": role}

    def authenticated_user() -> str | None:
        identity = authenticated_identity()
        return identity["username"] if identity else None

    def require_authentication():
        username = authenticated_user()
        if username:
            return username, None
        return None, (
            jsonify({"status": "fail", "error": "autenticación requerida"}),
            401,
        )

    def require_administrator():
        identity = authenticated_identity()
        if not identity:
            return None, (
                jsonify({"status": "fail", "error": "autenticación requerida"}),
                401,
            )
        if identity["role"] != "administrador":
            return None, (
                jsonify({"status": "fail", "error": "permiso de administrador requerido"}),
                403,
            )
        return identity, None

    def require_powerbi_api_key():
        expected_hash = os.getenv("POWERBI_API_KEY_HASH", "")
        if not expected_hash:
            current_app.logger.error("POWERBI_API_KEY_HASH no configurado")
            return jsonify({
                "status": "fail",
                "error": "integración Power BI no configurada",
            }), 503
        provided = request.headers.get("X-API-Key", "")
        if not _api_key_matches(provided, expected_hash):
            return jsonify({
                "status": "fail",
                "error": "credencial Power BI inválida",
            }), 401
        return None

    def session_response(
        username: str,
        provider: str = "local",
        role: str = "visita",
    ) -> Response:
        token = serializer().dumps({
            "sub": username,
            "provider": provider,
            "role": role,
        })
        response = jsonify({
            "status": "success",
            "user": username,
            "provider": provider,
            "role": role,
        })
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=SESSION_MAX_AGE,
            secure=True,
            httponly=True,
            samesite="Strict",
            path="/v3",
        )
        return response

    @blueprint.post("/auth/login")
    def login():
        """Inicia una sesión local para descargas históricas V3.
        ---
        tags:
          - V3 - Autenticación
        summary: Iniciar sesión para descargas V3
        description: >
          Valida las credenciales configuradas por el administrador y crea una
          cookie segura. La contraseña nunca debe incluirse en la URL.
        consumes:
          - application/json
        produces:
          - application/json
        parameters:
          - in: body
            name: credenciales
            required: true
            schema:
              type: object
              required: [username, password]
              properties:
                username:
                  type: string
                  example: usuario
                password:
                  type: string
                  format: password
                  example: su-contraseña
        responses:
          200:
            description: Sesión iniciada; el navegador recibe una cookie segura.
          401:
            description: Credenciales inválidas.
        """
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", ""))
        password = str(payload.get("password", ""))
        portal_user = None
        connection = connect()
        try:
            portal_user = authenticate_portal_user(connection, username, password)
        finally:
            connection.close()
        if portal_user:
            return session_response(
                portal_user["email"],
                role=portal_user["rol"],
            )

        expected_user = os.getenv("HISTORICO_USER", "")
        password_hash = os.getenv("HISTORICO_PASSWORD_HASH", "")
        legacy_valid = (
            bool(expected_user)
            and bool(password_hash)
            and secrets.compare_digest(username, expected_user)
            and check_password_hash(password_hash, password)
        )
        if not legacy_valid:
            return jsonify({"status": "fail", "error": "credenciales inválidas"}), 401

        # El acceso local heredado conserva sus credenciales por compatibilidad,
        # pero no debe presentarse en el portal con el nombre "admin".
        return session_response("visita", role="visita")

    @blueprint.post("/auth/microsoft")
    def microsoft_login():
        """Intercambia un ID token Microsoft por una sesión V3.
        ---
        tags:
          - V3 - Autenticación
        summary: Iniciar sesión V3 con Microsoft
        description: >
          Valida firma, audiencia, emisor y vencimiento del ID token. Está
          pensada para el portal web; no se debe pegar un token real en Swagger.
        consumes:
          - application/json
        produces:
          - application/json
        parameters:
          - in: body
            name: token
            required: true
            schema:
              type: object
              required: [id_token]
              properties:
                id_token:
                  type: string
                  description: ID token emitido por Microsoft Entra ID.
        responses:
          200:
            description: Sesión Microsoft validada.
          401:
            description: Token ausente, inválido o vencido.
        """
        payload = request.get_json(silent=True) or {}
        id_token = str(payload.get("id_token", ""))
        client_id = os.getenv(
            "HISTORICO_MICROSOFT_CLIENT_ID",
            DEFAULT_MICROSOFT_CLIENT_ID,
        )
        if not client_id or not id_token or len(id_token) > 16_384:
            return jsonify({"status": "fail", "error": "token inválido"}), 401

        try:
            signing_key = microsoft_jwks.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=client_id,
                options={
                    "require": ["aud", "exp", "iat", "iss", "sub", "tid"],
                },
            )
            _validate_microsoft_issuer(claims)
        except (PyJWTError, ValueError, OSError):
            current_app.logger.warning("Token Microsoft inválido para históricos")
            return jsonify({"status": "fail", "error": "token inválido"}), 401

        username = str(
            claims.get("preferred_username")
            or claims.get("email")
            or claims.get("name")
            or claims["sub"]
        )
        role = "administrador"
        connection = connect()
        try:
            registered = get_user_by_email(connection, username)
        finally:
            connection.close()
        if registered:
            if not bool(registered["activo"]):
                return jsonify({"status": "fail", "error": "usuario inactivo"}), 403
            role = registered["rol"]
        return session_response(username, provider="microsoft", role=role)

    @blueprint.get("/auth/status")
    def auth_status():
        """Comprueba si la cookie V3 sigue vigente.
        ---
        tags:
          - V3 - Autenticación
        summary: Consultar estado de la sesión V3
        produces:
          - application/json
        responses:
          200:
            description: La sesión está autenticada.
            examples:
              application/json:
                authenticated: true
                user: usuario@ejemplo.cl
          401:
            description: No existe una sesión válida.
            examples:
              application/json:
                authenticated: false
        """
        identity = authenticated_identity()
        if not identity:
            return jsonify({"authenticated": False}), 401
        return jsonify({
            "authenticated": True,
            "user": identity["username"],
            "provider": identity["provider"],
            "role": identity["role"],
        })

    @blueprint.post("/auth/logout")
    def logout():
        """Cierra la sesión de descargas V3.
        ---
        tags:
          - V3 - Autenticación
        summary: Cerrar sesión V3
        produces:
          - application/json
        responses:
          200:
            description: Cookie de sesión eliminada.
        """
        response = jsonify({"status": "success"})
        response.delete_cookie(SESSION_COOKIE, path="/v3")
        return response

    @blueprint.get("/admin/users")
    def admin_list_users():
        """Lista las cuentas locales sin exponer hashes.
        ---
        tags:
          - V3 - Usuarios
        summary: Listar usuarios del portal
        description: Requiere una sesión con rol administrador.
        responses:
          200:
            description: Lista de usuarios con correo, rol y estado.
          401:
            description: No existe una sesión válida.
          403:
            description: La sesión corresponde a una visita.
        """
        _, auth_error = require_administrator()
        if auth_error:
            return auth_error
        connection = connect()
        try:
            users = list_portal_users(connection)
        finally:
            connection.close()
        return jsonify({"status": "success", "users": users})

    @blueprint.post("/admin/users")
    def admin_create_user():
        """Crea una cuenta local con contraseña cifrada.
        ---
        tags:
          - V3 - Usuarios
        summary: Crear usuario del portal
        description: Requiere rol administrador. La contraseña se recibe solo en JSON y se almacena como hash.
        consumes:
          - application/json
        parameters:
          - in: body
            name: usuario
            required: true
            schema:
              type: object
              required: [email, password, role]
              properties:
                email:
                  type: string
                  format: email
                password:
                  type: string
                  format: password
                  minLength: 10
                role:
                  type: string
                  enum: [visita, administrador]
        responses:
          201:
            description: Usuario creado; la respuesta nunca incluye el hash.
          400:
            description: Datos inválidos.
          403:
            description: Permiso de administrador requerido.
          409:
            description: El correo ya está registrado.
        """
        _, auth_error = require_administrator()
        if auth_error:
            return auth_error
        payload = request.get_json(silent=True) or {}
        connection = connect()
        try:
            user = create_portal_user(
                connection,
                payload.get("email"),
                payload.get("password"),
                payload.get("role"),
            )
        except DuplicatePortalUserError as error:
            return jsonify({"status": "fail", "error": str(error)}), 409
        except PortalUserError as error:
            return jsonify({"status": "fail", "error": str(error)}), 400
        finally:
            connection.close()
        return jsonify({"status": "success", "user": user}), 201

    @blueprint.put("/admin/users/<int:user_id>")
    def admin_update_user(user_id: int):
        """Modifica rol, estado o contraseña de una cuenta.
        ---
        tags:
          - V3 - Usuarios
        summary: Actualizar usuario del portal
        description: Desactivar reemplaza el borrado físico y conserva la auditoría básica.
        consumes:
          - application/json
        parameters:
          - in: path
            name: user_id
            type: integer
            required: true
          - in: body
            name: cambios
            required: true
            schema:
              type: object
              properties:
                role:
                  type: string
                  enum: [visita, administrador]
                active:
                  type: boolean
                password:
                  type: string
                  format: password
                  minLength: 10
        responses:
          200:
            description: Usuario actualizado.
          400:
            description: Datos inválidos o se intentó retirar el último administrador local.
          403:
            description: Permiso de administrador requerido.
          404:
            description: Usuario inexistente.
        """
        _, auth_error = require_administrator()
        if auth_error:
            return auth_error
        payload = request.get_json(silent=True) or {}
        connection = connect()
        try:
            user = update_portal_user(
                connection,
                user_id,
                role=payload.get("role") if "role" in payload else None,
                active=payload.get("active") if "active" in payload else None,
                password=payload.get("password") if "password" in payload else None,
            )
        except (PortalUserError, LastAdministratorError) as error:
            return jsonify({"status": "fail", "error": str(error)}), 400
        finally:
            connection.close()
        if not user:
            return jsonify({"status": "fail", "error": "Usuario no encontrado"}), 404
        return jsonify({"status": "success", "user": user})

    def get_device(connection, device_id: int) -> tuple[dict[str, Any], list[int]]:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id_dispositivo, codigo_interno, id_proyecto, descripcion
                FROM sensores_dev.dispositivos
                WHERE id_dispositivo = %s
                """,
                (device_id,),
            )
            device = cursor.fetchone()
            if not device:
                raise LookupError("dispositivo no encontrado")

            cursor.execute(
                """
                SELECT id_sensor
                FROM sensores_dev.sensores_en_dispositivo
                WHERE id_dispositivo = %s
                ORDER BY id_sensor
                """,
                (device_id,),
            )
            sensor_ids = [int(row["id_sensor"]) for row in cursor.fetchall()]
            if not sensor_ids:
                raise LookupError("el dispositivo no tiene sensores asociados")
            return device, sensor_ids
        finally:
            cursor.close()

    def get_project_devices(
        connection,
        project_id: int,
    ) -> tuple[dict[str, Any], list[tuple[dict[str, Any], list[int]]]]:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id_proyecto, nombre, descripcion
                FROM sensores_dev.proyectos
                WHERE id_proyecto = %s
                """,
                (project_id,),
            )
            project = cursor.fetchone()
            if not project:
                raise LookupError("proyecto no encontrado")

            cursor.execute(
                """
                SELECT id_dispositivo
                FROM sensores_dev.dispositivos
                WHERE id_proyecto = %s
                ORDER BY id_dispositivo
                """,
                (project_id,),
            )
            device_ids = [int(row["id_dispositivo"]) for row in cursor.fetchall()]
        finally:
            cursor.close()

        if not device_ids:
            raise LookupError("el proyecto no tiene dispositivos")
        if len(device_ids) > MAX_POWERBI_PROJECT_DEVICES:
            raise ValueError(
                "el proyecto supera el máximo de "
                f"{MAX_POWERBI_PROJECT_DEVICES} dispositivos"
            )
        return project, [get_device(connection, device_id) for device_id in device_ids]

    def fetch_page(
        connection,
        device: dict[str, Any],
        sensor_ids: list[int],
        start: date,
        end: date,
        cursor_value: tuple[int, datetime, int] | None,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], str | None]:
        placeholders = ", ".join(["%s"] * len(sensor_ids))
        clauses = [
            f"d.id_sensor IN ({placeholders})",
            "d.fecha >= %s",
            "d.fecha < DATE_ADD(%s, INTERVAL 1 DAY)",
        ]
        params: list[Any] = [*sensor_ids, start, end]

        if cursor_value:
            cursor_sensor, cursor_date, cursor_id = cursor_value
            clauses.append(
                """
                (
                    d.id_sensor > %s
                    OR (
                        d.id_sensor = %s
                        AND (
                            d.fecha > %s
                            OR (d.fecha = %s AND d.id_dato > %s)
                        )
                    )
                )
                """
            )
            params.extend(
                [
                    cursor_sensor,
                    cursor_sensor,
                    cursor_date,
                    cursor_date,
                    cursor_id,
                ]
            )

        params.append(page_size)
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f"""
                SELECT d.id_dato, d.fecha, d.fecha_insercion, d.id_sensor,
                       d.id_variable, d.id_sesion, d.valor,
                       v.descripcion AS variable_descripcion, v.unidad
                FROM sensores_dev.datos AS d
                LEFT JOIN sensores_dev.variables AS v
                  ON v.id_variable = d.id_variable
                WHERE {' AND '.join(clauses)}
                ORDER BY d.id_sensor ASC, d.fecha ASC, d.id_dato ASC
                LIMIT %s
                """,
                params,
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()

        for row in rows:
            row["id_dispositivo"] = device["id_dispositivo"]
            row["codigo_interno"] = device["codigo_interno"]
            row["id_proyecto"] = device["id_proyecto"]

        next_cursor = None
        if rows:
            last = rows[-1]
            next_cursor = _encode_cursor(
                last["id_sensor"],
                last["fecha"],
                last["id_dato"],
            )
        return rows, next_cursor

    def get_measurement_columns(
        connection,
        sensor_ids: list[int],
        start: date,
        end: date,
    ) -> list[str]:
        placeholders = ", ".join(["%s"] * len(sensor_ids))
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT DISTINCT
                       CONCAT(
                           COALESCE(
                               NULLIF(TRIM(st.modelo), ''),
                               NULLIF(TRIM(st.marca), ''),
                               CONCAT('Sensor tipo ', st.id_sensor_tipo)
                           ),
                           ' [',
                           COALESCE(v.descripcion, CONCAT('Variable ', d.id_variable)),
                           ' (', COALESCE(v.unidad, 'sin unidad'), ')]'
                       )
                FROM sensores_dev.datos AS d
                JOIN sensores_dev.variables AS v
                  ON v.id_variable = d.id_variable
                JOIN sensores_dev.sensores AS sens
                  ON sens.id_sensor = d.id_sensor
                JOIN sensores_dev.sensores_tipo AS st
                  ON st.id_sensor_tipo = sens.id_sensor_tipo
                WHERE d.id_sensor IN ({placeholders})
                  AND d.fecha >= %s
                  AND d.fecha < DATE_ADD(%s, INTERVAL 1 DAY)
                """,
                [*sensor_ids, start, end],
            )
            return sorted(str(row[0]) for row in cursor.fetchall() if row[0])
        finally:
            cursor.close()

    def iter_sensor_rows(
        connection,
        sensor_id: int,
        start: date,
        end: date,
        page_size: int = MAX_PAGE_SIZE,
        latest_before: datetime | None = None,
    ) -> Iterator[dict[str, Any]]:
        cursor_value: tuple[datetime, int] | None = None
        while True:
            clauses = [
                "d.id_sensor = %s",
                "d.fecha >= %s",
                "d.fecha < DATE_ADD(%s, INTERVAL 1 DAY)",
            ]
            params: list[Any] = [sensor_id, start, end]
            if latest_before is not None:
                clauses.append("d.fecha <= %s")
                params.append(latest_before)
            if cursor_value:
                cursor_date, cursor_id = cursor_value
                clauses.append(
                    "(d.fecha < %s OR (d.fecha = %s AND d.id_dato < %s))"
                )
                params.extend([cursor_date, cursor_date, cursor_id])
            params.append(min(max(int(page_size), 1), MAX_PAGE_SIZE))

            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(
                    f"""
                    SELECT STRAIGHT_JOIN
                           d.id_dato, d.fecha, d.fecha_insercion,
                           d.id_sensor, d.id_variable, d.id_sesion, d.valor,
                           s.descripcion AS sesion_descripcion,
                           s.fecha_inicio, s.ubicacion,
                           CONCAT(
                               COALESCE(
                                   NULLIF(TRIM(st.modelo), ''),
                                   NULLIF(TRIM(st.marca), ''),
                                   CONCAT('Sensor tipo ', st.id_sensor_tipo)
                               ),
                               ' [',
                               COALESCE(
                                   v.descripcion,
                                   CONCAT('Variable ', d.id_variable)
                               ),
                               ' (', COALESCE(v.unidad, 'sin unidad'), ')]'
                           ) AS unidad_medida
                    FROM sensores_dev.datos AS d
                    FORCE INDEX (idx_datos_sensor_fecha)
                    JOIN sensores_dev.variables AS v
                      ON v.id_variable = d.id_variable
                    JOIN sensores_dev.sensores AS sens
                      ON sens.id_sensor = d.id_sensor
                    JOIN sensores_dev.sensores_tipo AS st
                      ON st.id_sensor_tipo = sens.id_sensor_tipo
                    LEFT JOIN sensores_dev.sesiones AS s
                      ON s.id_sesion = d.id_sesion
                    WHERE {' AND '.join(clauses)}
                    ORDER BY d.fecha DESC, d.id_dato DESC
                    LIMIT %s
                    """,
                    params,
                )
                rows = cursor.fetchall()
            finally:
                cursor.close()

            for row in rows:
                yield row
            if len(rows) < min(max(int(page_size), 1), MAX_PAGE_SIZE):
                break
            last = rows[-1]
            cursor_value = (last["fecha"], int(last["id_dato"]))

    def parse_request() -> tuple[
        date,
        date,
        int,
        tuple[int, datetime, int] | None,
    ]:
        start = _parse_date(request.args.get("fecha_inicio"), "fecha_inicio")
        end = _parse_date(request.args.get("fecha_fin"), "fecha_fin")
        if start > end:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin")
        try:
            page_size = int(request.args.get("limite", DEFAULT_PAGE_SIZE))
        except ValueError as error:
            raise ValueError("limite debe ser entero") from error
        if page_size < 1:
            raise ValueError("limite debe ser mayor que cero")
        page_size = min(page_size, MAX_PAGE_SIZE)
        return start, end, page_size, _decode_cursor(request.args.get("cursor"))

    @blueprint.get("/dispositivos/<int:device_id>/mediciones")
    def list_measurements(device_id: int):
        """Lista mediciones V3 por dispositivo mediante cursor.
        ---
        tags:
          - V3 - Datos estructurados
        summary: Listar mediciones paginadas de un dispositivo
        description: >
          Devuelve datos en formato largo, una fila por medición. El servidor
          resuelve automáticamente los sensores del dispositivo. Para continuar,
          envíe next_cursor como cursor; no use offset.
        produces:
          - application/json
        parameters:
          - name: device_id
            in: path
            type: integer
            required: true
            description: ID interno del dispositivo.
          - name: fecha_inicio
            in: query
            type: string
            format: date
            required: true
            description: Primer día incluido, formato YYYY-MM-DD.
          - name: fecha_fin
            in: query
            type: string
            format: date
            required: true
            description: Último día incluido, formato YYYY-MM-DD.
          - name: limite
            in: query
            type: integer
            default: 500
            minimum: 1
            maximum: 1000
            required: false
            description: Mediciones por página.
          - name: cursor
            in: query
            type: string
            required: false
            description: Valor next_cursor recibido en la página anterior.
        responses:
          200:
            description: Página de mediciones obtenida correctamente.
            examples:
              application/json:
                status: success
                data:
                  dispositivo:
                    id_dispositivo: 225
                    codigo_interno: HIRIPRO-V6
                    id_proyecto: 18
                  mediciones:
                    - id_dato: 59928911
                      fecha: '2026-05-20T12:39:30'
                      id_sensor: 219
                      id_variable: 31
                      variable_descripcion: Dióxido de Carbono
                      unidad: ppm
                      valor: 491.6
                  next_cursor: cursor-opaco
                  has_more: true
          400:
            description: Fechas, límite o cursor inválidos.
          404:
            description: Dispositivo no encontrado.
          503:
            description: Base de datos temporalmente no disponible.
        """
        try:
            start, end, page_size, cursor_value = parse_request()
        except ValueError as error:
            return jsonify({"status": "fail", "error": str(error)}), 400

        connection = None
        try:
            connection = connect()
            device, sensor_ids = get_device(connection, device_id)
            rows, next_cursor = fetch_page(
                connection,
                device,
                sensor_ids,
                start,
                end,
                cursor_value,
                page_size,
            )
            return jsonify(
                {
                    "status": "success",
                    "data": {
                        "dispositivo": device,
                        "mediciones": rows,
                        "next_cursor": next_cursor,
                        "has_more": len(rows) == page_size,
                    },
                }
            )
        except LookupError as error:
            return jsonify({"status": "fail", "error": str(error)}), 404
        except mysql.connector.Error:
            current_app.logger.exception("Error de MariaDB en mediciones V3")
            return jsonify(
                {"status": "fail", "error": "error consultando la base de datos"}
            ), 503
        finally:
            if connection is not None and connection.is_connected():
                connection.close()

    @blueprint.get("/vista-previa")
    def latest_preview():
        """Entrega una tabla estructurada y paginada para visualización.
        ---
        tags:
          - V3 - Datos estructurados
        summary: Vista estructurada de datos recientes o de un rango
        description: >
          Devuelve formato ancho: una fila por fecha y una columna por variable,
          equivalente a la tabla del portal. Acepta hasta 10 dispositivos y usa
          cursor para mostrar páginas anteriores sin consultas masivas.
        produces:
          - application/json
        parameters:
          - name: id_dispositivo
            in: query
            type: string
            required: true
            description: Uno o más IDs separados por coma; máximo 10.
            example: '92,225'
          - name: fecha_inicio
            in: query
            type: string
            format: date
            required: false
            description: Primer día incluido; si se omite comienza en 1970.
          - name: fecha_fin
            in: query
            type: string
            format: date
            required: false
            description: Último día incluido; si se omite usa hoy.
          - name: limite
            in: query
            type: integer
            default: 25
            minimum: 1
            maximum: 100
            required: false
            description: Filas estructuradas por página.
          - name: cursor
            in: query
            type: string
            required: false
            description: next_cursor de la página anterior.
        responses:
          200:
            description: Tabla estructurada obtenida correctamente.
            examples:
              application/json:
                status: success
                data:
                  tableData:
                    - fecha: '2026-07-31T12:00:00'
                      codigo_interno: AIRE-01
                      PMS5003-PM2.5: 12.4
                  totalCount: 1
                  preview: true
                  has_more: true
                  next_cursor: cursor-opaco
                  page_size: 25
          400:
            description: Parámetros inválidos o más de 10 dispositivos.
          404:
            description: Algún dispositivo no fue encontrado.
          503:
            description: Base de datos temporalmente no disponible.
        """
        raw_device_ids = request.args.get("id_dispositivo", "")
        try:
            device_ids = list(dict.fromkeys(
                int(value.strip())
                for value in raw_device_ids.split(",")
                if value.strip()
            ))
            limit = min(max(int(request.args.get("limite", 25)), 1), 100)
            start = (
                _parse_date(request.args.get("fecha_inicio"), "fecha_inicio")
                if request.args.get("fecha_inicio")
                else date(1970, 1, 1)
            )
            end = (
                _parse_date(request.args.get("fecha_fin"), "fecha_fin")
                if request.args.get("fecha_fin")
                else date.today()
            )
            if start > end:
                raise ValueError("fecha_inicio no puede ser posterior a fecha_fin")
            preview_cursor = _decode_preview_cursor(request.args.get("cursor"))
        except ValueError:
            return jsonify({"status": "fail", "error": "parámetros inválidos"}), 400
        if not device_ids:
            return jsonify({"status": "fail", "error": "id_dispositivo es obligatorio"}), 400
        if len(device_ids) > 10:
            return jsonify({"status": "fail", "error": "máximo 10 dispositivos"}), 400

        connection = None
        try:
            connection = connect()
            candidates: list[dict[str, Any]] = []
            latest_before = (
                datetime.fromisoformat(preview_cursor[0])
                if preview_cursor
                else None
            )
            for device_id in device_ids:
                device, sensor_ids = get_device(connection, device_id)
                streams = [
                    iter_sensor_rows(
                        connection,
                        sensor_id,
                        start,
                        end,
                        page_size=500,
                        latest_before=latest_before,
                    )
                    for sensor_id in sensor_ids
                ]
                rows: Iterator[dict[str, Any]] = _merge_wide_rows(streams, device)
                if preview_cursor:
                    unfiltered_rows = rows
                    rows = (
                        row for row in unfiltered_rows
                        if _preview_row_key(row) < preview_cursor
                    )
                candidates.extend(itertools.islice(rows, limit + 1))

            candidates.sort(key=_preview_row_key, reverse=True)
            if preview_cursor:
                candidates = [
                    row for row in candidates
                    if _preview_row_key(row) < preview_cursor
                ]
            has_more = len(candidates) > limit
            page_rows = candidates[:limit]
            table_data = [
                {key: _serialize(value) for key, value in row.items()}
                for row in page_rows
            ]
            return jsonify({
                "status": "success",
                "data": {
                    "tableData": table_data,
                    "totalCount": len(table_data),
                    "preview": True,
                    "has_more": has_more,
                    "next_cursor": (
                        _encode_preview_cursor(page_rows[-1])
                        if has_more and page_rows
                        else None
                    ),
                    "page_size": limit,
                    "range": {
                        "fecha_inicio": start.isoformat(),
                        "fecha_fin": end.isoformat(),
                    },
                },
            })
        except LookupError as error:
            return jsonify({"status": "fail", "error": str(error)}), 404
        except mysql.connector.Error:
            current_app.logger.exception("Error de MariaDB en vista previa V3")
            return jsonify({
                "status": "fail",
                "error": "error consultando la base de datos",
            }), 503
        finally:
            if connection is not None and connection.is_connected():
                connection.close()

    @blueprint.get("/disponibilidad")
    def measurement_availability():
        """Indica qué días de un mes tienen datos sin contar sus registros.
        ---
        tags:
          - V3 - Datos estructurados
        summary: Listar días con datos dentro de un mes
        description: >
          Consulta liviana para pintar el calendario. No descarga mediciones ni
          calcula conteos; solo indica si existe al menos un dato en cada día.
        produces:
          - application/json
        parameters:
          - name: id_dispositivo
            in: query
            type: string
            required: true
            description: Uno o más IDs separados por coma; máximo 10.
          - name: mes
            in: query
            type: string
            required: true
            pattern: '^\\d{4}-\\d{2}$'
            description: Mes consultado en formato YYYY-MM.
            example: '2026-07'
        responses:
          200:
            description: Días que contienen al menos una medición.
            examples:
              application/json:
                status: success
                data:
                  month: '2026-07'
                  days: ['2026-07-01', '2026-07-02']
                  device_ids: [225]
          400:
            description: Dispositivo o mes inválido.
          404:
            description: Dispositivo no encontrado.
          503:
            description: Base de datos temporalmente no disponible.
        """
        raw_device_ids = request.args.get("id_dispositivo", "")
        month_value = request.args.get("mes", "")
        try:
            device_ids = list(dict.fromkeys(
                int(value.strip())
                for value in raw_device_ids.split(",")
                if value.strip()
            ))
            month_start = datetime.strptime(month_value, "%Y-%m").date()
        except ValueError:
            return jsonify({
                "status": "fail",
                "error": "id_dispositivo o mes inválido",
            }), 400
        if not device_ids:
            return jsonify({
                "status": "fail",
                "error": "id_dispositivo es obligatorio",
            }), 400
        if len(device_ids) > 10:
            return jsonify({
                "status": "fail",
                "error": "máximo 10 dispositivos",
            }), 400

        connection = None
        try:
            connection = connect()
            sensor_ids: list[int] = []
            for device_id in device_ids:
                _, device_sensor_ids = get_device(connection, device_id)
                sensor_ids.extend(device_sensor_ids)
            sensor_ids = list(dict.fromkeys(sensor_ids))
            placeholders = ", ".join(["%s"] * len(sensor_ids))

            days_with_data: list[str] = []
            cursor = connection.cursor()
            try:
                days_in_month = calendar.monthrange(
                    month_start.year,
                    month_start.month,
                )[1]
                for day_number in range(days_in_month):
                    day_start = month_start + timedelta(days=day_number)
                    day_end = day_start + timedelta(days=1)
                    cursor.execute(
                        f"""
                        SELECT 1
                        FROM sensores_dev.datos AS d
                        FORCE INDEX (idx_datos_sensor_fecha)
                        WHERE d.id_sensor IN ({placeholders})
                          AND d.fecha >= %s
                          AND d.fecha < %s
                        LIMIT 1
                        """,
                        [*sensor_ids, day_start, day_end],
                    )
                    if cursor.fetchone() is not None:
                        days_with_data.append(day_start.isoformat())
            finally:
                cursor.close()

            response = jsonify({
                "status": "success",
                "data": {
                    "month": month_start.strftime("%Y-%m"),
                    "days": days_with_data,
                    "device_ids": device_ids,
                },
            })
            response.headers["Cache-Control"] = "private, max-age=60"
            return response
        except LookupError as error:
            return jsonify({"status": "fail", "error": str(error)}), 404
        except mysql.connector.Error:
            current_app.logger.exception(
                "Error de MariaDB consultando disponibilidad V3"
            )
            return jsonify({
                "status": "fail",
                "error": "error consultando la base de datos",
            }), 503
        finally:
            if connection is not None and connection.is_connected():
                connection.close()

    @blueprint.get("/powerbi/proyectos/<int:project_id>/datos")
    def powerbi_project_data(project_id: int):
        """Entrega el formato ancho legacy mediante páginas V3 protegidas.
        ---
        tags:
          - V3 - Power BI
        summary: Listar un proyecto completo para Power BI
        description: >
          Devuelve formato ancho compatible con V2 y paginación por cursor. La
          clave se envía en X-API-Key, nunca en la URL. Las fechas son obligatorias.
          Si otra carga está activa puede responder 429 con Retry-After.
        produces:
          - application/json
        parameters:
          - name: project_id
            in: path
            type: integer
            required: true
            description: ID interno del proyecto.
          - name: X-API-Key
            in: header
            type: string
            format: password
            required: true
            description: Clave privada configurada para Power BI.
          - name: fecha_inicio
            in: query
            type: string
            format: date
            required: true
          - name: fecha_fin
            in: query
            type: string
            format: date
            required: true
          - name: limite
            in: query
            type: integer
            default: 500
            minimum: 1
            maximum: 1000
            required: false
          - name: cursor
            in: query
            type: string
            required: false
            description: next_cursor de la página anterior.
        responses:
          200:
            description: Página de datos anchos del proyecto.
          400:
            description: Fechas, límite o cursor inválidos.
          401:
            description: Clave ausente o incorrecta.
          404:
            description: Proyecto sin dispositivos o no encontrado.
          429:
            description: Otra carga Power BI está en curso; reintente después.
          503:
            description: Integración no configurada o base no disponible.
        """
        auth_error = require_powerbi_api_key()
        if auth_error:
            return auth_error

        try:
            start = _parse_date(request.args.get("fecha_inicio"), "fecha_inicio")
            end = _parse_date(request.args.get("fecha_fin"), "fecha_fin")
            if start > end:
                raise ValueError("fecha_inicio no puede ser posterior a fecha_fin")
            limit = min(max(int(request.args.get("limite", 500)), 1), MAX_PAGE_SIZE)
            page_cursor = _decode_preview_cursor(request.args.get("cursor"))
        except ValueError as error:
            return jsonify({"status": "fail", "error": str(error)}), 400

        lock_file = open(POWERBI_LOCK_PATH, "a+")
        deadline = time.monotonic() + 30
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    lock_file.close()
                    return (
                        jsonify({
                            "status": "queued",
                            "error": "hay otra consulta Power BI en curso",
                        }),
                        429,
                        {"Retry-After": "30"},
                    )
                time.sleep(0.5)

        connection = None
        try:
            connection = connect()
            project, prepared_devices = get_project_devices(connection, project_id)
            candidates: list[dict[str, Any]] = []
            latest_before = (
                datetime.fromisoformat(page_cursor[0])
                if page_cursor
                else None
            )

            for device, sensor_ids in prepared_devices:
                streams = [
                    iter_sensor_rows(
                        connection,
                        sensor_id,
                        start,
                        end,
                        page_size=500,
                        latest_before=latest_before,
                    )
                    for sensor_id in sensor_ids
                ]
                rows: Iterator[dict[str, Any]] = _merge_wide_rows(streams, device)
                if page_cursor:
                    unfiltered_rows = rows
                    rows = (
                        row for row in unfiltered_rows
                        if _preview_row_key(row) < page_cursor
                    )
                candidates.extend(itertools.islice(rows, limit + 1))

            candidates.sort(key=_preview_row_key, reverse=True)
            if page_cursor:
                candidates = [
                    row for row in candidates
                    if _preview_row_key(row) < page_cursor
                ]
            has_more = len(candidates) > limit
            page_rows = candidates[:limit]
            table_data = [
                {key: _serialize(value) for key, value in row.items()}
                for row in page_rows
            ]
            response = jsonify({
                "status": "success",
                "data": {
                    "tableData": table_data,
                    "tabla": "datos",
                    "totalCount": len(table_data),
                    "has_more": has_more,
                    "next_cursor": (
                        _encode_preview_cursor(page_rows[-1])
                        if has_more and page_rows
                        else None
                    ),
                    "page_size": limit,
                    "proyecto": {
                        key: _serialize(value) for key, value in project.items()
                    },
                    "range": {
                        "fecha_inicio": start.isoformat(),
                        "fecha_fin": end.isoformat(),
                    },
                },
            })
            response.headers["Cache-Control"] = "no-store"
            return response
        except LookupError as error:
            return jsonify({"status": "fail", "error": str(error)}), 404
        except ValueError as error:
            return jsonify({"status": "fail", "error": str(error)}), 400
        except mysql.connector.Error:
            current_app.logger.exception("Error de MariaDB en Power BI V3")
            return jsonify({
                "status": "fail",
                "error": "error consultando la base de datos",
            }), 503
        finally:
            if connection is not None and connection.is_connected():
                connection.close()
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()

    @blueprint.get("/disponibilidad-meses")
    def monthly_measurement_availability():
        """Indica qué meses de un año tienen al menos una medición.
        ---
        tags:
          - V3 - Datos estructurados
        summary: Listar meses con datos dentro de un año
        description: >
          Consulta liviana para el calendario anual. No descarga mediciones ni
          cuenta registros; devuelve únicamente los meses que tienen datos.
        produces:
          - application/json
        parameters:
          - name: id_dispositivo
            in: query
            type: string
            required: true
            description: Uno o más IDs separados por coma; máximo 10.
          - name: anio
            in: query
            type: integer
            minimum: 1970
            maximum: 2100
            required: true
            description: Año de cuatro cifras.
            example: 2026
        responses:
          200:
            description: Meses que contienen al menos una medición.
            examples:
              application/json:
                status: success
                data:
                  year: 2026
                  months: ['2026-01', '2026-02', '2026-07']
                  device_ids: [225]
          400:
            description: Dispositivo o año inválido.
          404:
            description: Dispositivo no encontrado.
          503:
            description: Base de datos temporalmente no disponible.
        """
        raw_device_ids = request.args.get("id_dispositivo", "")
        try:
            device_ids = list(dict.fromkeys(
                int(value.strip())
                for value in raw_device_ids.split(",")
                if value.strip()
            ))
            year = int(request.args.get("anio", ""))
        except ValueError:
            return jsonify({
                "status": "fail",
                "error": "id_dispositivo o año inválido",
            }), 400
        if not device_ids:
            return jsonify({
                "status": "fail",
                "error": "id_dispositivo es obligatorio",
            }), 400
        if len(device_ids) > 10:
            return jsonify({
                "status": "fail",
                "error": "máximo 10 dispositivos",
            }), 400
        if year < 1970 or year > 2100:
            return jsonify({
                "status": "fail",
                "error": "año fuera de rango",
            }), 400

        connection = None
        try:
            connection = connect()
            sensor_ids: list[int] = []
            for device_id in device_ids:
                _, device_sensor_ids = get_device(connection, device_id)
                sensor_ids.extend(device_sensor_ids)
            sensor_ids = list(dict.fromkeys(sensor_ids))
            placeholders = ", ".join(["%s"] * len(sensor_ids))

            months_with_data: list[str] = []
            cursor = connection.cursor()
            try:
                for month_number in range(1, 13):
                    month_start = date(year, month_number, 1)
                    month_end = (
                        date(year + 1, 1, 1)
                        if month_number == 12
                        else date(year, month_number + 1, 1)
                    )
                    cursor.execute(
                        f"""
                        SELECT 1
                        FROM sensores_dev.datos AS d
                        FORCE INDEX (idx_datos_sensor_fecha)
                        WHERE d.id_sensor IN ({placeholders})
                          AND d.fecha >= %s
                          AND d.fecha < %s
                        LIMIT 1
                        """,
                        [*sensor_ids, month_start, month_end],
                    )
                    if cursor.fetchone() is not None:
                        months_with_data.append(
                            f"{year:04d}-{month_number:02d}"
                        )
            finally:
                cursor.close()

            response = jsonify({
                "status": "success",
                "data": {
                    "year": year,
                    "months": months_with_data,
                    "device_ids": device_ids,
                },
            })
            response.headers["Cache-Control"] = "private, max-age=60"
            return response
        except LookupError as error:
            return jsonify({"status": "fail", "error": str(error)}), 404
        except mysql.connector.Error:
            current_app.logger.exception(
                "Error de MariaDB consultando meses disponibles V3"
            )
            return jsonify({
                "status": "fail",
                "error": "error consultando la base de datos",
            }), 503
        finally:
            if connection is not None and connection.is_connected():
                connection.close()

    @blueprint.get("/dispositivos/<int:device_id>/historico.ndjson")
    def stream_history(device_id: int):
        """Descarga mediciones V3 como NDJSON transmitido por bloques.
        ---
        tags:
          - V3 - Descargas
        summary: Descargar histórico largo de un dispositivo
        description: >
          Requiere una cookie obtenida en /v3/auth/login o /v3/auth/microsoft.
          Cada línea es un JSON independiente. El cliente debe leer el stream y
          no usar response.json(). Las fechas son obligatorias.
        produces:
          - application/x-ndjson
        parameters:
          - name: device_id
            in: path
            type: integer
            required: true
          - name: fecha_inicio
            in: query
            type: string
            format: date
            required: true
          - name: fecha_fin
            in: query
            type: string
            format: date
            required: true
          - name: limite
            in: query
            type: integer
            default: 500
            minimum: 1
            maximum: 1000
            required: false
            description: Tamaño de cada bloque interno.
          - name: cursor
            in: query
            type: string
            required: false
            description: Checkpoint desde el cual reanudar.
        responses:
          200:
            description: Stream NDJSON; termina con una línea _meta complete.
          400:
            description: Fechas, límite o cursor inválidos.
          401:
            description: Sesión requerida.
        """
        _, auth_error = require_authentication()
        if auth_error:
            return auth_error
        try:
            start, end, page_size, cursor_value = parse_request()
        except ValueError as error:
            return jsonify({"status": "fail", "error": str(error)}), 400

        @stream_with_context
        def generate() -> Iterator[str]:
            connection = None
            emitted = 0
            current_cursor = cursor_value
            try:
                connection = connect()
                device, sensor_ids = get_device(connection, device_id)
                while True:
                    rows, next_cursor = fetch_page(
                        connection,
                        device,
                        sensor_ids,
                        start,
                        end,
                        current_cursor,
                        page_size,
                    )
                    for row in rows:
                        yield json.dumps(
                            row,
                            default=_serialize,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ) + "\n"
                    emitted += len(rows)
                    if not rows or len(rows) < page_size:
                        yield json.dumps(
                            {
                                "_meta": {
                                    "complete": True,
                                    "rows": emitted,
                                    "next_cursor": None,
                                }
                            },
                            separators=(",", ":"),
                        ) + "\n"
                        break
                    current_cursor = _decode_cursor(next_cursor)
                    yield json.dumps(
                        {
                            "_meta": {
                                "complete": False,
                                "rows": emitted,
                                "next_cursor": next_cursor,
                            }
                        },
                        separators=(",", ":"),
                    ) + "\n"
            except LookupError as error:
                yield json.dumps(
                    {"_error": {"status": 404, "message": str(error)}},
                    separators=(",", ":"),
                ) + "\n"
            except mysql.connector.Error:
                current_app.logger.exception("Error de MariaDB en histórico V3")
                yield json.dumps(
                    {
                        "_error": {
                            "status": 503,
                            "message": "error consultando la base de datos",
                        }
                    },
                    separators=(",", ":"),
                ) + "\n"
            finally:
                if connection is not None and connection.is_connected():
                    connection.close()

        return Response(
            generate(),
            mimetype="application/x-ndjson",
            headers={
                "Cache-Control": "no-store",
                "X-Accel-Buffering": "no",
                "Content-Disposition": (
                    f'attachment; filename="dispositivo-{device_id}-historico.ndjson"'
                ),
            },
        )

    @blueprint.get("/historicos.csv")
    def stream_csv_history():
        """Descarga históricos V3 en CSV ancho o largo.
        ---
        tags:
          - V3 - Descargas
        summary: Descargar CSV histórico de uno o más dispositivos
        description: >
          Requiere cookie de sesión V3. El formato web genera una fila por fecha
          y columnas dinámicas como el portal; largo genera una fila por medición.
          Se aceptan hasta 25 dispositivos. Las descargas se serializan para
          proteger MariaDB y pueden responder 429.
        produces:
          - text/csv
          - application/json
        parameters:
          - name: id_dispositivo
            in: query
            type: string
            required: true
            description: Uno o más IDs separados por coma; máximo 25.
          - name: fecha_inicio
            in: query
            type: string
            format: date
            default: '1970-01-01'
            required: false
          - name: fecha_fin
            in: query
            type: string
            format: date
            required: false
            description: Si se omite usa la fecha actual.
          - name: formato
            in: query
            type: string
            enum: [web, largo]
            default: web
            required: false
        responses:
          200:
            description: CSV UTF-8 con BOM y nombre por dispositivo/rango.
          400:
            description: Dispositivo, fechas o formato inválidos.
          401:
            description: Sesión requerida.
          404:
            description: Algún dispositivo no fue encontrado.
          429:
            description: Otra descarga está en curso; reintente después.
          503:
            description: Base de datos temporalmente no disponible.
        """
        username, auth_error = require_authentication()
        if auth_error:
            return auth_error

        raw_device_ids = request.args.get("id_dispositivo", "")
        try:
            device_ids = list(dict.fromkeys(
                int(value.strip())
                for value in raw_device_ids.split(",")
                if value.strip()
            ))
        except ValueError:
            return jsonify({"status": "fail", "error": "id_dispositivo inválido"}), 400
        if not device_ids:
            return jsonify({"status": "fail", "error": "id_dispositivo es obligatorio"}), 400
        if len(device_ids) > 25:
            return jsonify({"status": "fail", "error": "máximo 25 dispositivos por descarga"}), 400

        try:
            start = _parse_date(
                request.args.get("fecha_inicio", "1970-01-01"),
                "fecha_inicio",
            )
            end = _parse_date(
                request.args.get("fecha_fin", date.today().isoformat()),
                "fecha_fin",
            )
            if start > end:
                raise ValueError("fecha_inicio no puede ser posterior a fecha_fin")
        except ValueError as error:
            return jsonify({"status": "fail", "error": str(error)}), 400

        output_format = request.args.get("formato", "web").lower()
        if output_format not in {"web", "largo"}:
            return jsonify({
                "status": "fail",
                "error": "formato debe ser web o largo",
            }), 400

        metadata_connection = None
        try:
            metadata_connection = connect()
            device_codes = [
                str(get_device(metadata_connection, device_id)[0]["codigo_interno"])
                for device_id in device_ids
            ]
        except LookupError as error:
            return jsonify({"status": "fail", "error": str(error)}), 404
        except mysql.connector.Error:
            current_app.logger.exception("Error obteniendo nombres para CSV")
            return jsonify({
                "status": "fail",
                "error": "error consultando la base de datos",
            }), 503
        finally:
            if metadata_connection is not None and metadata_connection.is_connected():
                metadata_connection.close()

        device_filename = "-".join(
            _safe_filename_part(code) for code in device_codes
        )[:120].rstrip("-._")
        download_filename = f"{device_filename}_{start}_{end}.csv"

        lock_file = open(EXPORT_LOCK_PATH, "a+")
        deadline = time.monotonic() + 30
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    lock_file.close()
                    return (
                        jsonify({
                            "status": "queued",
                            "error": "hay otra descarga en curso; intente nuevamente",
                        }),
                        429,
                        {"Retry-After": "30"},
                    )
                time.sleep(0.5)

        columns = [
            "id_dato", "fecha", "fecha_insercion", "id_proyecto",
            "id_dispositivo", "codigo_interno", "id_sensor", "id_variable",
            "variable_descripcion", "unidad", "id_sesion", "valor",
        ]

        @stream_with_context
        def generate_csv() -> Iterator[str]:
            connection = None
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            try:
                connection = connect()
                prepared_devices = [
                    (device, sensor_ids)
                    for device, sensor_ids in (
                        get_device(connection, device_id)
                        for device_id in device_ids
                    )
                ]

                if output_format == "web":
                    measurement_columns = sorted({
                        column
                        for _, sensor_ids in prepared_devices
                        for column in get_measurement_columns(
                            connection, sensor_ids, start, end
                        )
                    })
                    output_columns = [
                        *WIDE_BASE_COLUMNS,
                        *measurement_columns,
                        "id_dato_concatenado",
                    ]
                    writer.writerow(output_columns)
                    yield "\ufeff" + buffer.getvalue()
                    buffer.seek(0)
                    buffer.truncate(0)

                    for device, sensor_ids in prepared_devices:
                        streams = [
                            iter_sensor_rows(connection, sensor_id, start, end)
                            for sensor_id in sensor_ids
                        ]
                        for row in _merge_wide_rows(streams, device):
                            writer.writerow([
                                _serialize(row.get(column))
                                for column in output_columns
                            ])
                            if buffer.tell() >= 64 * 1024:
                                yield buffer.getvalue()
                                buffer.seek(0)
                                buffer.truncate(0)
                        if buffer.tell():
                            yield buffer.getvalue()
                            buffer.seek(0)
                            buffer.truncate(0)
                else:
                    writer.writerow(columns)
                    yield "\ufeff" + buffer.getvalue()
                    buffer.seek(0)
                    buffer.truncate(0)

                    for device, sensor_ids in prepared_devices:
                        cursor_value = None
                        while True:
                            rows, next_cursor = fetch_page(
                                connection,
                                device,
                                sensor_ids,
                                start,
                                end,
                                cursor_value,
                                MAX_PAGE_SIZE,
                            )
                            for row in rows:
                                writer.writerow([
                                    _serialize(row.get(column)) for column in columns
                                ])
                            if buffer.tell():
                                yield buffer.getvalue()
                                buffer.seek(0)
                                buffer.truncate(0)
                            if not rows or len(rows) < MAX_PAGE_SIZE:
                                break
                            cursor_value = _decode_cursor(next_cursor)
            except (LookupError, mysql.connector.Error):
                current_app.logger.exception(
                    "Error exportando histórico CSV para %s", username
                )
            finally:
                if connection is not None and connection.is_connected():
                    connection.close()
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()

        return Response(
            generate_csv(),
            mimetype="text/csv",
            headers={
                "Cache-Control": "no-store",
                "X-Accel-Buffering": "no",
                "Content-Disposition": (
                    f'attachment; filename="{download_filename}"'
                ),
            },
        )

    return blueprint


__all__ = [
    "create_historico_v3_blueprint",
    "_api_key_matches",
    "_decode_cursor",
    "_encode_cursor",
    "_parse_date",
    "_safe_filename_part",
    "_validate_microsoft_issuer",
]
