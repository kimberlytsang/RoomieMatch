"""US-15 Profile CRUD API tests."""
import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from profiles import services
from profiles.models import (
    BudgetRange, Location, PartyPreference, PetsPreference, Preference, Profile, SleepPreference,
)

URL = "/api/profiles/me"


@pytest.fixture
def user(db):
    return User.objects.create_user("profile-api@example.com", "Correct-Horse-42")


@pytest.fixture
def signed_in(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def details(db):
    location = Location.objects.create(city="Brooklyn", state="NY")
    return {
        "display_name": "  Avery  ",
        "bio": "  I like cooking.  ",
        "location_id": location.pk,
        "budget_range": BudgetRange.B1001_1500,
        "pets_preference": PetsPreference.NO_PETS,
    }


@pytest.fixture
def profile(user, details):
    return services.create_profile(user, **details)


def test_post_creates_profile_and_preferences(signed_in, user, details):
    assert reverse("profile-me") == URL
    response = signed_in.post(URL, details, content_type="application/json")
    assert response.status_code == 201
    assert response.json() == {
        "user_id": str(user.pk), "display_name": "Avery", "bio": "I like cooking.",
    }
    saved = Profile.objects.get(user=user)
    assert saved.display_name == "Avery"
    assert saved.bio == "I like cooking."
    assert saved.profile_picture is None
    preference = Preference.objects.get(user=user)
    assert preference.location_id == details["location_id"]
    assert preference.budget_range == details["budget_range"]
    assert preference.pets_preference == details["pets_preference"]
    assert preference.sleep_preference == SleepPreference.NO_PREFERENCE
    assert preference.party_preference == PartyPreference.NO_PREFERENCE


def test_get_reads_only_own_profile(signed_in, user, profile):
    other = User.objects.create_user("other-api@example.com", "Correct-Horse-42")
    Profile.objects.create(user=other, display_name="Other user", bio="Private to this profile")
    response = signed_in.get(URL, {"user_id": str(other.pk)})
    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(user.pk), "display_name": "Avery", "bio": "I like cooking.",
    }


def test_patch_updates_name_and_bio_without_touching_preferences(signed_in, user, profile):
    before = Preference.objects.filter(user=user).values().get()
    response = signed_in.patch(URL, {
        "display_name": "  Avery Updated  ", "bio": "  New introduction.  ",
    }, content_type="application/json")
    assert response.status_code == 200
    profile.refresh_from_db()
    assert profile.display_name == "Avery Updated"
    assert profile.bio == "New introduction."
    assert response.json()["display_name"] == profile.display_name
    assert Preference.objects.filter(user=user).values().get() == before
    assert Profile.objects.filter(user=user).count() == 1


def test_patch_can_clear_bio_without_changing_name(signed_in, profile):
    response = signed_in.patch(URL, {"bio": ""}, content_type="application/json")
    assert response.status_code == 200
    profile.refresh_from_db()
    assert profile.bio == ""
    assert profile.display_name == "Avery"


def test_delete_preserves_account_preferences_and_other_profiles(signed_in, user, profile, details):
    other = User.objects.create_user("other-delete@example.com", "Correct-Horse-42")
    services.create_profile(other, **details)
    before = Preference.objects.filter(user=user).values().get()
    response = signed_in.delete(URL)
    assert response.status_code == 204
    assert response.content == b""
    assert not Profile.objects.filter(user=user).exists()
    assert User.objects.filter(pk=user.pk).exists()
    assert Preference.objects.filter(user=user).values().get() == before
    assert Profile.objects.filter(user=other).exists()
    assert Preference.objects.filter(user=other).exists()
    assert signed_in.session["_auth_user_id"] == str(user.pk)
    assert signed_in.get(URL).status_code == 404
    assert signed_in.post(URL, details, content_type="application/json").status_code == 201


@pytest.mark.parametrize("method", ["get", "post", "patch", "delete"])
def test_api_requires_login(client, db, method):
    response = getattr(client, method)(URL)
    assert response.status_code == 401
    assert response.json() == {"error": "Authentication required."}


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_missing_profile_returns_404(signed_in, method):
    response = getattr(signed_in, method)(URL, {"bio": "Updated"}, content_type="application/json")
    assert response.status_code == 404
    assert response.json() == {"error": "Profile not found."}


def test_duplicate_post_cannot_overwrite_existing_profile(signed_in, user, profile, details):
    response = signed_in.post(URL, {**details, "display_name": "Replacement"}, content_type="application/json")
    assert response.status_code == 409
    assert "error" in response.json()
    profile.refresh_from_db()
    assert profile.display_name == "Avery"
    assert Profile.objects.filter(user=user).count() == 1


@pytest.mark.parametrize("method", ["post", "patch", "delete"])
def test_write_requires_csrf(user, profile, details, method):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    response = getattr(client, method)(URL, details, content_type="application/json")
    assert response.status_code == 403
    profile.refresh_from_db()
    assert profile.display_name == "Avery"


