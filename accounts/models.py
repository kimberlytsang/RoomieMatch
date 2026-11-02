import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from .fields import CIEmailField
from django.db import models


class Role(models.TextChoices):
    SEEKER = "SEEKER", "Seeker"
    ADMIN = "ADMIN", "App Administrator"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password, role=Role.SEEKER):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email), role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_admin(self, email, password):
        return self.create_user(email, password, role=Role.ADMIN)


class User(AbstractBaseUser):
    """users table. Passwords are stored hashed in the password_hash column."""

    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = CIEmailField(unique=True)  # case-insensitive unique (citext)
    password = models.CharField("password", max_length=128, db_column="password_hash")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.SEEKER)

    last_login = None  # not part of the ER design

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    def __str__(self):
        return self.email


class Session(models.Model):
    """sessions table from the ER diagram.

    Not yet used: login currently relies on Django's built-in session store.
    See docs/DESIGN_CHANGES.md for the open decision.
    """

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "sessions"
        indexes = [models.Index(fields=["expires_at"])]

class SupportRequest(models.Model):
    subject = models.CharField(max_length=100)
    body = models.CharField(max_length=1000)
    user = models.CharField(max_length=100)

    def __str__(self):
        return self.subject
