import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Conversation(models.Model):
    """A one-to-one thread. user_a_id < user_b_id and the pair is unique, so two
    users always share exactly one conversation."""

    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_a"
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_b"
    )

    class Meta:
        db_table = "conversations"
        constraints = [
            models.UniqueConstraint(fields=["user_a", "user_b"], name="uniq_conversation_pair"),
            models.CheckConstraint(
                condition=Q(user_a__lt=F("user_b")), name="conversation_users_ordered_and_distinct"
            ),
        ]


class Message(models.Model):
    message_id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )  # must be one of the conversation's two users (checked in the service layer)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages"
        indexes = [models.Index(fields=["conversation", "sent_at"])]
        constraints = [
            models.CheckConstraint(condition=Q(body__regex=r"\S"), name="message_body_not_blank"),
        ]
