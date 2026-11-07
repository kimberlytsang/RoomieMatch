"""US-04 / US-05 / US-06: saved preferences and location suggestions."""
import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from profiles import services
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile

URL = "/api/preferences/me"


@pytest.fixture
def user(db):
    return User.objects.create_user("preferences@example.com", "Correct-Horse-42")


@pytest.fixture
def signed_in(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def locations(db):
    return {
        city: Location.objects.create(city=city, state="NY")
        for city in ("Manhattan", "Brooklyn")
    }


@pytest.fixture
def values(locations):
    return {
        "location_id": locations["Manhattan"].pk,
        "budget_range": BudgetRange.B1001_1500,
        "pets_preference": PetsPreference.NO_PETS,
    }


@pytest.fixture
def profile(user, values):
    profile = services.create_profile(user, display_name="Avery", bio="Quiet home.", **values)
    profile.profile_picture = b"existing-photo"
    profile.save(update_fields=["profile_picture"])
    return profile


def test_get_missing_preferences_returns_404(signed_in, user):
    assert reverse("preferences-me") == URL
    response = signed_in.get(URL)
    assert response.status_code == 404
    assert response.json() == {"error": "Preferences not set."}
    assert not Preference.objects.filter(user=user).exists()


def test_get_returns_only_current_users_preferences(signed_in, user, profile, locations):
    other = User.objects.create_user("other-preferences@example.com", "Correct-Horse-42")
    services.save_preferences(other, {
        "location_id": locations["Brooklyn"].pk,
        "budget_range": BudgetRange.OVER_3000,
        "pets_preference": PetsPreference.PET_FRIENDLY,
    })
    response = signed_in.get(URL, {"user_id": str(other.pk)})
    assert response.status_code == 200
    assert response.json() == {
        "location_id": locations["Manhattan"].pk,
        "location_name": "Manhattan, NY",
        "budget_range": BudgetRange.B1001_1500,
        "pets_preference": PetsPreference.NO_PETS,
    }
    assert response["Cache-Control"] == "private, no-store"


@pytest.mark.parametrize("budget_range", BudgetRange.values)
def test_put_creates_preferences_with_each_budget_range(signed_in, user, values, budget_range):
    values["budget_range"] = budget_range
    response = signed_in.put(URL, values, content_type="application/json")
    assert response.status_code == 200
    saved = Preference.objects.get(user=user)
    assert saved.budget_range == budget_range
    assert saved.location_id == values["location_id"]
    assert saved.pets_preference == PetsPreference.NO_PETS
    assert signed_in.get(URL).json()["budget_range"] == budget_range
    assert not Profile.objects.filter(user=user).exists()


@pytest.mark.parametrize("pets_preference", PetsPreference.values)
def test_saved_pet_preference_can_be_changed(signed_in, user, profile, values, pets_preference):
    response = signed_in.put(URL, {**values, "pets_preference": pets_preference}, content_type="application/json")
    assert response.status_code == 200
    assert Preference.objects.get(user=user).pets_preference == pets_preference
    assert Preference.objects.filter(user=user).count() == 1


def test_update_replaces_preferences_without_changing_profile_or_other_user(
    signed_in, user, profile, values, locations,
):
    other = User.objects.create_user("unchanged-preferences@example.com", "Correct-Horse-42")
    services.save_preferences(other, values)
    old_profile = Profile.objects.filter(user=user).values().get()
    other_preferences = Preference.objects.filter(user=other).values().get()
    changed = {
        "location_id": locations["Brooklyn"].pk,
        "budget_range": BudgetRange.B1501_2000,
        "pets_preference": PetsPreference.PET_FRIENDLY,
    }
    assert signed_in.put(URL, changed, content_type="application/json").status_code == 200
    saved = Preference.objects.get(user=user)
    assert saved.location_id == changed["location_id"]
    assert saved.budget_range == changed["budget_range"]
    assert saved.pets_preference == changed["pets_preference"]
    assert Preference.objects.filter(user=user).count() == 1
    assert Profile.objects.filter(user=user).values().get() == old_profile
    assert Preference.objects.filter(user=other).values().get() == other_preferences


def test_page_and_new_login_read_saved_choices(signed_in, user, profile, locations):
    changed = {
        "location_id": locations["Brooklyn"].pk,
        "budget_range": BudgetRange.B1501_2000,
        "pets_preference": PetsPreference.PET_FRIENDLY,
    }
    assert signed_in.put(URL, changed, content_type="application/json").status_code == 200
    for _ in range(2):
        page = signed_in.get(reverse("my-profile"))
        assert page.status_code == 200
        assert page.context["preference"].budget_range == changed["budget_range"]
        assert list(page.context["budget_ranges"]) == list(BudgetRange.choices)
        assert list(page.context["pets_preferences"]) == list(PetsPreference.choices)
        for text in (b"Brooklyn, NY", b"$1,501-$2,000", b"Pet friendly", b"Edit preferences"):
            assert text in page.content
    assert signed_in.post(reverse("auth-logout")).status_code == 204
    fresh = Client()
    assert fresh.post(reverse("auth-login"), {
        "email": user.email, "password": "Correct-Horse-42",
    }, content_type="application/json").status_code == 200
    saved = fresh.get(URL).json()
    assert {field: saved[field] for field in changed} == changed
    assert b"Brooklyn, NY" in fresh.get(reverse("my-profile")).content


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("field, invalid", [
    ("location_id", ""), ("location_id", None), ("location_id", True),
    ("location_id", 1.5), ("location_id", "invalid"), ("location_id", "\u00b2"),
    ("location_id", 2147483647), ("location_id", "9" * 5000),
    ("budget_range", ""), ("budget_range", None), ("budget_range", "INVALID"), ("budget_range", []),
    ("pets_preference", ""), ("pets_preference", None), ("pets_preference", "INVALID"), ("pets_preference", {}),
])
def test_invalid_preferences_do_not_create_or_partially_update(
    signed_in, user, values, field, invalid, existing,
):
    before = None
    if existing:
        services.save_preferences(user, values)
        before = Preference.objects.filter(user=user).values().get()
    changed = {**values, "budget_range": BudgetRange.OVER_3000, field: invalid}
    response = signed_in.put(URL, changed, content_type="application/json")
    assert response.status_code == 400
    assert response.json()["error"]
    if existing:
        assert Preference.objects.filter(user=user).values().get() == before
    else:
        assert not Preference.objects.filter(user=user).exists()


@pytest.mark.parametrize("missing", ["location_id", "budget_range", "pets_preference"])
def test_put_requires_all_three_fields(signed_in, user, values, missing):
    values.pop(missing)
    response = signed_in.put(URL, values, content_type="application/json")
    assert response.status_code == 400
    assert not Preference.objects.filter(user=user).exists()


def test_put_cannot_target_another_user(signed_in, user, values):
    other = User.objects.create_user("target-preferences@example.com", "Correct-Horse-42")
    services.save_preferences(other, values)
    before = Preference.objects.filter(user=other).values().get()
    response = signed_in.put(URL, {
        **values, "user_id": str(other.pk), "budget_range": BudgetRange.OVER_3000,
    }, content_type="application/json")
    assert response.status_code == 400
    assert not Preference.objects.filter(user=user).exists()
    assert Preference.objects.filter(user=other).values().get() == before


@pytest.mark.parametrize("body", ['[]', 'null', '{"broken":', b"\xff"])
def test_bad_json_returns_400(signed_in, user, body):
    response = signed_in.put(URL, body, content_type="application/json")
    assert response.status_code == 400
    assert not Preference.objects.filter(user=user).exists()


@pytest.mark.parametrize("method, url", [("get", URL), ("put", URL), ("get", "/api/locations?q=m")])
def test_preferences_and_locations_require_login(client, db, method, url):
    response = getattr(client, method)(url)
    assert response.status_code == 401


def test_put_requires_csrf_and_accepts_a_valid_token(user, values):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.put(URL, values, content_type="application/json").status_code == 403
    assert not Preference.objects.filter(user=user).exists()
    client.get(reverse("create-profile"))
    response = client.put(URL, values, content_type="application/json",
                          HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
    assert response.status_code == 200
    assert Preference.objects.get(user=user).pets_preference == PetsPreference.NO_PETS


@pytest.mark.parametrize("method, url", [
    ("post", URL), ("patch", URL), ("delete", URL), ("put", "/api/locations"),
])
def test_unsupported_methods_do_not_change_preferences(signed_in, user, profile, method, url):
    before = Preference.objects.filter(user=user).values().get()
    assert getattr(signed_in, method)(url).status_code == 405
    assert Preference.objects.filter(user=user).values().get() == before


@pytest.mark.parametrize("query", ["m", "M", "  mAn  "])
def test_locations_match_partial_names_ignoring_case(signed_in, locations, query):
    assert reverse("locations") == "/api/locations"
    response = signed_in.get(reverse("locations"), {"q": query})
    assert response.status_code == 200
    assert response.json() == [{
        "location_id": locations["Manhattan"].pk, "city": "Manhattan", "state": "NY",
    }]


@pytest.mark.parametrize("query", ["", "No such city"])
def test_location_search_with_no_matches_returns_empty_list(signed_in, locations, query):
    assert signed_in.get(reverse("locations"), {"q": query}).json() == []


@pytest.mark.parametrize("query", ["before\x00after", "x" * 101])
def test_invalid_location_queries_return_400(signed_in, query):
    response = signed_in.get(reverse("locations"), {"q": query})
    assert response.status_code == 400


def test_updated_preferences_are_used_by_profile_and_roommate_filters(
    signed_in, user, profile, values, locations,
):
    viewer = User.objects.create_user("preferences-viewer@example.com", "Correct-Horse-42")
    searcher = Client()
    searcher.force_login(viewer)
    search_url = reverse("roommate-list")
    old_filters = {
        "location": values["location_id"], "budget": values["budget_range"],
        "pets": values["pets_preference"],
    }
    assert searcher.get(search_url, old_filters).context["roommates"].filter(user=user).exists()
    changed = {
        "location_id": locations["Brooklyn"].pk,
        "budget_range": BudgetRange.OVER_3000,
        "pets_preference": PetsPreference.PET_FRIENDLY,
    }
    assert signed_in.put(URL, changed, content_type="application/json").status_code == 200
    assert not searcher.get(search_url, old_filters).context["roommates"].filter(user=user).exists()
    new_filters = {
        "location": changed["location_id"], "budget": changed["budget_range"],
        "pets": changed["pets_preference"],
    }
    assert searcher.get(search_url, new_filters).context["roommates"].filter(user=user).exists()
    detail = searcher.get(reverse("roommate-detail", args=[user.pk]))
    own_page = signed_in.get(reverse("my-profile"))
    for text in (b"Brooklyn, NY", b"$3,001+", b"Pet friendly"):
        assert text in detail.content
        assert text in own_page.content
