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
        budget_range=BudgetRange.B2501_3000,
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


@pytest.mark.parametrize("search_name", ["alice johnson", "ALICE", "Ali"])
def test_name_search_is_case_insensitive_and_matches_partial_names(
    client, location, search_name
):
    viewer = make_roommate("viewer@example.com", "Viewer", location)
    make_roommate("alice@example.com", "Alice Johnson", location)
    make_roommate("bob@example.com", "Bob Smith", location)
    client.force_login(viewer)

    response = client.get("/roommates/", {"name": search_name})

    assert response.status_code == 200
    assert b"Alice Johnson" in response.content
    assert b"Bob Smith" not in response.content


def test_name_search_combines_with_all_existing_filters(client, location):
    viewer = make_roommate("viewer@example.com", "Viewer", location)
    make_roommate("matching@example.com", "Alice Johnson", location)

    other_location = Location.objects.create(city="Brooklyn", state="NY")
    wrong_location = make_roommate("location@example.com", "Alice Location", other_location)
    wrong_budget = make_roommate("budget@example.com", "Alice Budget", location)
    wrong_pets = make_roommate("pets@example.com", "Alice Pets", location)
    Preference.objects.filter(user=wrong_budget).update(
        budget_range=BudgetRange.B2001_2500
    )
    Preference.objects.filter(user=wrong_pets).update(
        pets_preference=PetsPreference.PET_FRIENDLY
    )
    client.force_login(viewer)

    response = client.get(
        "/roommates/",
        {
            "name": "alice",
            "location": location.location_id,
            "budget": BudgetRange.B2501_3000,
            "pets": PetsPreference.NO_PETS,
        },
    )

    assert response.status_code == 200
    assert b"Alice Johnson" in response.content
    assert b"Alice Location" not in response.content
    assert b"Alice Budget" not in response.content
    assert b"Alice Pets" not in response.content
    assert b"Viewer" not in response.content


def test_name_search_with_no_matches_shows_filtered_empty_state(client, location):
    viewer = make_roommate("viewer@example.com", "Viewer", location)
    make_roommate("alice@example.com", "Alice Johnson", location)
    client.force_login(viewer)

    response = client.get("/roommates/", {"name": "Nobody"})

    assert response.status_code == 200
    assert b"No matches found" in response.content
    assert b"Try different filters or clear them" in response.content
    assert b"Clear all filters" in response.content


def test_search_preserves_name_and_selected_filter_values(client, location):
    viewer = make_roommate("viewer@example.com", "Viewer", location)
    make_roommate("alice@example.com", "Alice Johnson", location)
    client.force_login(viewer)

    response = client.get(
        "/roommates/",
        {
            "name": "Ali",
            "location": location.location_id,
            "budget": BudgetRange.B2501_3000,
            "pets": PetsPreference.NO_PETS,
        },
    )

    assert response.status_code == 200
    assert b'<input id="name" name="name" type="search" value="Ali">' in response.content
    assert (
        f'<option value="{location.location_id}" selected>'.encode()
        in response.content
    )
    assert (
        f'<option value="{BudgetRange.B2501_3000}" selected>'.encode()
        in response.content
    )
    assert (
        f'<option value="{PetsPreference.NO_PETS}" selected>'.encode()
        in response.content
    )


def test_clear_filters_clears_name_search(client, location):
    viewer = make_roommate("viewer@example.com", "Viewer", location)
    make_roommate("alice@example.com", "Alice Johnson", location)
    make_roommate("bob@example.com", "Bob Smith", location)
    client.force_login(viewer)

    response = client.get("/roommates/", {"name": "Alice"})

    assert b"Alice Johnson" in response.content
    assert b"Bob Smith" not in response.content
    assert b'href="/roommates/"' in response.content

    cleared_response = client.get("/roommates/")

    assert cleared_response.status_code == 200
    assert b"Alice Johnson" in cleared_response.content
    assert b"Bob Smith" in cleared_response.content
    assert b"Showing all roommates" in cleared_response.content


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
    assert b"$2,501-$3,000 / month" in response.content
    assert b"No pets" in response.content


def test_unavailable_roommate_profile_is_not_exposed(client, location):
    viewer = make_roommate("viewer@example.com", "Viewer", location)
    unavailable = make_roommate("maya@example.com", "Maya", location)
    unavailable.profile.delete()
    client.force_login(viewer)

    response = client.get(f"/roommates/{unavailable.user_id}/")

    assert response.status_code == 404
    assert b"Profile unavailable" in response.content
