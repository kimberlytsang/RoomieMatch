"""US-07 / browseable roommate-profile tests."""

import pytest
from django.test import Client

from accounts.models import User
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def location(db):
    return Location.objects.create(city="Manhattan", state="NY")


def make_roommate(email, name, location):
    user = User.objects.create_user(email, "Correct-Horse-42")
    Profile.objects.create(user=user, display_name=name, bio=f"Hello from {name}.")
    Preference.objects.create(
        user=user,
        location=location,
        budget_range=BudgetRange.B1501_2000,
        pets_preference=PetsPreference.NO_PETS,
    )
    return user


def test_signed_in_seeker_can_browse_other_roommates(client, location):
    viewer = make_roommate("viewer@example.com", "Viewer", location)
    roommate = make_roommate("maya@example.com", "Maya", location)
    client.force_login(viewer)

    response = client.get("/roommates/")

    assert response.status_code == 200
    assert b"Maya" in response.content
    assert b"Viewer" not in response.content
    assert f"/roommates/{roommate.user_id}/".encode() in response.content


def test_roommate_list_shows_empty_state_when_no_one_else_is_available(client, location):
    viewer = make_roommate("viewer@example.com", "Viewer", location)
    client.force_login(viewer)

    response = client.get("/roommates/")

    assert response.status_code == 200
    assert b"No matches found" in response.content


def test_roommate_list_requires_authentication(client):
    response = client.get("/roommates/")

    assert response.status_code == 302
    assert response.url == "/login/?next=/roommates/"


def test_selected_roommate_profile_shows_shared_preferences(client, location):
    viewer = make_roommate("viewer@example.com", "Viewer", location)
    roommate = make_roommate("maya@example.com", "Maya", location)
    client.force_login(viewer)

    response = client.get(f"/roommates/{roommate.user_id}/")

    assert response.status_code == 200
    assert b"Maya" in response.content
    assert b"Manhattan, NY" in response.content
    assert b"$1,501-$2,000 / month" in response.content
    assert b"No pets" in response.content


def test_unavailable_roommate_profile_is_not_exposed(client, location):
    viewer = make_roommate("viewer@example.com", "Viewer", location)
    unavailable = make_roommate("maya@example.com", "Maya", location)
    unavailable.profile.delete()
    client.force_login(viewer)

    response = client.get(f"/roommates/{unavailable.user_id}/")

    assert response.status_code == 404
    assert b"Profile unavailable" in response.content
