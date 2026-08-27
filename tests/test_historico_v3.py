import unittest
import hashlib
import os
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import Flask
from werkzeug.security import generate_password_hash

from historico_v3 import (
    create_historico_v3_blueprint,
    _api_key_matches,
    _decode_cursor,
    _decode_preview_cursor,
    _encode_cursor,
    _encode_preview_cursor,
    _parse_date,
    _merge_wide_rows,
    _serialize,
    _safe_filename_part,
    _validate_microsoft_issuer,
)


class CursorTests(unittest.TestCase):
    def test_cursor_round_trip(self):
        fecha = datetime(2026, 7, 27, 12, 30, 45)
        encoded = _encode_cursor(1028, fecha, 12345)
        self.assertEqual(_decode_cursor(encoded), (1028, fecha, 12345))

    def test_invalid_cursor(self):
        with self.assertRaises(ValueError):
            _decode_cursor("no-es-un-cursor")

    def test_preview_cursor_round_trip(self):
        row = {
            "fecha": datetime(2026, 5, 6, 15, 42, 53),
            "codigo_interno": "HIRI-01",
            "fecha_insercion": datetime(2026, 5, 6, 15, 42, 54),
            "id_sesion": "Sin sesión",
            "id_dato_concatenado": "11, 10",
        }
        cursor = _encode_preview_cursor(row)
        self.assertEqual(_decode_preview_cursor(cursor), (
            "2026-05-06T15:42:53",
            "HIRI-01",
            "2026-05-06T15:42:54",
            "Sin sesión",
            "11, 10",
        ))

    def test_invalid_preview_cursor(self):
        with self.assertRaises(ValueError):
            _decode_preview_cursor("no-es-un-cursor")

    def test_dates(self):
        self.assertEqual(_parse_date("2026-07-27", "fecha").isoformat(), "2026-07-27")

    def test_csv_null_is_empty(self):
        self.assertEqual(_serialize(None), "")

    def test_powerbi_api_key_hash(self):
        expected_hash = hashlib.sha256(b"test-powerbi-key").hexdigest()
        self.assertTrue(_api_key_matches("test-powerbi-key", expected_hash))
        self.assertFalse(_api_key_matches("wrong-key", expected_hash))
        self.assertFalse(_api_key_matches("", expected_hash))
        self.assertFalse(_api_key_matches("test-powerbi-key", "invalid-hash"))

    def test_safe_download_filename(self):
        self.assertEqual(_safe_filename_part("AIRE-01"), "AIRE-01")
        self.assertEqual(_safe_filename_part("Estación / Norte"), "Estaci-n-Norte")

    def test_microsoft_v2_issuer(self):
        tenant = "9188040d-6c67-4c5b-b112-36a304b66dad"
        _validate_microsoft_issuer({
            "tid": tenant,
            "ver": "2.0",
            "iss": f"https://login.microsoftonline.com/{tenant}/v2.0",
        })

    def test_microsoft_rejects_wrong_issuer(self):
        with self.assertRaises(ValueError):
            _validate_microsoft_issuer({
                "tid": "9188040d-6c67-4c5b-b112-36a304b66dad",
                "ver": "2.0",
                "iss": "https://example.invalid/",
            })

    def test_wide_rows_merge_sensor_series_by_date(self):
        first = datetime(2026, 7, 31, 15, 15, 30)
        previous = datetime(2026, 7, 31, 15, 10, 30)
        common = {
            "fecha_insercion": first,
            "id_sesion": None,
            "sesion_descripcion": None,
            "fecha_inicio": None,
            "ubicacion": None,
        }
        streams = [
            iter([
                {**common, "fecha": first, "id_dato": 3,
                 "unidad_medida": "Sensor A [Temperatura (°C)]", "valor": 12.5},
                {**common, "fecha": previous, "fecha_insercion": previous,
                 "id_dato": 1, "unidad_medida": "Sensor A [Temperatura (°C)]",
                 "valor": 12.0},
            ]),
            iter([
                {**common, "fecha": first, "id_dato": 4,
                 "unidad_medida": "Sensor B [Humedad (%)]", "valor": 70},
            ]),
        ]
        rows = list(_merge_wide_rows(streams, {
            "id_proyecto": 12,
            "codigo_interno": "AIRE-01",
            "descripcion": None,
        }))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["fecha"], first)
        self.assertEqual(rows[0]["id_sesion"], "Sin sesión")
        self.assertEqual(rows[0]["Sensor A [Temperatura (°C)]"], "12.5")
        self.assertEqual(rows[0]["Sensor B [Humedad (%)]"], "70")
        self.assertEqual(rows[0]["id_dato_concatenado"], "4, 3")

    def test_wide_rows_uses_stable_fallback_for_missing_sensor_metadata(self):
        timestamp = datetime(2026, 5, 6, 15, 42, 53)
        rows = list(_merge_wide_rows([
            iter([{
                "fecha": timestamp,
                "fecha_insercion": timestamp,
                "id_dato": 10,
                "id_sensor": 28,
                "id_variable": 3,
                "id_sesion": None,
                "sesion_descripcion": None,
                "fecha_inicio": None,
                "ubicacion": None,
                "unidad_medida": None,
                "valor": 21.5,
            }]),
        ], {
            "id_proyecto": 2,
            "codigo_interno": "HIRI-01",
            "descripcion": None,
        }))

        self.assertEqual(rows[0]["Sensor 28 [Variable 3]"], "21.5")


