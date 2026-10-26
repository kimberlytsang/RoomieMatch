"""Navigation tests for the signed-in home page."""

from django.test import Client

from accounts.models import User


def test_signed_in_home_page_has_a_clear_roommate_call_to_action(db):
    user = User.objects.create_user("viewer@example.com", "Correct-Horse-42")
    client = Client()
    client.force_login(user)

    response = client.get("/")

    assert response.status_code == 200
    assert b"Browse roommates" in response.content
    assert b'href="/roommates/"' in response.content
