"""US-15: authenticated profile creation and its form validation."""

from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from profiles import services
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile


@pytest.fixture
def user(db):
    return User.objects.create_user("new-roomie@example.com", "Correct-Horse-42")


@pytest.fixture
def signed_in(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def details(db):
    location = Location.objects.create(city="Brooklyn", state="NY")
    return {
        "display_name": "  Avery  ",
        "bio": "  I enjoy cooking and a quiet home.  ",
        "location_id": str(location.pk),
        "budget_range": BudgetRange.B1001_1500,
        "pets_preference": PetsPreference.NO_PETS,
    }


@pytest.mark.parametrize("method", ["get", "post"])
def test_creation_requires_login(client, method):
    response = getattr(client, method)(reverse("create-profile"))
    assert response.status_code == 302
    assert response.url == "/login/?next=/create-profile/"


def test_new_user_can_open_form_and_profile_entry(signed_in, user, details):
    response = signed_in.get(reverse("create-profile"))
    assert response.status_code == 200
    assert b"Create your profile" in response.content
    assert b"Brooklyn, NY" in response.content
    assert b"csrfmiddlewaretoken" in response.content
    assert b'enctype="multipart/form-data"' in response.content
    assert b'name="profile_picture" type="file"' in response.content
    assert b"This preference is not saved" in response.content
    assert not Profile.objects.filter(user=user).exists()
    assert signed_in.get(reverse("my-profile")).url == reverse("create-profile")


def test_creation_saves_current_users_profile_and_redirects_to_d1(signed_in, user, details):
    other = User.objects.create_user("other-roomie@example.com", "Correct-Horse-42")
    response = signed_in.post(reverse("create-profile"), {**details, "user_id": str(other.pk)})
    assert response.status_code == 302
    assert response.url == reverse("my-profile")
    profile = Profile.objects.get(user=user)
    preference = Preference.objects.get(user=user)
    assert profile.display_name == "Avery"
    assert profile.bio == "I enjoy cooking and a quiet home."
    assert profile.profile_picture is None
    assert preference.location_id == int(details["location_id"])
    assert preference.budget_range == BudgetRange.B1001_1500
    assert preference.pets_preference == PetsPreference.NO_PETS
    assert not Profile.objects.filter(user=other).exists()
    page = signed_in.get(response.url)
    assert page.status_code == 200
    for text in [b"Avery", b"Brooklyn, NY", b"I enjoy cooking", b"$1,001-$1,500", b"No pets"]:
        assert text in page.content


def test_bio_is_optional(signed_in, user, details):
    details["bio"] = ""
    assert signed_in.post(reverse("create-profile"), details).status_code == 302
    assert Profile.objects.get(user=user).bio == ""


@pytest.mark.parametrize("field, value", [
    ("display_name", ""),
    ("display_name", "   "),
    ("display_name", "a" * 51),
    ("bio", "a" * 501),
    ("location_id", ""),
    ("location_id", "not-a-location"),
    ("location_id", "2147483647"),
    ("location_id", "9" * 50),
    ("budget_range", ""),
    ("budget_range", "INVALID"),
    ("pets_preference", ""),
    ("pets_preference", "HAVE_PETS"),
])
def test_invalid_fields_are_rejected_without_partial_records(signed_in, user, details, field, value):
    details[field] = value
    response = signed_in.post(reverse("create-profile"), details)
    assert response.status_code == 400
    assert field in response.context["errors"]
    assert response.context["values"][field] == value
    assert not Profile.objects.filter(user=user).exists()
    assert not Preference.objects.filter(user=user).exists()


def test_missing_fields_are_rejected(signed_in, user):
    response = signed_in.post(reverse("create-profile"), {})
    assert response.status_code == 400
    assert set(response.context["errors"]) == {"display_name", "location_id", "budget_range", "pets_preference"}
    assert not Profile.objects.filter(user=user).exists()


@pytest.mark.parametrize("method", ["get", "post"])
def test_existing_profile_is_never_overwritten(signed_in, user, details, method):
    services.create_profile(user, **details)
    changed = {**details, "display_name": "Replacement", "budget_range": BudgetRange.OVER_3000}
    response = getattr(signed_in, method)(reverse("create-profile"), changed)
    assert response.status_code == 302
    assert response.url == reverse("my-profile")
    assert Profile.objects.get(user=user).display_name == "Avery"
    assert Preference.objects.get(user=user).budget_range == BudgetRange.B1001_1500
    with pytest.raises(services.ProfileAlreadyExists):
        services.create_profile(user, **changed)
    assert Profile.objects.filter(user=user).count() == 1


def test_profile_failure_rolls_back_preference(user, details):
    with patch("profiles.services.Profile.objects.create", side_effect=RuntimeError("save failed")):
        with pytest.raises(RuntimeError):
            services.create_profile(user, **details)
    assert not Profile.objects.filter(user=user).exists()
    assert not Preference.objects.filter(user=user).exists()


def test_creation_requires_csrf_and_accepts_valid_token(user, details):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.post(reverse("create-profile"), details).status_code == 403
    assert not Profile.objects.filter(user=user).exists()
    client.get(reverse("create-profile"))
    response = client.post(reverse("create-profile"), {
        **details, "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
    })
    assert response.status_code == 302
    assert Profile.objects.filter(user=user).exists()


def test_unsupported_methods_cannot_create(signed_in, user):
    assert signed_in.put(reverse("create-profile")).status_code == 405
    assert not Profile.objects.filter(user=user).exists()
