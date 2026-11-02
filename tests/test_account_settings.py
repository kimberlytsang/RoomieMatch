"""Tests for the signed-in account menu and settings page."""

import json

import pytest
from django.test import Client

from accounts.models import User
from messaging.models import Conversation, Message
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile
from support.models import SupportRequest


DELETE_ACCOUNT = "/api/users/me"
GOOD_PASSWORD = "Correct-Horse-42"


def create_roommate(email, name, location):
    user = User.objects.create_user(email, GOOD_PASSWORD)
    Profile.objects.create(user=user, display_name=name)
    Preference.objects.create(
        user=user,
        location=location,
        budget_range=BudgetRange.B2501_3000,
        pets_preference=PetsPreference.NO_PETS,
    )
    return user


def test_account_settings_requires_authentication(client):
    response = client.get("/account/settings/")

    assert response.status_code == 302
    assert response.url == "/login/?next=/account/settings/"


def test_signed_in_user_can_open_account_settings(client, db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)

    response = client.get("/account/settings/")

    assert response.status_code == 200
    assert b"Account settings" in response.content
    assert b"Logged in as roomie@example.com" in response.content
    assert b"You will be logged out after 30 minutes of inactivity." in response.content
    assert b'href="/account/settings/"' in response.content
    assert b'id="change-password-form"' in response.content
    assert b"Current password" in response.content
    assert b"New password" in response.content
    assert b"Confirm new password" in response.content
    assert b'placeholder="Type your current password here"' in response.content
    assert b'placeholder="Create a new password"' in response.content
    assert b'placeholder="Enter your new password again"' in response.content
    assert b'id="open-delete-account-modal"' in response.content
    assert b'id="delete-account-modal"' in response.content
    assert b"Delete account" in response.content
    assert b"Keep account" in response.content
    assert b"permanently deleted" in response.content


def test_canceling_account_deletion_keeps_account_and_related_data(client, db):
    location = Location.objects.create(city="Manhattan", state="NY")
    user = create_roommate("roomie@example.com", "Roomie", location)
    client.force_login(user)

    response = client.get("/account/settings/")

    assert response.status_code == 200
    assert b'id="keep-account"' in response.content
    assert User.objects.filter(pk=user.pk).exists()
    assert Profile.objects.filter(user=user).exists()
    assert Preference.objects.filter(user=user).exists()


