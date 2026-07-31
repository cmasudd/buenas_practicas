import unittest
import os
import time
from datetime import datetime
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import Flask

from historico_v3 import (
    create_historico_v3_blueprint,
    _decode_cursor,
    _encode_cursor,
    _parse_date,
    _serialize,
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

    def test_dates(self):
        self.assertEqual(_parse_date("2026-07-27", "fecha").isoformat(), "2026-07-27")

    def test_csv_null_is_empty(self):
        self.assertEqual(_serialize(None), "")

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
        }):
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


if __name__ == "__main__":
    unittest.main()
