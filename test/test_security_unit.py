import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pydantic import BaseModel, ValidationError

class TestSecurityUnit(unittest.IsolatedAsyncioTestCase):
    def test_password_length_validator_72_bytes_ok(self):
        from app.core.security import PasswordStr

        class SchemaTest(BaseModel):
            password: PasswordStr

        pwd_72 = "a" * 72
        schema = SchemaTest(password=pwd_72)
        self.assertEqual(schema.password, pwd_72)

    def test_password_length_validator_73_bytes_fails(self):
        from app.core.security import PasswordStr

        class SchemaTest(BaseModel):
            password: PasswordStr

        pwd_73 = "a" * 73
        with self.assertRaises(ValidationError) as ctx:
            SchemaTest(password=pwd_73)
        self.assertIn("72 bytes", str(ctx.exception))

    def test_password_length_validator_utf8_multibyte(self):
        from app.core.security import PasswordStr

        class SchemaTest(BaseModel):
            password: PasswordStr

        # Multi-byte UTF-8 character: "ñ" is 2 bytes in UTF-8
        pwd_36_chars = "ñ" * 36
        self.assertEqual(len(pwd_36_chars.encode("utf-8")), 72)
        schema = SchemaTest(password=pwd_36_chars)
        self.assertEqual(schema.password, pwd_36_chars)

        pwd_37_chars = "ñ" * 37
        with self.assertRaises(ValidationError):
            SchemaTest(password=pwd_37_chars)

    async def test_hash_and_verify_password(self):
        from app.core.security import hash_password, verify_password

        pwd = "mi_clave_segura_123"
        hashed = await hash_password(pwd)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))
        
        is_valid = await verify_password(pwd, hashed)
        self.assertTrue(is_valid)

        is_invalid = await verify_password("clave_erronea", hashed)
        self.assertFalse(is_invalid)

if __name__ == "__main__":
    unittest.main()
