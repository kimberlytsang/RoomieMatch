"""Tests for US-10 idle session expiration."""

import json
from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client
from django.utils import timezone

import pytest

from accounts.models import User

LOGIN = "/api/auth/login"
PASSWORD = "Correct-Horse-42"


@pytest.fixture
def user(db):
    return User.objects.create_user("roomie@example.com", PASSWORD)


def login(client):
    return client.post(
        LOGIN,
        data=json.dumps({"email": "roomie@example.com", "password": PASSWORD}),
        content_type="application/json",
    )


def expire_session(session_key):
    Session.objects.filter(session_key=session_key).update(
        expire_date=timezone.now() - timedelta(seconds=1)
    )


def test_session_uses_a_30_minute_idle_timeout_and_renews_on_activity(user):
    assert settings.SESSION_COOKIE_AGE == 30 * 60
    assert settings.SESSION_SAVE_EVERY_REQUEST is True

    client = Client()
    assert login(client).status_code == 200
    session_key = client.cookies["sessionid"].value
    original_expiry = Session.objects.get(session_key=session_key).expire_date

    response = client.get("/account/settings/")

    assert response.status_code == 200
    renewed_expiry = Session.objects.get(session_key=session_key).expire_date
    assert renewed_expiry > original_expiry


def test_expired_session_cookie_is_rejected_by_protected_api(user):
    client = Client()
    assert login(client).status_code == 200
    old_session_key = client.cookies["sessionid"].value
    expire_session(old_session_key)

    replay = Client()
    replay.cookies["sessionid"] = old_session_key
    response = replay.post(
        "/api/auth/password/change",
        data="{}",
        content_type="application/json",
    )

    assert response.status_code == 401
    assert response.json() == {"error": "Authentication required."}


def test_user_can_log_in_again_after_session_timeout(user):
    client = Client()
    assert login(client).status_code == 200
    old_session_key = client.cookies["sessionid"].value
    expire_session(old_session_key)

    expired_response = client.post(
        "/api/auth/password/change",
        data="{}",
        content_type="application/json",
    )
    assert expired_response.status_code == 401

    relogin_response = login(client)

    assert relogin_response.status_code == 200
    assert client.cookies["sessionid"].value != old_session_key
    assert client.get("/account/settings/").status_code == 200
