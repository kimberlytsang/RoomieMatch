"""Service layer: business logic for accounts. Views call these functions;
only services and models touch the database."""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from .models import User,SupportRequest

MAX_PASSWORD_LENGTH = 128


class InvalidEmail(Exception):
    pass


class DuplicateEmail(Exception):
    pass


class WeakPassword(Exception):
    def __init__(self, reasons):
        super().__init__(" ".join(reasons))
        self.reasons = reasons


class IncorrectCurrentPassword(Exception):
    pass


class PasswordUnchanged(Exception):
    pass


def _validate_password(password, user=None):
    if len(password) > MAX_PASSWORD_LENGTH:
        raise WeakPassword([f"Password must be at most {MAX_PASSWORD_LENGTH} characters."])
    password_errors = []
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        password_errors.extend(exc.messages)
    if not any(character.isupper() for character in password):
        password_errors.append("Password must include at least one uppercase letter.")
    if not any(character.isdigit() for character in password):
        password_errors.append("Password must include at least one number.")
    if not any(not character.isalnum() and not character.isspace() for character in password):
        password_errors.append("Password must include at least one special character.")
    if password_errors:
        raise WeakPassword(password_errors)


def register_user(email, password):
    """US-01: create a user account. Passwords are hashed by Django before saving.

    Raises InvalidEmail, WeakPassword or DuplicateEmail."""
    email = email.strip()
    try:
        validate_email(email)
    except ValidationError:
        raise InvalidEmail("Enter a valid email address.")

    _validate_password(password)

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


def change_password(user, current_password, new_password):
    """Validate the current password and save a new one without ending the session."""
    if not user.check_password(current_password):
        raise IncorrectCurrentPassword
    if user.check_password(new_password):
        raise PasswordUnchanged
    _validate_password(new_password, user=user)
    user.set_password(new_password)
    user.save(update_fields=["password"])


def submit_support_request(user,subject,body):
    """US-18: Create the support request entry in the db. Not going to worry about duplicates for now."""
    SupportRequest.objects.create(user=user, subject=subject, body=body)
def delete_account(user):
    """US-14: permanently delete a user and their cascading related records."""
    with transaction.atomic():
        user.delete()
