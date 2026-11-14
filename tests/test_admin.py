import pytest
from django.test import Client

from accounts.models import User,SupportRequest
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile


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
        SupportRequest.objects.create(subject="Test", body="Help")
    admin = User.objects.create_admin("testAdmin@example.com", "Correct-Horse-42")
    client.force_login(admin)
    response = client.get('/app-admin/')

    assert len(response.context["support_requests"]) == 3
    assert response.status_code == 200

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