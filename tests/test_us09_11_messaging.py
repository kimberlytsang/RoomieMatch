"""US-09 and US-11 tests for sending and reading persisted conversations."""

import pytest
from django.core.exceptions import ValidationError
from django.test import Client

from accounts.models import SupportRequest, User
from messaging.models import Conversation, Message
from messaging import services as messaging_services
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile


@pytest.fixture
def users(db):
    location = Location.objects.create(city="Manhattan", state="NY")

    def create(email, name):
        user = User.objects.create_user(email, "Correct-Horse-42")
        Profile.objects.create(user=user, display_name=name)
        Preference.objects.create(
            user=user,
            location=location,
            budget_range=BudgetRange.B1001_1500,
            pets_preference=PetsPreference.NO_PETS,
        )
        return user

    return {
        "alex": create("alex@example.com", "Alex"),
        "maya": create("maya@example.com", "Maya"),
        "sam": create("sam@example.com", "Sam"),
    }


def test_signed_in_user_can_send_message_from_roommate_profile(client, users):
    client.force_login(users["alex"])

    response = client.post(
        f"/roommates/{users['maya'].user_id}/message/", {"body": "Hi Maya!"}
    )

    conversation = Conversation.objects.get()
    message = Message.objects.get()
    assert response.status_code == 302
    assert response.url == f"/conversations/{conversation.conversation_id}/"
    assert message.conversation == conversation
    assert message.sender == users["alex"]
    assert message.body == "Hi Maya!"


def test_message_modal_starts_with_an_editable_greeting(client, users):
    client.force_login(users["alex"])

    response = client.get(f"/roommates/{users['maya'].user_id}/")

    assert response.status_code == 200
    assert b"Hi Maya! I am looking for a place in New York too. Want to chat?" in response.content
    assert b"data-send-on-enter" in response.content
    assert b"Press Enter to send. Shift + Enter for a new line." in response.content


def test_empty_message_shows_error_and_is_not_saved(client, users):
    client.force_login(users["alex"])

    response = client.post(
        f"/roommates/{users['maya'].user_id}/message/", {"body": "   "}
    )

    assert response.status_code == 400
    assert b"Enter a message." in response.content
    assert not Message.objects.exists()
    assert not Conversation.objects.exists()


def test_missing_message_body_is_rejected(client, users):
    client.force_login(users["alex"])

    response = client.post(f"/roommates/{users['maya'].user_id}/message/", {})

    assert response.status_code == 400
    assert b"Enter a message." in response.content
    assert not Message.objects.exists()
    assert not Conversation.objects.exists()


@pytest.mark.parametrize("body", ["x" * 2001, " " + ("x" * 2000)])
@pytest.mark.parametrize("route", ["new_conversation", "reply"])
def test_oversized_message_is_rejected(client, users, body, route):
    client.force_login(users["alex"])
    if route == "new_conversation":
        url = f"/roommates/{users['maya'].user_id}/message/"
        previous_message_count = 0
        previous_conversation_count = 0
    else:
        conversation, _ = messaging_services.send_message(
            users["maya"], users["alex"], "Previous message"
        )
        url = f"/conversations/{conversation.conversation_id}/"
        previous_message_count = 1
        previous_conversation_count = 1

    response = client.post(url, {"body": body})

    assert response.status_code == 400
    assert b"Message must be 2000 characters or fewer." in response.content
    assert Message.objects.count() == previous_message_count
    assert Conversation.objects.count() == previous_conversation_count
    assert len(body) > 2000


def test_message_at_character_limit_is_accepted(client, users):
    client.force_login(users["alex"])
    body = "x" * 2000

    response = client.post(
        f"/roommates/{users['maya'].user_id}/message/", {"body": body}
    )

    assert response.status_code == 302
    assert Message.objects.get().body == body


@pytest.mark.parametrize("body", [None, 123, [], {}])
def test_send_message_rejects_non_string_bodies(users, body):
    with pytest.raises(ValidationError) as exc_info:
        messaging_services.send_message(users["alex"], users["maya"], body)

    assert exc_info.value.message_dict["body"] == ["Enter a message."]
    assert not Message.objects.exists()
    assert not Conversation.objects.exists()


