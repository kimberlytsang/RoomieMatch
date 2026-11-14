import pytest
from django.test import Client

from accounts.models import User,SupportRequest
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile


@pytest.fixture
def client():
    return Client()


def test_fully_formed_support_form(client, db):
    row_count = SupportRequest.objects.count()
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)
    response = client.post(
        "/api/auth/support",
        data={
            "subject":"test subject",
            "body":"test body"
        },
        content_type='application/json'
    )

    assert response.status_code == 201
    assert b"Support request successfully submitted." in response.content
    assert SupportRequest.objects.count() == row_count + 1


def test_malformed_support_form(client, db):
    row_count = SupportRequest.objects.count()
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)
    response = client.post(
        "/api/auth/support",
        data={
            "subject":None,
            "body":"test body"
        },
        content_type='application/json'
    )

    assert response.status_code == 400
    assert b"Subject and Body are required." in response.content
    assert SupportRequest.objects.count() == row_count

def test_empty_request(client, db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)
    response = client.post(
        "/api/auth/support",
        data = {},
        content_type='application/json'
    )

    assert response.status_code == 500

def test_unauthenticated_support_form(client):
    response = client.post(
        "/api/auth/support",
        data={
            "subject":None,
            "body":"test body"
        },
        content_type='application/json'
    )

    assert response.status_code == 401