"""Blueprint V3 para consultar y descargar históricos por dispositivo.

Este módulo no reemplaza rutas legacy. Se registra con un prefijo /v3 y usa:

* filtros obligatorios por dispositivo y fecha;
* paginación keyset por (id_sensor, fecha, id_dato);
* lotes pequeños y acotados;
* streaming NDJSON con checkpoints reanudables.
"""

from __future__ import annotations

import base64
import csv
import fcntl
import heapq
import io
import json
import os
import secrets
import time
import uuid
from datetime import date, datetime
from typing import Any, Iterator

import decimal
import mysql.connector
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash
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
                values.setdefault(row["unidad_medida"], []).append(row["valor"])
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

    def authenticated_user() -> str | None:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        try:
            payload = serializer().loads(token, max_age=SESSION_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return None
        username = payload.get("sub") if isinstance(payload, dict) else None
        return username if isinstance(username, str) else None

    def require_authentication():
        username = authenticated_user()
        if username:
            return username, None
        return None, (
            jsonify({"status": "fail", "error": "autenticación requerida"}),
            401,
        )

    def session_response(username: str, provider: str = "local") -> Response:
        token = serializer().dumps({"sub": username, "provider": provider})
        response = jsonify({
            "status": "success",
            "user": username,
            "provider": provider,
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
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", ""))
        password = str(payload.get("password", ""))
        expected_user = os.getenv("HISTORICO_USER", "")
        password_hash = os.getenv("HISTORICO_PASSWORD_HASH", "")
        valid = (
            bool(expected_user)
            and bool(password_hash)
            and secrets.compare_digest(username, expected_user)
            and check_password_hash(password_hash, password)
        )
        if not valid:
            return jsonify({"status": "fail", "error": "credenciales inválidas"}), 401

        return session_response(username)

    @blueprint.post("/auth/microsoft")
    def microsoft_login():
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
        return session_response(username, provider="microsoft")

    @blueprint.get("/auth/status")
    def auth_status():
        username = authenticated_user()
        if not username:
            return jsonify({"authenticated": False}), 401
        return jsonify({"authenticated": True, "user": username})

    @blueprint.post("/auth/logout")
    def logout():
        response = jsonify({"status": "success"})
        response.delete_cookie(SESSION_COOKIE, path="/v3")
        return response

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
                       CONCAT(st.modelo, ' [', v.descripcion, ' (', v.unidad, ')]')
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
    ) -> Iterator[dict[str, Any]]:
        cursor_value: tuple[datetime, int] | None = None
        while True:
            clauses = [
                "d.id_sensor = %s",
                "d.fecha >= %s",
                "d.fecha < DATE_ADD(%s, INTERVAL 1 DAY)",
            ]
            params: list[Any] = [sensor_id, start, end]
            if cursor_value:
                cursor_date, cursor_id = cursor_value
                clauses.append(
                    "(d.fecha < %s OR (d.fecha = %s AND d.id_dato < %s))"
                )
                params.extend([cursor_date, cursor_date, cursor_id])
            params.append(MAX_PAGE_SIZE)

            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(
                    f"""
                    SELECT STRAIGHT_JOIN
                           d.id_dato, d.fecha, d.fecha_insercion,
                           d.id_sensor, d.id_variable, d.id_sesion, d.valor,
                           s.descripcion AS sesion_descripcion,
                           s.fecha_inicio, s.ubicacion,
                           CONCAT(st.modelo, ' [', v.descripcion, ' (',
                                  v.unidad, ')]') AS unidad_medida
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
            if len(rows) < MAX_PAGE_SIZE:
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

    @blueprint.get("/dispositivos/<int:device_id>/historico.ndjson")
    def stream_history(device_id: int):
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
                    f'attachment; filename="historico-{start}-{end}.csv"'
                ),
            },
        )

    return blueprint


__all__ = [
    "create_historico_v3_blueprint",
    "_decode_cursor",
    "_encode_cursor",
    "_parse_date",
    "_validate_microsoft_issuer",
]
