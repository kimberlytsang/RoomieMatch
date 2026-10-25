"""Service layer: business logic for accounts. Views call these functions;
only services and models touch the database."""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from .models import User

MAX_PASSWORD_LENGTH = 128


class InvalidEmail(Exception):
    pass


class DuplicateEmail(Exception):
    pass


class WeakPassword(Exception):
    def __init__(self, reasons):
        super().__init__(" ".join(reasons))
        self.reasons = reasons


def register_user(email, password):
    """US-01: create a user account. Passwords are hashed by Django before saving.

    Raises InvalidEmail, WeakPassword or DuplicateEmail."""
    email = email.strip()
    try:
        validate_email(email)
    except ValidationError:
        raise InvalidEmail("Enter a valid email address.")

    if len(password) > MAX_PASSWORD_LENGTH:
        raise WeakPassword([f"Password must be at most {MAX_PASSWORD_LENGTH} characters."])
    try:
        validate_password(password)
    except ValidationError as exc:
        raise WeakPassword(list(exc.messages))

    # Email is unique ignoring case (citext). Check first for a clean error, and
    # still catch the database constraint in case two sign-ups race.
    if User.objects.filter(email=email).exists():
        raise DuplicateEmail("An account with this email already exists.")
    try:
        with transaction.atomic():
            return User.objects.create_user(email, password)
    except IntegrityError:
        raise DuplicateEmail("An account with this email already exists.")


def authenticate_user(request, email, password):
    """US-02: return the user for valid credentials, otherwise None.

    The caller does not learn whether the email or the password was wrong."""
    return authenticate(request, email=email.strip(), password=password)
