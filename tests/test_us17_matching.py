"""US-17 tests for rule-based roommate recommendations."""

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import Role, User
from profiles.matching import compatibility_percentage
from profiles.models import (
    BudgetRange,
    Location,
    PartyPreference,
    PetsPreference,
    Preference,
    Profile,
    SleepPreference,
)


PASSWORD = "Correct-Horse-42"


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def locations(db):
    return {
        "manhattan": Location.objects.create(city="Manhattan", state="NY"),
        "brooklyn": Location.objects.create(city="Brooklyn", state="NY"),
    }


def create_roommate(
    email,
    name,
    location,
    *,
    budget=BudgetRange.B2501_3000,
    pets=PetsPreference.NO_PETS,
    sleep=SleepPreference.EARLY,
    parties=PartyPreference.NO_PARTIES,
    role=Role.SEEKER,
    with_profile=True,
    with_preferences=True,
):
    user = User.objects.create_user(email, PASSWORD, role=role)
    if with_profile:
        Profile.objects.create(user=user, display_name=name)
    if with_preferences:
        Preference.objects.create(
            user=user,
            location=location,
            budget_range=budget,
            pets_preference=pets,
            sleep_preference=sleep,
            party_preference=parties,
        )
    return user


def suggested(client):
    return client.get(reverse("roommate-list"), {"mode": "suggested"})


def test_fully_matching_preferences_score_one_hundred_percent(db, locations):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    candidate = create_roommate("candidate@example.com", "Candidate", locations["manhattan"])
    score = compatibility_percentage(viewer.preference, candidate.preference)
    assert score == 100


def test_partially_matching_preferences_use_weighted_percentage(db, locations):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    candidate = create_roommate(
        "candidate@example.com",
        "Candidate",
        locations["manhattan"],
        budget=BudgetRange.B2001_2500,
        sleep=SleepPreference.LATE,
    )
    assert compatibility_percentage(viewer.preference, candidate.preference) == 55


def test_no_matching_preferences_score_zero(db, locations):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    candidate = create_roommate(
        "candidate@example.com",
        "Candidate",
        locations["brooklyn"],
        budget=BudgetRange.B2001_2500,
        pets=PetsPreference.PET_FRIENDLY,
        sleep=SleepPreference.LATE,
        parties=PartyPreference.OFTEN,
    )
    assert compatibility_percentage(viewer.preference, candidate.preference) == 0


def test_no_preference_categories_are_excluded_and_remaining_weights_normalized(
    db, locations
):
    viewer = create_roommate(
        "viewer@example.com",
        "Viewer",
        locations["manhattan"],
        pets=PetsPreference.NO_PREFERENCE,
        parties=PartyPreference.NO_PREFERENCE,
    )
    candidate = create_roommate(
        "candidate@example.com",
        "Candidate",
        locations["manhattan"],
        pets=PetsPreference.PET_FRIENDLY,
        parties=PartyPreference.OFTEN,
        sleep=SleepPreference.LATE,
    )
    # Location + budget match (60); only sleep (15) is applicable and differs.
    assert compatibility_percentage(viewer.preference, candidate.preference) == 80


def test_no_comparable_preferences_return_no_score():
    class NoPreferences:
        location_id = None
        budget_range = None
        pets_preference = PetsPreference.NO_PREFERENCE
        sleep_preference = SleepPreference.NO_PREFERENCE
        party_preference = PartyPreference.NO_PREFERENCE

    assert compatibility_percentage(NoPreferences(), NoPreferences()) is None


@pytest.mark.parametrize("with_profile,with_preferences", [(False, True), (True, False)])
def test_viewer_with_incomplete_profile_gets_helpful_message(
    client, locations, with_profile, with_preferences
):
    viewer = create_roommate(
        "viewer@example.com",
        "Viewer",
        locations["manhattan"],
        with_profile=with_profile,
        with_preferences=with_preferences,
    )
    create_roommate("candidate@example.com", "Candidate", locations["manhattan"])
    client.force_login(viewer)

    response = suggested(client)

    assert response.status_code == 200
    assert b"Complete your roommate profile and preferences" in response.content
    assert b"Complete your profile" in response.content
    assert b"% compatible" not in response.content


def test_incomplete_candidate_is_excluded(client, locations):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    create_roommate(
        "candidate@example.com",
        "Incomplete Candidate",
        locations["manhattan"],
        with_preferences=False,
    )
    client.force_login(viewer)

    response = suggested(client)

    assert response.status_code == 200
    assert b"Incomplete Candidate" not in response.content
    assert b"no other eligible roommate profiles to recommend" in response.content


def test_zero_compatibility_candidates_are_excluded_with_empty_state(
    client, locations
):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    create_roommate(
        "candidate@example.com",
        "No Match",
        locations["brooklyn"],
        budget=BudgetRange.B2001_2500,
        pets=PetsPreference.PET_FRIENDLY,
        sleep=SleepPreference.LATE,
        parties=PartyPreference.OFTEN,
    )
    client.force_login(viewer)

    response = suggested(client)

    assert response.status_code == 200
    assert b"No Match" not in response.content
    assert b"positive compatibility score" in response.content
    assert b"0% compatible" not in response.content


