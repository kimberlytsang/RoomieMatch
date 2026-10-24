import uuid

from django.conf import settings
from django.db import models


class Category(models.TextChoices):
    APP_ISSUE = "APP_ISSUE", "App issue"
    USER_ISSUE = "USER_ISSUE", "User issue"
    USER_FEEDBACK = "USER_FEEDBACK", "User feedback"


class Status(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    RESOLVED = "RESOLVED", "Resolved"


class SupportRequest(models.Model):
    request_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_requests"
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "support_requests"
