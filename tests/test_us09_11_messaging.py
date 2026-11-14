"""US-09 and US-11 tests for sending and reading persisted conversations."""

import pytest
from django.test import Client

from accounts.models import User
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


def test_empty_message_shows_error_and_is_not_saved(client, users):
    client.force_login(users["alex"])

    response = client.post(
        f"/roommates/{users['maya'].user_id}/message/", {"body": "   "}
    )

    assert response.status_code == 400
    assert b"Enter a message." in response.content
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


def test_no_conversations_shows_empty_state(client, users):
    client.force_login(users["alex"])

    response = client.get("/conversations/")

    assert response.status_code == 200
    assert b"No conversations yet" in response.content


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
