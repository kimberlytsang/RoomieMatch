"""US-12 tests for filtering the roommate-search results."""

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
def roommates(db):
    manhattan = Location.objects.create(city="Manhattan", state="NY")
    brooklyn = Location.objects.create(city="Brooklyn", state="NY")

    def create(email, name, location, budget, pets, sleep, parties):
        user = User.objects.create_user(email, "Correct-Horse-42")
        Profile.objects.create(user=user, display_name=name)
        Preference.objects.create(
            user=user,
            location=location,
            budget_range=budget,
            pets_preference=pets,
            sleep_preference=sleep,
            party_preference=parties,
        )
        return user

    viewer = create(
        "viewer@example.com", "Viewer", manhattan, BudgetRange.B2501_3000,
        PetsPreference.NO_PETS, SleepPreference.EARLY, PartyPreference.NO_PARTIES,
    )
    maya = create(
        "maya@example.com", "Maya", manhattan, BudgetRange.B2501_3000,
        PetsPreference.NO_PETS, SleepPreference.EARLY, PartyPreference.NO_PARTIES,
    )
    sam = create(
        "sam@example.com", "Sam", brooklyn, BudgetRange.B2001_2500,
        PetsPreference.PET_FRIENDLY, SleepPreference.LATE, PartyPreference.SOMETIMES,
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
            "sleep": SleepPreference.EARLY,
            "parties": PartyPreference.NO_PARTIES,
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


def test_sleep_and_party_filters_are_applied_separately(client, roommates):
    client.force_login(roommates["viewer"])

    response = client.get(
        "/roommates/",
        {"sleep": SleepPreference.EARLY, "parties": PartyPreference.NO_PARTIES},
    )

    assert response.status_code == 200
    assert b"Maya" in response.content
    assert b"Sam" not in response.content
    assert b"Sleep early" in response.content
    assert b"No pets" in response.content
    assert b"No parties" in response.content
    assert b"Sleep: Sleep early" not in response.content


def test_pet_no_preference_label_is_specific_to_pets(client, roommates):
    client.force_login(roommates["viewer"])

    response = client.get("/roommates/")

    assert response.status_code == 200
    assert b"No preference with pets" in response.content


def test_sleep_and_party_no_preference_values_are_not_filter_options(client, roommates):
    client.force_login(roommates["viewer"])

    response = client.get("/roommates/")

    assert response.status_code == 200
    assert b"No preference with sleep" not in response.content
    assert b"No preference with parties" not in response.content
