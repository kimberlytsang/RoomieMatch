"""US-12 tests for filtering the roommate-search results."""

import pytest
from django.test import Client

from accounts.models import User
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def roommates(db):
    manhattan = Location.objects.create(city="Manhattan", state="NY")
    brooklyn = Location.objects.create(city="Brooklyn", state="NY")

    def create(email, name, location, budget, pets):
        user = User.objects.create_user(email, "Correct-Horse-42")
        Profile.objects.create(user=user, display_name=name)
        Preference.objects.create(
            user=user,
            location=location,
            budget_range=budget,
            pets_preference=pets,
        )
        return user

    viewer = create(
        "viewer@example.com", "Viewer", manhattan, BudgetRange.B2501_3000, PetsPreference.NO_PETS
    )
    maya = create(
        "maya@example.com", "Maya", manhattan, BudgetRange.B2501_3000, PetsPreference.NO_PETS
    )
    sam = create(
        "sam@example.com", "Sam", brooklyn, BudgetRange.B2001_2500, PetsPreference.PET_FRIENDLY
    )
    return {"viewer": viewer, "maya": maya, "sam": sam, "manhattan": manhattan, "brooklyn": brooklyn}


def test_location_filter_shows_only_matching_roommates(client, roommates):
    client.force_login(roommates["viewer"])

    response = client.get("/roommates/", {"location": roommates["manhattan"].location_id})

    assert response.status_code == 200
    assert b"Maya" in response.content
    assert b"Sam" not in response.content


def test_multiple_filters_require_all_selected_preferences(client, roommates):
    client.force_login(roommates["viewer"])

    response = client.get(
        "/roommates/",
        {
            "location": roommates["manhattan"].location_id,
            "budget": BudgetRange.B2501_3000,
            "pets": PetsPreference.NO_PETS,
        },
    )

    assert response.status_code == 200
    assert b"Maya" in response.content
    assert b"Sam" not in response.content


def test_filters_with_no_matches_show_empty_state_and_clear_link(client, roommates):
    client.force_login(roommates["viewer"])

    response = client.get("/roommates/", {"budget": BudgetRange.OVER_3000})

    assert response.status_code == 200
    assert b"No matches found" in response.content
    assert b"Clear all filters" in response.content
    assert b'href="/roommates/"' in response.content


def test_clear_filters_returns_to_the_unfiltered_roommate_list(client, roommates):
    client.force_login(roommates["viewer"])

    response = client.get("/roommates/")

    assert response.status_code == 200
    assert b"Maya" in response.content
    assert b"Sam" in response.content
    assert b"Showing all roommates" in response.content