def test_conversation_list_and_detail_show_persisted_messages(client, users):
    conversation, _ = messaging_services.send_message(
        users["alex"], users["maya"], "Hi Maya!"
    )
    messaging_services.send_message(users["maya"], users["alex"], "Hi Alex!")
    client.force_login(users["alex"])

    list_response = client.get("/conversations/")
    detail_response = client.get(f"/conversations/{conversation.conversation_id}/")

    assert list_response.status_code == 200
    assert b"Maya" in list_response.content
    assert detail_response.status_code == 200
    assert b"Hi Maya!" in detail_response.content
    assert b"Hi Alex!" in detail_response.content
    assert b"data-send-on-enter" in detail_response.content
    assert b"data-draft-key" in detail_response.content


def test_user_can_reply_from_an_existing_conversation(client, users):
    conversation, _ = messaging_services.send_message(
        users["maya"], users["alex"], "Hi Alex!"
    )
    client.force_login(users["alex"])

    response = client.post(
        f"/conversations/{conversation.conversation_id}/", {"body": "Nice to meet you!"}
    )

    assert response.status_code == 302
    assert Message.objects.filter(
        conversation=conversation, sender=users["alex"], body="Nice to meet you!"
    ).exists()


def test_empty_reply_shows_message_prompt_and_is_not_saved(client, users):
    conversation, _ = messaging_services.send_message(
        users["maya"], users["alex"], "Hi Alex!"
    )
    client.force_login(users["alex"])

    response = client.post(f"/conversations/{conversation.conversation_id}/", {"body": "  "})

    assert response.status_code == 400
    assert b"Message not sent" in response.content
    assert b"Enter a message." in response.content
    assert Message.objects.filter(conversation=conversation).count() == 1


def test_hide_conversation_shows_styled_confirmation_prompt(client, users):
    conversation, _ = messaging_services.send_message(
        users["alex"], users["maya"], "Hi Maya!"
    )
    client.force_login(users["alex"])

    response = client.get(f"/conversations/{conversation.conversation_id}/")

    assert response.status_code == 200
    assert (
        b"Hide this conversation for yourself? The other person will still see the "
        b"conversation. The chat will reappear when a new message is sent."
        in response.content
    )
    assert b'data-confirm-hide-yes>Yes</button>' in response.content
    assert b'data-confirm-hide-no>No</button>' in response.content


def test_no_conversations_shows_empty_state(client, users):
    client.force_login(users["alex"])

    response = client.get("/conversations/")

    assert response.status_code == 200
    assert b"You have no chats yet" in response.content


def test_conversations_persist_for_a_new_logged_in_session(users):
    conversation, _ = messaging_services.send_message(
        users["alex"], users["maya"], "Message that persists"
    )
    restarted_client = Client()
    restarted_client.force_login(users["alex"])

    response = restarted_client.get(f"/conversations/{conversation.conversation_id}/")

    assert response.status_code == 200
    assert b"Message that persists" in response.content


def test_non_participant_cannot_open_someone_elses_conversation(client, users):
    conversation, _ = messaging_services.send_message(
        users["alex"], users["maya"], "Private message"
    )
    client.force_login(users["sam"])

    response = client.get(f"/conversations/{conversation.conversation_id}/")

    assert response.status_code == 404
    assert b"Conversation unavailable" in response.content


def test_participant_can_poll_only_new_messages(client, users):
    conversation, first_message = messaging_services.send_message(
        users["alex"], users["maya"], "Hi Maya!"
    )
    messaging_services.send_message(users["maya"], users["alex"], "Hi Alex!")
    client.force_login(users["alex"])

    response = client.get(
        f"/api/conversations/{conversation.conversation_id}/messages?after={first_message.message_id}"
    )

    assert response.status_code == 200
    messages = response.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["message_id"] == Message.objects.get(body="Hi Alex!").message_id
    assert messages[0]["body"] == "Hi Alex!"
    assert messages[0]["sender_id"] == str(users["maya"].user_id)
    assert messages[0]["sent_at_display"]


