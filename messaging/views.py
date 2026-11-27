"""JSON endpoints for messaging. Business rules live in services.py."""

from django.http import JsonResponse
from django.urls import reverse
from django.utils import dateformat, timezone
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Max

from config.api import authenticated_only, error

from . import services
from .models import Conversation, ConversationVisibility, Message


@require_GET
@authenticated_only
def conversation_messages(request, conversation_id):
    """Return messages created after ``after`` for one participant's thread.

    The conversation page polls this small endpoint instead of refreshing the
    whole document, so a draft in the compose box is never lost.
    """
    after = request.GET.get("after", "0")
    if not after.isdigit():
        return error(400, "after must be a message ID.")

    try:
        conversation = services.get_conversation_for_user(request.user, conversation_id)
    except Conversation.DoesNotExist:
        return error(404, "Conversation unavailable.")

    visible = services.visible_messages(conversation, request.user)
    messages = visible.filter(message_id__gt=int(after)).order_by(
        "sent_at", "message_id"
    )
    return JsonResponse({
        "visible_message_ids": list(visible.values_list("message_id", flat=True)),
        "messages": [
            {
                "message_id": message.message_id,
                "body": message.body,
                "sender_id": str(message.sender_id),
                "sent_at_display": dateformat.format(
                    timezone.localtime(message.sent_at), "g:i A"
                ),
            }
            for message in messages
        ]
    })


@require_GET
@authenticated_only
def conversation_sidebar(request):
    """Return the requester's chat list so new conversations appear without refresh."""
    conversations = []
    for conversation in services.visible_conversations(request.user):
        other_user = services.other_participant(conversation, request.user)
        last_message = services.visible_messages(conversation, request.user).order_by("-sent_at", "-message_id").first()
        profile = getattr(other_user, "profile", None)
        conversations.append(
            {
                "conversation_id": str(conversation.conversation_id),
                "is_pinned": conversation.is_pinned,
                "other_name": services.participant_name(other_user),
                "last_message": last_message.body if last_message else "Start a conversation",
                "url": reverse(
                    "conversation-detail", kwargs={"conversation_id": conversation.conversation_id}
                ),
                "profile_photo_url": (
                    reverse("profile-photo", kwargs={"user_id": other_user.user_id})
                    if profile and profile.profile_picture
                    else ""
                ),
            }
        )
    return JsonResponse({"conversations": conversations})


@require_POST
@authenticated_only
def pin_conversation(request, conversation_id):
    try:
        conversation = services.get_conversation_for_user(request.user, conversation_id)
    except Conversation.DoesNotExist:
        return error(404, "Conversation unavailable.")
    action = request.POST.get("action")
    if action not in ("pin", "unpin"):
        return error(400, "Invalid action.")
    if not services.visible_messages(conversation, request.user).exists():
        return error(404, "Conversation unavailable.")
    visibility, _ = ConversationVisibility.objects.get_or_create(conversation=conversation, user=request.user)
    visibility.is_pinned = action == "pin"
    visibility.save(update_fields=["is_pinned"])
    return JsonResponse({"is_pinned": visibility.is_pinned})


@require_POST
@authenticated_only
def remove_message(request, conversation_id, message_id):
    try:
        conversation = services.get_conversation_for_user(request.user, conversation_id)
        message = services.visible_messages(conversation, request.user).get(message_id=message_id)
    except (Conversation.DoesNotExist, Message.DoesNotExist):
        return error(404, "Message unavailable.")
    if request.POST.get("action") == "unsend":
        if message.sender_id != request.user.pk:
            return error(403, "Only the sender can unsend a message.")
        message.delete()
    elif request.POST.get("action") == "delete":
        message.hidden_for.add(request.user)
    else:
        return error(400, "Invalid action.")
    return JsonResponse({"ok": True})


@require_POST
@authenticated_only
def remove_conversation(request, conversation_id):
    try:
        conversation = services.get_conversation_for_user(request.user, conversation_id)
    except Conversation.DoesNotExist:
        return error(404, "Conversation unavailable.")
    latest = conversation.messages.aggregate(last=Max("message_id"))["last"] or 0
    ConversationVisibility.objects.update_or_create(conversation=conversation, user=request.user, defaults={"hidden_through_id": latest, "is_pinned": False})
    return JsonResponse({"ok": True})
