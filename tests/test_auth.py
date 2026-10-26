"""Tests for US-01 (register), US-02 (log in), US-03 (log out).
Each story has a happy-path test plus error and permission cases from the
interface table (Sprint 2, Section 4)."""
import pytest
from django.test import Client

from accounts.models import User

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
LOGOUT = "/api/auth/logout"
GOOD_PASSWORD = "Correct-Horse-42"


def post(client, url, body):
    return client.post(url, data=body, content_type="application/json")


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return User.objects.create_user("roomie@example.com", GOOD_PASSWORD)


# ---------------------------------------------------------------- US-01 register

def test_register_creates_account_and_session(client, db):
    res = post(client, REGISTER, {"email": "new@example.com", "password": GOOD_PASSWORD})
    assert res.status_code == 201
    created = User.objects.get(email="new@example.com")
    assert res.json() == {"user_id": str(created.user_id)}
    assert "sessionid" in res.cookies  # the user is signed in
    assert created.role == "SEEKER"


def test_register_stores_a_hash_not_the_password(client, db):
    post(client, REGISTER, {"email": "new@example.com", "password": GOOD_PASSWORD})
    stored = User.objects.get(email="new@example.com").password
    assert stored != GOOD_PASSWORD and GOOD_PASSWORD not in stored


@pytest.mark.parametrize("body", [
    {},
    {"email": "new@example.com"},
    {"password": GOOD_PASSWORD},
    {"email": "", "password": GOOD_PASSWORD},
    {"email": "new@example.com", "password": ""},
    {"email": 123, "password": GOOD_PASSWORD},
    {"email": "not-an-email", "password": GOOD_PASSWORD},
])
def test_register_rejects_missing_or_invalid_fields_with_400(client, db, body):
    res = post(client, REGISTER, body)
    assert res.status_code == 400
    assert "error" in res.json()
    assert User.objects.count() == 0


@pytest.mark.parametrize(("body", "message"), [
    ({}, "Please fill out the missing fields: Email and Password."),
    ({"email": "new@example.com"}, "Please fill out the missing fields: Password."),
    ({"password": GOOD_PASSWORD}, "Please fill out the missing fields: Email."),
    ({"email": "", "password": GOOD_PASSWORD}, "Please fill out the missing fields: Email."),
    ({"email": "new@example.com", "password": ""}, "Please fill out the missing fields: Password."),
])
def test_register_lists_missing_fields(client, db, body, message):
    res = post(client, REGISTER, body)
    assert res.status_code == 400
    assert res.json()["error"] == message
    assert User.objects.count() == 0


def test_register_rejects_non_json_body_with_400(client, db):
    res = client.post(REGISTER, data="email=a@b.com", content_type="text/plain")
    assert res.status_code == 400


def test_register_duplicate_email_is_409_ignoring_case(client, user):
    res = post(client, REGISTER, {"email": "ROOMIE@Example.com", "password": GOOD_PASSWORD})
    assert res.status_code == 409
    assert User.objects.count() == 1


@pytest.mark.parametrize("password", ["short1!", "password", "12345678901", "a" * 129])
def test_register_weak_password_is_422(client, db, password):
    res = post(client, REGISTER, {"email": "new@example.com", "password": password})
    assert res.status_code == 422
    assert User.objects.count() == 0


@pytest.mark.parametrize(("password", "message"), [
    ("Ab1!", "This password is too short. It must contain at least 8 characters."),
    ("lowercase123!", "Password must include at least one uppercase letter."),
    ("Uppercase123", "Password must include at least one symbol."),
    ("A!" + "a" * 127, "Password must be at most 128 characters."),
])
def test_register_returns_specific_password_requirement(client, db, password, message):
    res = post(client, REGISTER, {"email": "new@example.com", "password": password})
    assert res.status_code == 422
    assert res.json()["error"] == message
    assert User.objects.count() == 0


def test_register_requires_csrf_token(db):
    strict = Client(enforce_csrf_checks=True)
    res = post(strict, REGISTER, {"email": "new@example.com", "password": GOOD_PASSWORD})
    assert res.status_code == 403
    assert User.objects.count() == 0


def test_register_rejects_get(client, db):
    assert client.get(REGISTER).status_code == 405


# ------------------------------------------------------------------ US-02 log in

def test_login_with_valid_credentials_starts_session(client, user):
    res = post(client, LOGIN, {"email": "roomie@example.com", "password": GOOD_PASSWORD})
    assert res.status_code == 200
    assert res.json() == {"user_id": str(user.user_id)}
    assert "sessionid" in res.cookies
    assert client.session["_auth_user_id"] == str(user.user_id)


def test_login_email_is_case_insensitive(client, user):
    res = post(client, LOGIN, {"email": "Roomie@EXAMPLE.com", "password": GOOD_PASSWORD})
    assert res.status_code == 200


@pytest.mark.parametrize("body", [
    {},
    {"email": "roomie@example.com"},
    {"password": GOOD_PASSWORD},
    {"email": "", "password": ""},
])
def test_login_missing_fields_is_400(client, user, body):
    res = post(client, LOGIN, body)
    assert res.status_code == 400
    assert res.json()["error"] == "Email or password not provided."


def test_login_wrong_password_is_401_without_session(client, user):
    res = post(client, LOGIN, {"email": "roomie@example.com", "password": "Wrong-Password-1"})
    assert res.status_code == 401
    assert "sessionid" not in res.cookies


def test_login_unknown_email_looks_the_same_as_wrong_password(client, user):
    wrong_pw = post(client, LOGIN, {"email": "roomie@example.com", "password": "Wrong-Password-1"})
    no_user = post(client, LOGIN, {"email": "nobody@example.com", "password": GOOD_PASSWORD})
    assert no_user.status_code == wrong_pw.status_code == 401
    assert no_user.json() == wrong_pw.json()


def test_login_requires_csrf_token(user):
    strict = Client(enforce_csrf_checks=True)
    res = post(strict, LOGIN, {"email": "roomie@example.com", "password": GOOD_PASSWORD})
    assert res.status_code == 403


# ----------------------------------------------------------------- US-03 log out

def test_logout_returns_204_with_no_body_and_ends_session(client, user):
    post(client, LOGIN, {"email": "roomie@example.com", "password": GOOD_PASSWORD})
    res = post(client, LOGOUT, {})
    assert res.status_code == 204
    assert res.content == b""
    assert "_auth_user_id" not in client.session
    # The old session no longer works: logging out again is unauthorized.
    assert post(client, LOGOUT, {}).status_code == 401


def test_logout_session_is_removed_on_the_server(client, user):
    post(client, LOGIN, {"email": "roomie@example.com", "password": GOOD_PASSWORD})
    old_key = client.cookies["sessionid"].value
    post(client, LOGOUT, {})
    replay = Client()
    replay.cookies["sessionid"] = old_key  # someone replays the old cookie
    assert post(replay, LOGOUT, {}).status_code == 401


def test_logout_without_a_session_is_401(client, db):
    assert post(client, LOGOUT, {}).status_code == 401


def test_logout_requires_csrf_token(user):
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(user)
    assert post(strict, LOGOUT, {}).status_code == 403


# ----------------------------------------------------------------------- pages

def test_pages_render(client, user):
    assert client.get("/").status_code == 200
    assert client.get("/login/").status_code == 200
    assert client.get("/register/").status_code == 200


def test_signed_in_user_sees_email_and_is_redirected_from_login_page(client, user):
    client.force_login(user)
    assert b"roomie@example.com" in client.get("/").content
    assert client.get("/login/").status_code == 302
