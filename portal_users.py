from __future__ import annotations

import re
from typing import Any

import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash


VALID_ROLES = {"visita", "administrador"}
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class PortalUserError(ValueError):
    pass


class DuplicatePortalUserError(PortalUserError):
    pass


class LastAdministratorError(PortalUserError):
    pass


def normalize_email(value: Any) -> str:
    email = str(value or "").strip().casefold()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise PortalUserError("Correo electrónico inválido")
    return email


def validate_role(value: Any) -> str:
    role = str(value or "").strip().casefold()
    if role not in VALID_ROLES:
        raise PortalUserError("Rol inválido")
    return role


def validate_password(value: Any) -> str:
    password = str(value or "")
    if len(password) < 10 or len(password) > 256:
        raise PortalUserError("La contraseña debe tener entre 10 y 256 caracteres")
    return password


def create_schema(connection) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS portal_usuarios (
                id_usuario BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                email VARCHAR(254) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                rol VARCHAR(20) NOT NULL,
                activo TINYINT(1) NOT NULL DEFAULT 1,
                creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (id_usuario),
                UNIQUE KEY portal_usuarios_email_unique (email),
                CONSTRAINT portal_usuarios_rol_valido
                    CHECK (rol IN ('visita', 'administrador'))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        connection.commit()
    finally:
        cursor.close()


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id_usuario": int(row["id_usuario"]),
        "email": row["email"],
        "rol": row["rol"],
        "activo": bool(row["activo"]),
        "creado_en": row.get("creado_en"),
        "actualizado_en": row.get("actualizado_en"),
    }


def get_user_by_email(connection, email: Any) -> dict[str, Any] | None:
    try:
        normalized = normalize_email(email)
    except PortalUserError:
        return None
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id_usuario, email, password_hash, rol, activo,
                   creado_en, actualizado_en
            FROM portal_usuarios
            WHERE email = %s
            LIMIT 1
            """,
            (normalized,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def authenticate_user(connection, email: Any, password: Any) -> dict[str, Any] | None:
    user = get_user_by_email(connection, email)
    if not user or not bool(user["activo"]):
        return None
    if not check_password_hash(user["password_hash"], str(password or "")):
        return None
    return public_user(user)


def list_users(connection) -> list[dict[str, Any]]:
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id_usuario, email, rol, activo, creado_en, actualizado_en
            FROM portal_usuarios
            ORDER BY email
            """
        )
        return [public_user(row) for row in cursor.fetchall()]
    finally:
        cursor.close()


def create_user(connection, email: Any, password: Any, role: Any) -> dict[str, Any]:
    normalized = normalize_email(email)
    validated_password = validate_password(password)
    validated_role = validate_role(role)
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO portal_usuarios (email, password_hash, rol, activo)
            VALUES (%s, %s, %s, 1)
            """,
            (
                normalized,
                generate_password_hash(validated_password),
                validated_role,
            ),
        )
        connection.commit()
        user_id = cursor.lastrowid
    except mysql.connector.IntegrityError as error:
        connection.rollback()
        raise DuplicatePortalUserError("El usuario ya existe") from error
    finally:
        cursor.close()

    user = get_user_by_email(connection, normalized)
    if not user:
        raise PortalUserError(f"No fue posible recuperar el usuario {user_id}")
    return public_user(user)


def update_user(
    connection,
    user_id: int,
    *,
    role: Any | None = None,
    active: Any | None = None,
    password: Any | None = None,
) -> dict[str, Any] | None:
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id_usuario, email, password_hash, rol, activo,
                   creado_en, actualizado_en
            FROM portal_usuarios
            WHERE id_usuario = %s
            FOR UPDATE
            """,
            (int(user_id),),
        )
        current = cursor.fetchone()
        if not current:
            connection.rollback()
            return None

        next_role = validate_role(role) if role is not None else current["rol"]
        if active is not None and not isinstance(active, bool):
            raise PortalUserError("Estado activo inválido")
        next_active = active if active is not None else bool(current["activo"])
        if (
            current["rol"] == "administrador"
            and bool(current["activo"])
            and (next_role != "administrador" or not next_active)
        ):
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM portal_usuarios
                WHERE rol = 'administrador' AND activo = 1
                """
            )
            if int(cursor.fetchone()["total"]) <= 1:
                connection.rollback()
                raise LastAdministratorError(
                    "Debe mantenerse al menos un administrador local activo"
                )

        assignments = ["rol = %s", "activo = %s"]
        params: list[Any] = [next_role, int(next_active)]
        if password not in (None, ""):
            assignments.append("password_hash = %s")
            params.append(generate_password_hash(validate_password(password)))
        params.append(int(user_id))
        cursor.execute(
            f"UPDATE portal_usuarios SET {', '.join(assignments)} WHERE id_usuario = %s",
            tuple(params),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()

    updated = get_user_by_email(connection, current["email"])
    return public_user(updated) if updated else None