def test_participant_can_poll_their_conversation_sidebar(client, users):
    conversation, _ = messaging_services.send_message(
        users["maya"], users["alex"], "Hi Alex!"
    )
    client.force_login(users["alex"])

    response = client.get("/api/conversations/sidebar")

    assert response.status_code == 200
    conversations = response.json()["conversations"]
    assert conversations == [
        {
            "conversation_id": str(conversation.conversation_id),
            "is_pinned": False,
            "other_name": "Maya",
            "last_message": "Hi Alex!",
            "url": f"/conversations/{conversation.conversation_id}/",
            "profile_photo_url": "",
        }
    ]


def test_non_participant_cannot_poll_someone_elses_conversation(client, users):
    conversation, _ = messaging_services.send_message(
        users["alex"], users["maya"], "Private message"
    )
    client.force_login(users["sam"])

    response = client.get(f"/api/conversations/{conversation.conversation_id}/messages?after=0")

    assert response.status_code == 404
    assert response.json()["error"] == "Conversation unavailable."


def test_admin_can_use_chats_but_cannot_access_someone_elses_conversation(client, users):
    conversation, _ = messaging_services.send_message(
        users["alex"], users["maya"], "Private message"
    )
    admin = User.objects.create_admin("admin@example.com", "Correct-Horse-42")
    client.force_login(admin)

    chats_response = client.get("/conversations/")
    assert chats_response.status_code == 200
    assert b"Open a support request to contact a user." in chats_response.content
    assert client.get(f"/conversations/{conversation.conversation_id}/").status_code == 404
    poll_response = client.get(
        f"/api/conversations/{conversation.conversation_id}/messages?after=0"
    )
    assert poll_response.status_code == 404


def test_admin_can_start_a_chat_from_a_support_request(client, users):
    support_request = SupportRequest.objects.create(
        subject="Login issue", body="I need help logging in.", user=users["maya"].email
    )
    admin = User.objects.create_admin("admin@example.com", "Correct-Horse-42")
    client.force_login(admin)

    admin_page = client.get("/app-admin/")
    compose_url = f"/app-admin/support-requests/{support_request.id}/message/"
    assert admin_page.status_code == 200
    assert compose_url.encode() in admin_page.content

    compose_response = client.get(compose_url)
    assert compose_response.status_code == 200
    assert b"Message maya@example.com" in compose_response.content
    assert b"data-send-on-enter" in compose_response.content
    assert b"Press Enter to send. Shift + Enter for a new line." in compose_response.content

    send_response = client.post(compose_url, {"body": "I can help with your login issue."})
    conversation = Conversation.objects.get()
    assert send_response.status_code == 302
    assert send_response.url == f"/conversations/{conversation.conversation_id}/"
    assert Message.objects.filter(
        conversation=conversation,
        sender=admin,
        body="I can help with your login issue.",
    ).exists()


def test_admin_can_message_a_user_from_their_roommate_profile(client, users):
    admin = User.objects.create_admin("admin@example.com", "Correct-Horse-42")
    client.force_login(admin)
    profile_url = f"/roommates/{users['maya'].user_id}/"

    profile = client.get(profile_url)
    assert profile.status_code == 200
    assert b"Send a message" in profile.content
    assert b"I am looking for a place in New York too" not in profile.content

    response = client.post(f"{profile_url}message/", {"body": "Hello from support"})
    assert response.status_code == 302
    conversation = Conversation.objects.get()
    assert response.url == f"/conversations/{conversation.conversation_id}/"
    assert Message.objects.filter(conversation=conversation, sender=admin, body="Hello from support").exists()


def test_delete_message_is_private_and_only_sender_can_unsend(client, users):
    conversation, message = messaging_services.send_message(users["alex"], users["maya"], "Hello Maya")
    url = f"/api/conversations/{conversation.conversation_id}/messages/{message.message_id}/remove"
    client.force_login(users["maya"])
    assert client.post(url, {"action": "unsend"}).status_code == 403
    assert client.post(url, {"action": "delete"}).status_code == 200
    assert not messaging_services.visible_messages(conversation, users["maya"]).exists()
    assert messaging_services.visible_messages(conversation, users["alex"]).exists()
    client.force_login(users["sam"])
    assert client.post(url, {"action": "unsend"}).status_code == 404
    client.force_login(users["alex"])
    assert client.post(url, {"action": "unsend"}).status_code == 200
    assert not Message.objects.filter(pk=message.pk).exists()