@pytest.mark.parametrize("body", [{}, {"confirmation": False}, {"confirmation": "yes"}])
def test_delete_account_rejects_missing_or_invalid_confirmation(client, db, body):
    location = Location.objects.create(city="Manhattan", state="NY")
    user = create_roommate("roomie@example.com", "Roomie", location)
    client.force_login(user)

    response = client.delete(
        DELETE_ACCOUNT,
        data=json.dumps(body),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json() == {"error": "Account deletion confirmation is required."}
    assert User.objects.filter(pk=user.pk).exists()
    assert Profile.objects.filter(user=user).exists()
    assert Preference.objects.filter(user=user).exists()
    assert client.session["_auth_user_id"] == str(user.pk)


def test_delete_account_requires_authentication(client, db):
    response = client.delete(
        DELETE_ACCOUNT,
        data=json.dumps({"confirmation": True}),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_get_cannot_delete_account(client, db):
    user = User.objects.create_user("roomie@example.com", GOOD_PASSWORD)
    client.force_login(user)

    response = client.get(DELETE_ACCOUNT)

    assert response.status_code == 405
    assert User.objects.filter(pk=user.pk).exists()


def test_delete_account_requires_csrf_token(db):
    user = User.objects.create_user("roomie@example.com", GOOD_PASSWORD)
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)

    response = client.delete(
        DELETE_ACCOUNT,
        data=json.dumps({"confirmation": True}),
        content_type="application/json",
    )

    assert response.status_code == 403
    assert User.objects.filter(pk=user.pk).exists()


def test_delete_account_removes_related_records_and_ends_session(client, db):
    location = Location.objects.create(city="Manhattan", state="NY")
    user = create_roommate("roomie@example.com", "Roomie", location)
    other_user = create_roommate("other@example.com", "Other", location)
    user_a, user_b = sorted((user, other_user), key=lambda account: account.user_id)
    conversation = Conversation.objects.create(user_a=user_a, user_b=user_b)
    Message.objects.create(conversation=conversation, sender=user, body="Hello")
    SupportRequest.objects.create(
        submitter=user, category="USER_FEEDBACK", description="Please remove my account."
    )
    client.force_login(user)

    response = client.delete(
        DELETE_ACCOUNT,
        data=json.dumps({"confirmation": True}),
        content_type="application/json",
    )

    assert response.status_code == 204
    assert response.content == b""
    assert not User.objects.filter(pk=user.pk).exists()
    assert not Profile.objects.filter(user_id=user.pk).exists()
    assert not Preference.objects.filter(user_id=user.pk).exists()
    assert Conversation.objects.count() == 0
    assert Message.objects.count() == 0
    assert SupportRequest.objects.count() == 0
    assert User.objects.filter(pk=other_user.pk).exists()
    assert "_auth_user_id" not in client.session

    login_response = client.post(
        "/api/auth/login",
        data=json.dumps({"email": "roomie@example.com", "password": GOOD_PASSWORD}),
        content_type="application/json",
    )
    assert login_response.status_code == 401


def test_deleted_roommate_is_not_searchable_or_accessible(client, db):
    location = Location.objects.create(city="Manhattan", state="NY")
    viewer = create_roommate("viewer@example.com", "Viewer", location)
    deleted_user = create_roommate("deleted@example.com", "Deleted Roommate", location)
    client.force_login(deleted_user)

    delete_response = client.delete(
        DELETE_ACCOUNT,
        data=json.dumps({"confirmation": True}),
        content_type="application/json",
    )
    assert delete_response.status_code == 204

    viewer_client = Client()
    viewer_client.force_login(viewer)
    list_response = viewer_client.get("/roommates/")
    detail_response = viewer_client.get(f"/roommates/{deleted_user.pk}/")

    assert list_response.status_code == 200
    assert b"Deleted Roommate" not in list_response.content
    assert detail_response.status_code == 404


def test_signed_in_home_page_has_account_menu(client, db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)

    response = client.get("/")

    assert response.status_code == 200
    assert b'id="account-menu-toggle"' in response.content
    assert b"Account settings" in response.content
    assert b'data-logout' in response.content
    assert b"account-menu-avatar" not in response.content


def test_change_password_updates_hash_and_preserves_session(client, db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)

    response = client.post(
        "/api/auth/password/change",
        data=json.dumps({
            "current_password": "Correct-Horse-42",
            "new_password": "New-Secure-Password-43!",
            "confirm_password": "New-Secure-Password-43!",
        }),
        content_type="application/json",
    )

    user.refresh_from_db()
    assert response.status_code == 200
    assert response.json() == {"message": "Password updated successfully."}
    assert user.check_password("New-Secure-Password-43!")
    assert client.session["_auth_user_id"] == str(user.user_id)
    assert client.post("/api/auth/logout", data="{}", content_type="application/json").status_code == 204


def test_change_password_rejects_incorrect_current_password(client, db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)

    response = client.post(
        "/api/auth/password/change",
        data=json.dumps({
            "current_password": "Wrong-Password-2!",
            "new_password": "New-Secure-Password-43!",
            "confirm_password": "New-Secure-Password-43!",
        }),
        content_type="application/json",
    )

    user.refresh_from_db()
    assert response.status_code == 400
    assert response.json()["error"] == "Current password is incorrect."
    assert user.check_password("Correct-Horse-42")


def test_change_password_rejects_current_password_as_new_password(client, db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)

    response = client.post(
        "/api/auth/password/change",
        data=json.dumps({
            "current_password": "Correct-Horse-42",
            "new_password": "Correct-Horse-42",
            "confirm_password": "Correct-Horse-42",
        }),
        content_type="application/json",
    )

    user.refresh_from_db()
    assert response.status_code == 400
    assert response.json()["error"] == (
        "This is your current password. Please create a different one."
    )
    assert user.check_password("Correct-Horse-42")


def test_change_password_rejects_mismatched_confirmation(client, db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)

    response = client.post(
        "/api/auth/password/change",
        data=json.dumps({
            "current_password": "Correct-Horse-42",
            "new_password": "New-Secure-Password-43!",
            "confirm_password": "Different-Secure-Password-44!",
        }),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["error"] == "New password and confirmation password do not match."


def test_change_password_rejects_weak_new_password(client, db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)

    response = client.post(
        "/api/auth/password/change",
        data=json.dumps({
            "current_password": "Correct-Horse-42",
            "new_password": "weak",
            "confirm_password": "weak",
        }),
        content_type="application/json",
    )

    assert response.status_code == 422
    assert "error" in response.json()


def test_change_password_requires_a_number_in_new_password(client, db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)

    response = client.post(
        "/api/auth/password/change",
        data=json.dumps({
            "current_password": "Correct-Horse-42",
            "new_password": "New-Secure-Password!",
            "confirm_password": "New-Secure-Password!",
        }),
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json()["error"] == "Password must include at least one number."


def test_change_password_requires_authentication(client, db):
    response = client.post(
        "/api/auth/password/change",
        data=json.dumps({
            "current_password": "Correct-Horse-42",
            "new_password": "New-Secure-Password-43!",
            "confirm_password": "New-Secure-Password-43!",
        }),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_change_password_requires_csrf_token(db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)

    response = client.post(
        "/api/auth/password/change",
        data=json.dumps({
            "current_password": "Correct-Horse-42",
            "new_password": "New-Secure-Password-43!",
            "confirm_password": "New-Secure-Password-43!",
        }),
        content_type="application/json",
    )

    assert response.status_code == 403
