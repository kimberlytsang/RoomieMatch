"""Data-design checks (Sprint 2, Section 3): the database itself enforces the key rules.
These are schema tests, not user-story tests."""
import pytest
from django.db import IntegrityError, transaction

from accounts.models import User
from messaging.models import Conversation, Message


@pytest.fixture
def two_users(db):
    a = User.objects.create_user("a@example.com", "pw-A-12345")
    b = User.objects.create_user("b@example.com", "pw-B-12345")
    first, second = sorted([a, b], key=lambda u: u.user_id)
    return first, second


def test_email_is_unique_ignoring_case(db):
    User.objects.create_user("Person@Example.com", "pw-12345678")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user("person@example.com", "pw-12345678")


def test_password_is_stored_hashed(db):
    user = User.objects.create_user("hash@example.com", "plain-text-pw")
    assert user.password != "plain-text-pw"
    assert user.check_password("plain-text-pw")


def test_a_pair_of_users_has_one_conversation(two_users):
    first, second = two_users
    Conversation.objects.create(user_a=first, user_b=second)
    with pytest.raises(IntegrityError), transaction.atomic():
        Conversation.objects.create(user_a=first, user_b=second)


def test_conversation_needs_two_different_users(two_users):
    first, _ = two_users
    with pytest.raises(IntegrityError), transaction.atomic():
        Conversation.objects.create(user_a=first, user_b=first)


def test_blank_message_is_rejected(two_users):
    first, second = two_users
    convo = Conversation.objects.create(user_a=first, user_b=second)
    with pytest.raises(IntegrityError), transaction.atomic():
        Message.objects.create(conversation=convo, sender=first, body="   ")


def test_deleting_a_user_deletes_their_conversations_and_messages(two_users):
    first, second = two_users
    convo = Conversation.objects.create(user_a=first, user_b=second)
    Message.objects.create(conversation=convo, sender=first, body="hello")
    first.delete()
    assert Conversation.objects.count() == 0
    assert Message.objects.count() == 0
