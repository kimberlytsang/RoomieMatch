"""HTML views for sending messages and reading conversations."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import SupportRequest, User
from profiles import services as profile_services
from profiles.models import Profile

from . import services
from .models import Conversation


def _roommate_detail_context(
    roommate, message_error="", message_body="", message_attempted=False
):
    return {
        "roommate": roommate,
        "message_error": message_error,
        "message_body": message_body,
        "message_attempted": message_attempted,
    }


def _conversations_for_sidebar(user):
    """Prepare the signed-in user's conversations for the Chats sidebar."""
    conversations = services.visible_conversations(user)
    for conversation in conversations:
        conversation.other_user = services.other_participant(conversation, user)
        conversation.other_name = services.participant_name(conversation.other_user)
        conversation.last_message = services.visible_messages(conversation, user).order_by(
            "-sent_at", "-message_id"
        ).first()
    return conversations


def _conversation_context(request, conversation, conversations, *, message_error="", message_body=""):
    """Build the shared template context for the selected conversation."""
    other_user = services.other_participant(conversation, request.user)
    return {
        "conversation": conversation,
        "is_pinned": any(item.pk == conversation.pk and item.is_pinned for item in conversations),
        "conversations": conversations,
        "other_user": other_user,
        "other_name": services.participant_name(other_user),
        "messages": services.visible_messages(conversation, request.user).order_by("sent_at", "message_id"),
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
                message_attempted=True,
            ),
            status=400,
        )
    return redirect("conversation-detail", conversation_id=conversation.conversation_id)


@login_required(login_url="login-page")
def conversation_list(request):
    """US-11: list the requester's persisted conversations."""
    conversations = _conversations_for_sidebar(request.user)
    if conversations:
        return render(
            request,
            "messaging/conversation_detail.html",
            _conversation_context(request, conversations[0], conversations),
        )
    return render(request, "messaging/conversation_list.html", {"conversations": conversations})


@login_required(login_url="login-page")
@require_http_methods(["GET", "POST"])
def conversation_detail(request, conversation_id):
    """US-11: show a conversation and allow either participant to reply."""
    try:
        conversation = services.get_conversation_for_user(request.user, conversation_id)
    except Conversation.DoesNotExist:
        return render(request, "messaging/conversation_unavailable.html", status=404)

    conversations = _conversations_for_sidebar(request.user)
    if request.method == "POST":
        other_user = services.other_participant(conversation, request.user)
        body = request.POST.get("body", "")
        try:
            services.send_message(request.user, other_user, body)
        except ValidationError as exc:
            return render(
                request,
                "messaging/conversation_detail.html",
                _conversation_context(
                    request,
                    conversation,
                    conversations,
                    message_error=exc.message_dict.get("body", [exc.messages[0]])[0],
                    message_body=body,
                ),
                status=400,
            )
        return redirect("conversation-detail", conversation_id=conversation.conversation_id)

    return render(
        request,
        "messaging/conversation_detail.html",
        _conversation_context(request, conversation, conversations),
    )


@login_required(login_url="login-page")
@require_http_methods(["GET", "POST"])
def support_request_message(request, request_id):
    """Let an administrator contact the account that submitted a support request."""
    if not request.user.is_admin:
        return redirect("home")

    try:
        support_request = SupportRequest.objects.get(pk=request_id)
        recipient = User.objects.get(email__iexact=support_request.user)
    except (SupportRequest.DoesNotExist, User.DoesNotExist):
        return render(request, "messaging/conversation_unavailable.html", status=404)

    values = {"support_request": support_request, "recipient": recipient, "message_body": ""}
    if request.method == "POST":
        body = request.POST.get("body", "")
        try:
            conversation, _ = services.send_message(request.user, recipient, body)
        except ValidationError as exc:
            values.update(
                message_error=exc.message_dict.get("body", [exc.messages[0]])[0],
                message_body=body,
            )
            return render(request, "messaging/support_message_compose.html", values, status=400)
        return redirect("conversation-detail", conversation_id=conversation.conversation_id)

    return render(request, "messaging/support_message_compose.html", values)
