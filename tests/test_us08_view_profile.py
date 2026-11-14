"""US-08 tests for viewing another seeker's shared profile."""

import pytest
from django.test import Client

from accounts.models import User
from profiles.models import (
    BudgetRange,
    Location,
    PartyPreference,
    PetsPreference,
    Preference,
    Profile,
    SleepPreference,
)


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def profiles(db):
    location = Location.objects.create(city="Boston", state="MA")

    def create(email, name, *, sleep, pets, parties):
        user = User.objects.create_user(email, "Correct-Horse-42")
        Profile.objects.create(user=user, display_name=name, bio=f"Hello from {name}.")
        Preference.objects.create(
            user=user,
            location=location,
            budget_range=BudgetRange.B1001_1500,
            sleep_preference=sleep,
            pets_preference=pets,
            party_preference=parties,
        )
        return user

    viewer = create(
        "viewer@example.com",
        "Viewer",
        sleep=SleepPreference.NO_PREFERENCE,
        pets=PetsPreference.NO_PREFERENCE,
        parties=PartyPreference.NO_PREFERENCE,
    )
    roommate = create(
        "maya@example.com",
        "Maya",
        sleep=SleepPreference.EARLY,
        pets=PetsPreference.NO_PETS,
        parties=PartyPreference.NO_PARTIES,
    )
    return {"viewer": viewer, "roommate": roommate}


def test_selecting_a_search_result_opens_that_roommates_profile(client, profiles):
    client.force_login(profiles["viewer"])

    results = client.get("/roommates/")
    detail_url = f"/roommates/{profiles['roommate'].user_id}/"
    response = client.get(detail_url)

    assert results.status_code == 200
    assert detail_url.encode() in results.content
    assert response.status_code == 200
    assert b"Maya" in response.content


def test_profile_shows_shared_housing_and_lifestyle_preferences(client, profiles):
    client.force_login(profiles["viewer"])

    response = client.get(f"/roommates/{profiles['roommate'].user_id}/")

    assert response.status_code == 200
    assert b"$1,001-$1,500 / month" in response.content
    assert b"Boston, MA" in response.content
    assert b"Sleep early \xc2\xb7 No pets \xc2\xb7 No parties" in response.content
    assert b"Sleep: Sleep early" not in response.content


def test_unavailable_profile_shows_a_safe_message(client, profiles):
    client.force_login(profiles["viewer"])
    profiles["roommate"].profile.delete()

    response = client.get(f"/roommates/{profiles['roommate'].user_id}/")

    assert response.status_code == 404
    assert b"Profile unavailable" in response.content


def test_profile_requires_authentication(client, profiles):
    response = client.get(f"/roommates/{profiles['roommate'].user_id}/")

    assert response.status_code == 302
    assert response.url == f"/login/?next=/roommates/{profiles['roommate'].user_id}/"