class MicrosoftLoginTests(unittest.TestCase):
    @patch("historico_v3.PyJWKClient.get_signing_key_from_jwt")
    def test_microsoft_token_creates_secure_session(self, signing_key):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        signing_key.return_value.key = private_key.public_key()
        tenant = "9188040d-6c67-4c5b-b112-36a304b66dad"
        client_id = "test-client-id"
        now = int(time.time())
        token = jwt.encode(
            {
                "aud": client_id,
                "exp": now + 300,
                "iat": now,
                "iss": f"https://login.microsoftonline.com/{tenant}/v2.0",
                "sub": "user-id",
                "tid": tenant,
                "ver": "2.0",
                "preferred_username": "usuario@example.com",
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )
        with patch.dict(os.environ, {
            "HISTORICO_SESSION_SECRET": "test-session-secret",
            "HISTORICO_MICROSOFT_CLIENT_ID": client_id,
        }), patch("historico_v3.mysql.connector.connect"), patch(
            "historico_v3.get_user_by_email", return_value=None
        ):
            app = Flask(__name__)
            app.register_blueprint(create_historico_v3_blueprint({}))
            response = app.test_client().post(
                "/v3/auth/microsoft",
                json={"id_token": token},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["provider"], "microsoft")
        cookie = response.headers["Set-Cookie"]
        self.assertIn("Secure", cookie)
        self.assertIn("HttpOnly", cookie)


class LegacyVisitorLoginTests(unittest.TestCase):
    def test_legacy_admin_credentials_are_presented_as_visitor(self):
        connection = MagicMock()
        with patch.dict(os.environ, {
            "HISTORICO_SESSION_SECRET": "test-session-secret",
            "HISTORICO_USER": "admin",
            "HISTORICO_PASSWORD_HASH": generate_password_hash("admin"),
        }), patch(
            "historico_v3.mysql.connector.connect",
            return_value=connection,
        ), patch("historico_v3.authenticate_portal_user", return_value=None):
            app = Flask(__name__)
            app.register_blueprint(create_historico_v3_blueprint({}))
            response = app.test_client().post(
                "/v3/auth/login",
                json={"username": "admin", "password": "admin"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"], "visita")
        self.assertEqual(response.get_json()["role"], "visita")


class PowerBIAuthorizationTests(unittest.TestCase):
    def test_powerbi_endpoint_requires_server_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            app = Flask(__name__)
            app.register_blueprint(create_historico_v3_blueprint({}))
            response = app.test_client().get(
                "/v3/powerbi/proyectos/13/datos"
                "?fecha_inicio=2025-01-01&fecha_fin=2026-08-03"
            )

        self.assertEqual(response.status_code, 503)

    def test_powerbi_endpoint_rejects_wrong_key_before_database(self):
        expected_hash = hashlib.sha256(b"correct-key").hexdigest()
        with patch.dict(os.environ, {"POWERBI_API_KEY_HASH": expected_hash}):
            app = Flask(__name__)
            app.register_blueprint(create_historico_v3_blueprint({}))
            response = app.test_client().get(
                "/v3/powerbi/proyectos/13/datos"
                "?fecha_inicio=2025-01-01&fecha_fin=2026-08-03",
                headers={"X-API-Key": "wrong-key"},
            )

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
