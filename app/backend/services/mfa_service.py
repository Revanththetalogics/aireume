"""TOTP MFA helpers for tenant admins and platform roles."""
from __future__ import annotations

import os

import pyotp


ISSUER = os.getenv("MFA_ISSUER", "ARIA")


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(email: str, secret: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=ISSUER)


def verify_code(secret: str | None, code: str | None) -> bool:
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(str(code).strip(), valid_window=1)
