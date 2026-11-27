"""Business rules and database queries for direct messaging."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max, Q

from .models import Conversation, ConversationVisibility, Message

MAX_MESSAGE_LENGTH = 2000


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
    if len(body) > MAX_MESSAGE_LENGTH:
        raise ValidationError({
            "body": f"Message must be {MAX_MESSAGE_LENGTH} characters or fewer."
        })

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


def visible_messages(conversation, user):
    cutoff = ConversationVisibility.objects.filter(conversation=conversation, user=user).values_list("hidden_through_id", flat=True).first() or 0
    return conversation.messages.filter(message_id__gt=cutoff).exclude(hidden_for=user)


def visible_conversations(user):
    pinned = set(ConversationVisibility.objects.filter(user=user, is_pinned=True).values_list("conversation_id", flat=True))
    conversations = [conversation for conversation in list_conversations(user) if visible_messages(conversation, user).exists()]
    for conversation in conversations:
        conversation.is_pinned = conversation.pk in pinned
    return sorted(conversations, key=lambda conversation: not conversation.is_pinned)


def hidden_conversations(user):
    """Return conversations hidden by this user that have not received a new message."""
    hidden_cutoffs = dict(
        ConversationVisibility.objects.filter(user=user, hidden_through_id__gt=0)
        .values_list("conversation_id", "hidden_through_id")
    )
    conversations = list_conversations(user).filter(pk__in=hidden_cutoffs)
    hidden = []
    for conversation in conversations:
        cutoff = hidden_cutoffs[conversation.pk]
        if conversation.messages.filter(message_id__gt=cutoff).exists():
            continue
        conversation.other_user = other_participant(conversation, user)
        conversation.other_name = participant_name(conversation.other_user)
        conversation.last_message = conversation.messages.filter(
            message_id__lte=cutoff
        ).exclude(hidden_for=user).order_by("-message_id").first()
        hidden.append(conversation)
    return hidden


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


def users_have_conversation(user, other_user_id):
    """Return whether two users have a conversation."""
    return Conversation.objects.filter(
        Q(user_a=user, user_b_id=other_user_id)
        | Q(user_b=user, user_a_id=other_user_id)
    ).exists()


def unhide_conversation(user, conversation_id):
    """Restore a conversation hidden by this user, including its message history."""
    with transaction.atomic():
        try:
            conversation = get_conversation_for_user(user, conversation_id)
            visibility = ConversationVisibility.objects.select_for_update().get(
                conversation=conversation, user=user, hidden_through_id__gt=0
            )
        except (Conversation.DoesNotExist, ConversationVisibility.DoesNotExist):
            raise Conversation.DoesNotExist

        if conversation.messages.filter(
            message_id__gt=visibility.hidden_through_id
        ).exists():
            raise Conversation.DoesNotExist

        visibility.hidden_through_id = 0
        visibility.save(update_fields=["hidden_through_id"])
        return conversation


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