def test_positive_compatibility_scores_use_color_bands(client, locations):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    create_roommate("green@example.com", "Green Match", locations["manhattan"])
    create_roommate(
        "amber@example.com",
        "Amber Match",
        locations["manhattan"],
        budget=BudgetRange.B2001_2500,
        sleep=SleepPreference.LATE,
    )
    create_roommate(
        "red@example.com",
        "Red Match",
        locations["manhattan"],
        budget=BudgetRange.B2001_2500,
        pets=PetsPreference.PET_FRIENDLY,
        sleep=SleepPreference.LATE,
        parties=PartyPreference.OFTEN,
    )
    client.force_login(viewer)

    response = suggested(client)

    assert response.status_code == 200
    assert (
        b'<p class="compatibility-score compatibility-score-high">100% compatible</p>'
        in response.content
    )
    assert (
        b'<p class="compatibility-score compatibility-score-medium">55% compatible</p>'
        in response.content
    )
    assert (
        b'<p class="compatibility-score compatibility-score-low">30% compatible</p>'
        in response.content
    )


def test_suggestions_exclude_viewer_deleted_profiles_and_admin_accounts(
    client, locations
):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    create_roommate("candidate@example.com", "Eligible", locations["manhattan"])
    deleted = create_roommate("deleted@example.com", "Deleted", locations["manhattan"])
    deleted.profile.delete()
    create_roommate(
        "admin@example.com",
        "Admin",
        locations["manhattan"],
        role=Role.ADMIN,
    )
    client.force_login(viewer)

    response = suggested(client)

    assert response.status_code == 200
    assert b"Eligible" in response.content
    assert b"Viewer" not in response.content
    assert b"Deleted" not in response.content
    assert b"Admin" not in response.content


def test_suggestions_are_sorted_by_score_and_limited_to_five(client, locations):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    create_roommate("match@example.com", "A Full Match", locations["manhattan"])
    create_roommate(
        "partial@example.com",
        "B Partial Match",
        locations["manhattan"],
        sleep=SleepPreference.LATE,
    )
    create_roommate(
        "mismatch@example.com",
        "C Low Match",
        locations["brooklyn"],
        budget=BudgetRange.B2001_2500,
        pets=PetsPreference.PET_FRIENDLY,
        sleep=SleepPreference.LATE,
        parties=PartyPreference.OFTEN,
    )
    for index in range(5):
        create_roommate(
            f"extra{index}@example.com",
            f"Extra {index}",
            locations["manhattan"],
            sleep=SleepPreference.LATE,
        )
    client.force_login(viewer)

    response = suggested(client)

    assert response.status_code == 200
    rendered = response.context["roommates"]
    assert len(rendered) == 5
    scores = [profile.compatibility_percentage for profile in rendered]
    assert scores == sorted(scores, reverse=True)
    assert [profile.display_name for profile in rendered][0] == "A Full Match"
    assert "C Low Match" not in [profile.display_name for profile in rendered]
    assert b"100% compatible" in response.content


def test_suggestions_use_user_id_to_break_identical_score_and_name_ties(
    client, locations
):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    candidates = [
        create_roommate(
            f"same-name-{index}@example.com",
            "Same Name",
            locations["manhattan"],
        )
        for index in range(7)
    ]
    expected_user_ids = sorted(str(user.user_id) for user in candidates)[:5]
    client.force_login(viewer)

    response = suggested(client)

    assert response.status_code == 200
    rendered = response.context["roommates"]
    assert len(rendered) == 5
    assert [str(profile.user_id) for profile in rendered] == expected_user_ids
    assert len({profile.compatibility_percentage for profile in rendered}) == 1


def test_suggestions_use_updated_preferences_on_next_request(client, locations):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    candidate = create_roommate("candidate@example.com", "Candidate", locations["manhattan"])
    client.force_login(viewer)

    first_response = suggested(client)
    assert b"100% compatible" in first_response.content

    Preference.objects.filter(user=candidate).update(
        budget_range=BudgetRange.B2001_2500
    )
    second_response = suggested(client)

    assert b"70% compatible" in second_response.content


def test_suggestions_require_authentication(client):
    response = suggested(client)
    assert response.status_code == 302
    assert response.url == "/login/?next=/roommates/%3Fmode%3Dsuggested"


def test_user_can_return_to_regular_search_without_compatibility_scores(
    client, locations
):
    viewer = create_roommate("viewer@example.com", "Viewer", locations["manhattan"])
    create_roommate("candidate@example.com", "Candidate", locations["manhattan"])
    client.force_login(viewer)

    suggestions_response = suggested(client)
    regular_response = client.get(reverse("roommate-list"))

    assert b"100% compatible" in suggestions_response.content
    assert b"Back to search results" in suggestions_response.content
    assert b'class="roommate-filters"' not in suggestions_response.content
    assert regular_response.status_code == 200
    assert b'class="roommate-filters"' in regular_response.content
    assert b"Candidate" in regular_response.content
    assert b"Suggested Roommates" in regular_response.content
    assert b"% compatible" not in regular_response.content
