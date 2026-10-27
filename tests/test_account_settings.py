"""Tests for the signed-in account menu and settings page."""

import json

from django.test import Client

from accounts.models import User


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
