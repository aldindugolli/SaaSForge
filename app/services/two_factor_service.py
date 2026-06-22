import base64
import io
import secrets

import pyotp
import qrcode
from flask import current_app


class TwoFactorService:
    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(secret: str, email: str) -> str:
        issuer = current_app.config.get("APP_NAME", "SaaSForge")
        return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

    @staticmethod
    def generate_qr_code_base64(secret: str, email: str) -> str:
        uri = TwoFactorService.get_provisioning_uri(secret, email)
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        if not secret or not code:
            return False
        return pyotp.TOTP(secret).verify(code, valid_window=1)

    @staticmethod
    def generate_backup_codes(count: int = 8) -> list[str]:
        codes = set()
        while len(codes) < count:
            codes.add(secrets.token_hex(4))
        return sorted(codes)

    @staticmethod
    def verify_backup_code(backup_codes: list[str], code: str) -> bool:
        return code in (backup_codes or [])
