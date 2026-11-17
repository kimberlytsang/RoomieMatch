"""JSON endpoints for messaging. Business rules live in services.py."""

from django.http import JsonResponse
from django.utils import dateformat, timezone
from django.views.decorators.http import require_GET

from config.api import authenticated_only, error

from . import services
from .models import Conversation


@require_GET
@authenticated_only
def conversation_messages(request, conversation_id):
    """Return messages created after ``after`` for one participant's thread.

    The conversation page polls this small endpoint instead of refreshing the
    whole document, so a draft in the compose box is never lost.
    """
    if request.user.is_admin:
        return error(403, "Seeker access required.")

    after = request.GET.get("after", "0")
    if not after.isdigit():
        return error(400, "after must be a message ID.")

    try:
        conversation = services.get_conversation_for_user(request.user, conversation_id)
    except Conversation.DoesNotExist:
        return error(404, "Conversation unavailable.")

    messages = conversation.messages.filter(message_id__gt=int(after)).order_by(
        "sent_at", "message_id"
    )
    return JsonResponse({
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
