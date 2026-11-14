"""Business rules and database queries for direct messaging."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max, Q

from .models import Conversation, Message


def _ordered_pair(first_user, second_user):
    """Return users in the stable order required by Conversation's constraint."""
    if first_user.pk == second_user.pk:
        raise ValidationError({"recipient": "You cannot message yourself."})
    return (
        (first_user, second_user)
        if str(first_user.pk) < str(second_user.pk)
        else (second_user, first_user)
    )


def send_message(sender, recipient, body):
    """Create a message and its one-to-one conversation when needed."""
    if not isinstance(body, str) or not body.strip():
        raise ValidationError({"body": "Enter a message."})

    user_a, user_b = _ordered_pair(sender, recipient)
    with transaction.atomic():
        try:
            conversation, _ = Conversation.objects.get_or_create(
                user_a=user_a, user_b=user_b
            )
        except IntegrityError:
            # A concurrent first message may have created the same pair.
            conversation = Conversation.objects.get(user_a=user_a, user_b=user_b)
        message = Message.objects.create(
            conversation=conversation, sender=sender, body=body.strip()
        )
    return conversation, message


def list_conversations(user):
    """Return the signed-in user's conversations, newest activity first."""
    return (
        Conversation.objects.filter(Q(user_a=user) | Q(user_b=user))
        .select_related(
            "user_a__profile", "user_b__profile", "user_a__preference", "user_b__preference"
        )
        .annotate(last_message_at=Max("messages__sent_at"))
        .order_by("-last_message_at")
    )


def get_conversation_for_user(user, conversation_id):
    """Return a conversation only when the requester is a participant."""
    return (
        Conversation.objects.filter(
            Q(user_a=user) | Q(user_b=user), conversation_id=conversation_id
        )
        .select_related(
            "user_a__profile", "user_b__profile", "user_a__preference", "user_b__preference"
        )
        .prefetch_related("messages__sender")
        .get()
    )


def other_participant(conversation, user):
    """Return the other user in a conversation the requester can access."""
    if conversation.user_a_id == user.pk:
        return conversation.user_b
    if conversation.user_b_id == user.pk:
        return conversation.user_a
    raise Conversation.DoesNotExist


def participant_name(user):
    """Prefer a profile display name; fall back to the account email."""
    profile = getattr(user, "profile", None)
    return profile.display_name if profile else user.email
