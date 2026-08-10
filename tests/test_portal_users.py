import unittest

from portal_users import (
    PortalUserError,
    normalize_email,
    public_user,
    validate_password,
    validate_role,
)


class PortalUsersTests(unittest.TestCase):
    def test_normalizes_email(self):
        self.assertEqual(normalize_email(" Persona@Ejemplo.CL "), "persona@ejemplo.cl")

    def test_rejects_invalid_email_role_and_short_password(self):
        with self.assertRaises(PortalUserError):
            normalize_email("correo-invalido")
        with self.assertRaises(PortalUserError):
            validate_role("superusuario")
        with self.assertRaises(PortalUserError):
            validate_password("corta")

    def test_public_user_never_returns_password_hash(self):
        result = public_user({
            "id_usuario": 3,
            "email": "persona@ejemplo.cl",
            "password_hash": "secreto",
            "rol": "visita",
            "activo": 1,
            "creado_en": None,
            "actualizado_en": None,
        })
        self.assertNotIn("password_hash", result)
        self.assertEqual(result["rol"], "visita")


if __name__ == "__main__":
    unittest.main()
