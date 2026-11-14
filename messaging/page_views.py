"""HTML views for sending messages and reading conversations."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from profiles import services as profile_services
from profiles.models import Profile

from . import services
from .models import Conversation


def _roommate_detail_context(roommate, message_error="", message_body=""):
    return {
        "roommate": roommate,
        "message_error": message_error,
        "message_body": message_body,
    }


@login_required(login_url="login-page")
@require_POST
def send_message_page(request, user_id):
    """US-09: send a message from an available roommate's profile."""
    try:
        roommate = profile_services.get_available_roommate(request.user, user_id)
    except Profile.DoesNotExist:
        return render(request, "profiles/roommate_unavailable.html", status=404)

    body = request.POST.get("body", "")
    try:
        conversation, _ = services.send_message(request.user, roommate.user, body)
    except ValidationError as exc:
        return render(
            request,
            "profiles/roommate_detail.html",
            _roommate_detail_context(
                roommate,
                message_error=exc.message_dict.get("body", [exc.messages[0]])[0],
                message_body=body,
            ),
            status=400,
        )
    return redirect("conversation-detail", conversation_id=conversation.conversation_id)


@login_required(login_url="login-page")
def conversation_list(request):
    """US-11: list the requester's persisted conversations."""
    conversations = list(services.list_conversations(request.user))
    for conversation in conversations:
        conversation.other_user = services.other_participant(conversation, request.user)
        conversation.other_name = services.participant_name(conversation.other_user)
    return render(request, "messaging/conversation_list.html", {"conversations": conversations})


@login_required(login_url="login-page")
def conversation_detail(request, conversation_id):
    """US-11: show messages in one conversation to a participant only."""
    try:
        conversation = services.get_conversation_for_user(request.user, conversation_id)
    except Conversation.DoesNotExist:
        return render(request, "messaging/conversation_unavailable.html", status=404)

    other_user = services.other_participant(conversation, request.user)
    return render(
        request,
        "messaging/conversation_detail.html",
        {
            "conversation": conversation,
            "other_user": other_user,
            "other_name": services.participant_name(other_user),
            "messages": conversation.messages.all().order_by("sent_at", "message_id"),
        },
    )
