"""Password strength policy used at registration, reset, and change-password."""
import re

_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")

MIN_LENGTH = 10


def validate_password_strength(password: str) -> None:
    """Raise ValueError if the password does not meet policy."""
    if not password or len(password) < MIN_LENGTH:
        raise ValueError(f"Password must be at least {MIN_LENGTH} characters")
    if not _UPPER.search(password):
        raise ValueError("Password must include an uppercase letter")
    if not _LOWER.search(password):
        raise ValueError("Password must include a lowercase letter")
    if not _DIGIT.search(password):
        raise ValueError("Password must include a number")