def test_valid_csrf_allows_create_update_and_delete(user, details):
    details.update(sleep_preference=SleepPreference.LATE, party_preference=PartyPreference.OFTEN)
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    client.get("/create-profile/")
    headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}
    assert client.post(URL, details, content_type="application/json", **headers).status_code == 201
    assert client.patch(URL, {"bio": "Updated"}, content_type="application/json", **headers).status_code == 200
    assert client.delete(URL, **headers).status_code == 204
    assert not Profile.objects.filter(user=user).exists()


@pytest.mark.parametrize("method", ["post", "patch"])
@pytest.mark.parametrize("body", ['{"broken":', '[]'])
def test_invalid_json_returns_error(signed_in, user, method, body):
    response = getattr(signed_in, method)(URL, body, content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()
    assert not Profile.objects.filter(user=user).exists()


@pytest.mark.parametrize("field, value", [
    ("display_name", None), ("bio", 123), ("location_id", True),
    ("location_id", 1.5), ("budget_range", []), ("pets_preference", {}),
    ("display_name", " "), ("location_id", "invalid"),
    ("sleep_preference", None), ("sleep_preference", []),
    ("sleep_preference", ""), ("sleep_preference", "INVALID"),
    ("party_preference", None), ("party_preference", True),
    ("party_preference", ""), ("party_preference", "INVALID"),
])
def test_post_rejects_invalid_values_without_saving(signed_in, user, details, field, value):
    response = signed_in.post(URL, {**details, field: value}, content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()
    assert not Profile.objects.filter(user=user).exists()
    assert not Preference.objects.filter(user=user).exists()


def test_post_requires_existing_create_fields(signed_in, user):
    response = signed_in.post(URL, {}, content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()
    assert not Profile.objects.filter(user=user).exists()


@pytest.mark.parametrize("changes", [
    {}, {"display_name": " "}, {"bio": None}, {"display_name": "a" * 51},
    {"bio": "a" * 501}, {"budget_range": "OVER_3000"},
])
def test_patch_rejects_invalid_or_unsupported_fields(signed_in, profile, changes):
    response = signed_in.patch(URL, changes, content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()
    profile.refresh_from_db()
    assert profile.display_name == "Avery"
    assert profile.bio == "I like cooking."


@pytest.mark.parametrize("method", ["post", "patch"])
def test_cannot_target_another_user(signed_in, user, details, method):
    other = User.objects.create_user("target@example.com", "Correct-Horse-42")
    other_profile = services.create_profile(other, **details)
    data = {**details, "user_id": str(other.pk)} if method == "post" else {"bio": "Changed", "user_id": str(other.pk)}
    response = getattr(signed_in, method)(URL, data, content_type="application/json")
    assert response.status_code == 400
    other_profile.refresh_from_db()
    assert other_profile.bio == "I like cooking."
    assert not Profile.objects.filter(user=user).exists()


def test_put_is_not_supported(signed_in):
    assert signed_in.put(URL, {}, content_type="application/json").status_code == 405


@pytest.mark.parametrize("field, label", [("display_name", "Name"), ("bio", "About me")])
def test_post_rejects_null_characters(signed_in, user, details, field, label):
    response = signed_in.post(URL, {**details, field: "Before\x00After"}, content_type="application/json")
    assert response.status_code == 400
    assert response.json() == {"error": f"{label} cannot contain null characters."}
    assert not Profile.objects.filter(user=user).exists()
    assert not Preference.objects.filter(user=user).exists()


@pytest.mark.parametrize("field, label", [("display_name", "Name"), ("bio", "About me")])
def test_patch_rejects_null_characters(signed_in, user, profile, field, label):
    before = Preference.objects.filter(user=user).values().get()
    changes = {"display_name": "New name", "bio": "New bio", field: "Before\x00After"}
    response = signed_in.patch(URL, changes, content_type="application/json")
    assert response.status_code == 400
    assert response.json() == {"error": f"{label} cannot contain null characters."}
    profile.refresh_from_db()
    assert profile.display_name == "Avery"
    assert profile.bio == "I like cooking."
    assert Preference.objects.filter(user=user).values().get() == before


@pytest.mark.parametrize("sleep, parties", list(zip(SleepPreference.values, PartyPreference.values)))
def test_post_accepts_lifestyle_choices(signed_in, user, details, sleep, parties):
    response = signed_in.post(URL, {
        **details, "sleep_preference": sleep, "party_preference": parties,
    }, content_type="application/json")
    assert response.status_code == 201
    saved = Preference.objects.get(user=user)
    assert saved.sleep_preference == sleep
    assert saved.party_preference == parties


def test_legacy_post_preserves_existing_lifestyle_choices(signed_in, user, details):
    services.save_preferences(user, {
        "location_id": details["location_id"], "budget_range": details["budget_range"],
        "pets_preference": details["pets_preference"], "sleep_preference": SleepPreference.LATE,
        "party_preference": PartyPreference.OFTEN,
    })
    before = Preference.objects.filter(user=user).values().get()
    assert signed_in.post(URL, details, content_type="application/json").status_code == 201
    assert Preference.objects.filter(user=user).values().get() == before
