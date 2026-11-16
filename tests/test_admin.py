import pytest
import json
from django.test import Client

from accounts.models import User,SupportRequest
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile
from accounts.models import SupportRequestStatus


STATUS_URL = "/api/auth/support/{}/status"


@pytest.fixture
def client():
    return Client()

# def test_fully_formed_support_form(client, db):
#     row_count = SupportRequest.objects.count()
#     user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
#     client.force_login(user)
#     response = client.post(
#         "/api/auth/support",
#         data={
#             "subject":"test subject",
#             "body":"test body"
#         },
#         content_type='application/json'
#     )

#     assert response.status_code == 201
#     assert b"Support request successfully submitted." in response.content
#     assert SupportRequest.objects.count() == row_count + 1

def test_admin_access(client, db):
    row_count = SupportRequest.objects.count()
    for i in range(3):
        SupportRequest.objects.create(subject="Test", body="Help", user="roomie@example.com")
    admin = User.objects.create_admin("testAdmin@example.com", "Correct-Horse-42")
    client.force_login(admin)
    response = client.get('/app-admin/')

    assert len(response.context["support_requests"]) == 3
    assert response.status_code == 200
    assert b'<select id="status-' in response.content
    assert b"Open" in response.content
    assert b'<button id="save-support-statuses" type="button" disabled>Save Changes</button>' in response.content
    assert b'<button type="submit">Save</button>' not in response.content

def test_admin_access_no_auth(client):
    response = client.get('/app-admin/')

    assert response.status_code == 302
    assert response.headers['Location'].startswith('/login/')

def test_admin_access_as_seeker(client, db):
    user = User.objects.create_user("roomie@example.com", "Correct-Horse-42")
    client.force_login(user)
    response = client.get('/app-admin/')

    assert response.status_code == 302
    assert response.headers['Location'] == '/'


def test_admin_can_update_support_request_status_and_it_persists(client, db):
    request = SupportRequest.objects.create(
        subject="Test", body="Help", user="roomie@example.com"
    )
    admin = User.objects.create_admin("admin@example.com", "Correct-Horse-42")
    client.force_login(admin)

    response = client.post(
        STATUS_URL.format(request.pk),
        data=json.dumps({"status": SupportRequestStatus.IN_PROGRESS}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == SupportRequestStatus.IN_PROGRESS
    request.refresh_from_db()
    assert request.status == SupportRequestStatus.IN_PROGRESS
    page_response = client.get("/app-admin/")
    assert (
        f'<option value="{SupportRequestStatus.IN_PROGRESS}" selected>'.encode()
        in page_response.content
    )


def test_seeker_cannot_update_support_request_status(client, db):
    request = SupportRequest.objects.create(
        subject="Test", body="Help", user="roomie@example.com"
    )
    seeker = User.objects.create_user("seeker@example.com", "Correct-Horse-42")
    client.force_login(seeker)

    response = client.post(
        STATUS_URL.format(request.pk),
        data=json.dumps({"status": SupportRequestStatus.RESOLVED}),
        content_type="application/json",
    )

    assert response.status_code == 403
    request.refresh_from_db()
    assert request.status == SupportRequestStatus.OPEN


def test_unauthenticated_user_cannot_update_support_request_status(client, db):
    request = SupportRequest.objects.create(
        subject="Test", body="Help", user="roomie@example.com"
    )

    response = client.post(
        STATUS_URL.format(request.pk),
        data=json.dumps({"status": SupportRequestStatus.RESOLVED}),
        content_type="application/json",
    )

    assert response.status_code == 401
    request.refresh_from_db()
    assert request.status == SupportRequestStatus.OPEN


def test_get_cannot_update_support_request_status(client, db):
    request = SupportRequest.objects.create(
        subject="Test", body="Help", user="roomie@example.com"
    )
    admin = User.objects.create_admin("admin@example.com", "Correct-Horse-42")
    client.force_login(admin)

    response = client.get(
        STATUS_URL.format(request.pk), {"status": SupportRequestStatus.RESOLVED}
    )

    assert response.status_code == 405
    request.refresh_from_db()
    assert request.status == SupportRequestStatus.OPEN


@pytest.mark.parametrize("status", ["NEW", "CLOSED", "", None])
def test_invalid_status_is_rejected(client, db, status):
    request = SupportRequest.objects.create(
        subject="Test", body="Help", user="roomie@example.com"
    )
    admin = User.objects.create_admin("admin@example.com", "Correct-Horse-42")
    client.force_login(admin)

    response = client.post(
        STATUS_URL.format(request.pk),
        data=json.dumps({"status": status}),
        content_type="application/json",
    )

    assert response.status_code == 400
    request.refresh_from_db()
    assert request.status == SupportRequestStatus.OPEN


def test_missing_support_request_returns_not_found(client, db):
    admin = User.objects.create_admin("admin@example.com", "Correct-Horse-42")
    client.force_login(admin)

    response = client.post(
        STATUS_URL.format(99999),
        data=json.dumps({"status": SupportRequestStatus.RESOLVED}),
        content_type="application/json",
    )

    assert response.status_code == 404


def test_status_update_requires_csrf_token(db):
    request = SupportRequest.objects.create(
        subject="Test", body="Help", user="roomie@example.com"
    )
    admin = User.objects.create_admin("admin@example.com", "Correct-Horse-42")
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin)

    response = client.post(
        STATUS_URL.format(request.pk),
        data=json.dumps({"status": SupportRequestStatus.RESOLVED}),
        content_type="application/json",
    )

    assert response.status_code == 403
    request.refresh_from_db()
    assert request.status == SupportRequestStatus.OPEN