def test_delete_chat_is_private_and_new_message_brings_it_back(client, users):
    conversation, old_message = messaging_services.send_message(users["alex"], users["maya"], "Old message")
    client.force_login(users["alex"])
    url = f"/api/conversations/{conversation.conversation_id}/delete"
    assert client.post(url).status_code == 200
    assert conversation not in messaging_services.visible_conversations(users["alex"])
    assert conversation in messaging_services.visible_conversations(users["maya"])
    messaging_services.send_message(users["maya"], users["alex"], "New message")
    assert conversation in messaging_services.visible_conversations(users["alex"])
    assert not messaging_services.visible_messages(conversation, users["alex"]).filter(pk=old_message.pk).exists()


def test_hidden_conversations_page_shows_empty_state_and_link(client, users):
    client.force_login(users["alex"])

    response = client.get("/conversations/hidden/")

    assert response.status_code == 200
    assert b'<p class="chat-feature-hint">You have no hidden chats.</p>' in response.content
    assert b'href="/conversations/"' in response.content


def test_hidden_conversation_can_be_confirmed_and_unhidden(client, users):
    conversation, _ = messaging_services.send_message(
        users["alex"], users["maya"], "Previous message"
    )
    client.force_login(users["alex"])
    client.post(f"/api/conversations/{conversation.pk}/delete")

    hidden_page = client.get("/conversations/hidden/")

    assert hidden_page.status_code == 200
    assert b"Hidden Chats" in client.get(
        f"/conversations/{conversation.pk}/"
    ).content
    assert b"Maya" in hidden_page.content
    assert b"Previous message" in hidden_page.content
    assert b"Are you sure you want to unhide this conversation?" in hidden_page.content
    assert b">Yes</button>" in hidden_page.content
    assert b">No</button>" in hidden_page.content

    unhide_response = client.post(f"/conversations/{conversation.pk}/unhide/")

    assert unhide_response.status_code == 302
    assert unhide_response.url == "/conversations/hidden/"
    assert conversation in messaging_services.visible_conversations(users["alex"])
    assert b"You have no hidden chats" in client.get("/conversations/hidden/").content
    assert b"Previous message" in client.get(f"/conversations/{conversation.pk}/").content


def test_new_message_removes_conversation_from_hidden_list(client, users):
    conversation, _ = messaging_services.send_message(
        users["alex"], users["maya"], "Previous message"
    )
    client.force_login(users["alex"])
    client.post(f"/api/conversations/{conversation.pk}/delete")
    messaging_services.send_message(users["maya"], users["alex"], "New message")

    response = client.get("/conversations/hidden/")

    assert b"You have no hidden chats" in response.content
    assert conversation in messaging_services.visible_conversations(users["alex"])


def test_non_participant_cannot_unhide_conversation(client, users):
    conversation, _ = messaging_services.send_message(
        users["alex"], users["maya"], "Private message"
    )
    client.force_login(users["alex"])
    client.post(f"/api/conversations/{conversation.pk}/delete")
    client.force_login(users["sam"])

    response = client.post(f"/conversations/{conversation.pk}/unhide/")

    assert response.status_code == 404


def test_pinning_is_private_and_sorts_conversations_first(client, users):
    older, _ = messaging_services.send_message(users["alex"], users["maya"], "Older")
    newer, _ = messaging_services.send_message(users["alex"], users["sam"], "Newer")
    url = f"/api/conversations/{older.conversation_id}/pin"
    client.force_login(users["sam"])
    assert client.post(url, {"action": "pin"}).status_code == 404
    client.force_login(users["alex"])
    assert client.post(url, {"action": "pin"}).json()["is_pinned"] is True
    chats = client.get("/api/conversations/sidebar").json()["conversations"]
    assert [item["conversation_id"] for item in chats] == [str(older.pk), str(newer.pk)]
    assert chats[0]["is_pinned"] is True
    client.force_login(users["maya"])
    assert client.get("/api/conversations/sidebar").json()["conversations"][0]["is_pinned"] is False
    client.force_login(users["alex"])
    assert client.post(url, {"action": "unpin"}).json()["is_pinned"] is False
    assert client.get("/api/conversations/sidebar").json()["conversations"][0]["conversation_id"] == str(newer.pk)
