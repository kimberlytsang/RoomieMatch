"""US-15: real profile photos and profile/search integration."""
from io import BytesIO
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from PIL import Image

from accounts.models import User
from profiles import services
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile


def image_bytes(image_format="PNG", color="coral"):
    output = BytesIO()
    Image.new("RGB", (16, 16), color).save(output, format=image_format)
    return output.getvalue()


def photo_upload(image_format="PNG", color="coral"):
    extension = "jpg" if image_format == "JPEG" else "png"
    content_type = "image/jpeg" if image_format == "JPEG" else "image/png"
    return SimpleUploadedFile(
        f"avatar.{extension}", image_bytes(image_format, color), content_type=content_type,
    )


@pytest.fixture
def user(db):
    return User.objects.create_user("avatar@example.com", "Correct-Horse-42")


@pytest.fixture
def signed_in(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def details(db):
    location = Location.objects.create(city="Brooklyn", state="NY")
    return {
        "display_name": "Avery", "bio": "I like cooking.",
        "location_id": location.pk, "budget_range": BudgetRange.B1001_1500,
        "pets_preference": PetsPreference.NO_PETS,
    }


@pytest.fixture
def profile(user, details):
    return services.create_profile(user, **details, profile_picture=photo_upload())


@pytest.mark.parametrize("image_format, content_type", [("PNG", "image/png"), ("JPEG", "image/jpeg")])
def test_create_saves_and_displays_real_photo(signed_in, user, details, image_format, content_type):
    response = signed_in.post(reverse("create-profile"), {
        **details, "profile_picture": photo_upload(image_format),
    })
    assert response.status_code == 302
    assert response.url == reverse("my-profile")
    saved = Profile.objects.get(user=user)
    assert bytes(saved.profile_picture) == image_bytes(image_format)
    photo_url = reverse("profile-photo", args=[user.pk])
    page = signed_in.get(response.url)
    assert f'src="{photo_url}"'.encode() in page.content
    photo = signed_in.get(photo_url)
    assert photo.status_code == 200
    assert photo.content == image_bytes(image_format)
    assert photo["Content-Type"] == content_type
    assert photo["Cache-Control"] == "private, no-store"
    assert photo["X-Content-Type-Options"] == "nosniff"


def test_no_photo_uses_default(signed_in, user, details):
    services.create_profile(user, **details)
    page = signed_in.get(reverse("my-profile"))
    assert b'images/male_homepage_image.jpg' in page.content
    assert b'alt="Default profile photo"' in page.content
    assert signed_in.get(reverse("profile-photo", args=[user.pk])).status_code == 404


@pytest.mark.parametrize("image_format", ["JPEG", "PNG"])
def test_edit_replaces_photo_and_preserves_preferences(signed_in, user, profile, image_format):
    before = Preference.objects.filter(user=user).values().get()
    response = signed_in.post(reverse("my-profile"), {
        "display_name": "Avery Updated", "bio": "New bio.",
        "profile_picture": photo_upload(image_format, "navy"),
    })
    assert response.status_code == 302
    profile.refresh_from_db()
    assert profile.display_name == "Avery Updated"
    assert profile.bio == "New bio."
    assert bytes(profile.profile_picture) == image_bytes(image_format, "navy")
    photo = signed_in.get(reverse("profile-photo", args=[user.pk]))
    assert photo.content == bytes(profile.profile_picture)
    assert Preference.objects.filter(user=user).values().get() == before


def test_text_only_form_and_json_edits_keep_photo(signed_in, profile):
    original = bytes(profile.profile_picture)
    assert signed_in.post(reverse("my-profile"), {
        "display_name": "New name", "bio": "Form bio",
    }).status_code == 302
    assert signed_in.patch(reverse("profile-me"), {
        "bio": "API bio",
    }, content_type="application/json").status_code == 200
    profile.refresh_from_db()
    assert profile.display_name == "New name"
    assert profile.bio == "API bio"
    assert bytes(profile.profile_picture) == original


def test_photo_and_text_survive_refresh_and_new_login(signed_in, user, profile):
    assert signed_in.post(reverse("my-profile"), {
        "display_name": "Avery Updated", "bio": "Saved introduction.",
        "profile_picture": photo_upload("JPEG", "navy"),
    }).status_code == 302
    for _ in range(2):
        page = signed_in.get(reverse("my-profile"))
        assert b"Avery Updated" in page.content
        assert b"Saved introduction." in page.content
    assert signed_in.post(reverse("auth-logout")).status_code == 204
    assert signed_in.get(reverse("profile-photo", args=[user.pk])).status_code == 401
    new_session = Client()
    assert new_session.post(reverse("auth-login"), {
        "email": user.email, "password": "Correct-Horse-42",
    }, content_type="application/json").status_code == 200
    page = new_session.get(reverse("my-profile"))
    assert b"Avery Updated" in page.content
    assert b"Saved introduction." in page.content
    assert new_session.get(reverse("profile-photo", args=[user.pk])).content == image_bytes("JPEG", "navy")


@pytest.mark.parametrize("page_name", ["create-profile", "my-profile"])
@pytest.mark.parametrize("case", [
    "empty", "text", "gif", "svg", "corrupt_png", "truncated_jpeg",
    "too_large", "wrong_extension", "wrong_mime",
])
def test_invalid_uploads_do_not_save_partial_changes(signed_in, user, details, page_name, case):
    original = None
    if page_name == "my-profile":
        original = services.create_profile(user, **details, profile_picture=photo_upload())
        before_preference = Preference.objects.filter(user=user).values().get()
    png = image_bytes()
    files = {
        "empty": ("avatar.png", b"", "image/png"),
        "text": ("avatar.png", b"This is not an image.", "image/png"),
        "gif": ("avatar.gif", image_bytes("GIF"), "image/gif"),
        "svg": ("avatar.png", b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', "image/png"),
        "corrupt_png": ("avatar.png", png[:40] + b"broken" + png[46:], "image/png"),
        "truncated_jpeg": ("avatar.jpg", image_bytes("JPEG")[:-12], "image/jpeg"),
        "too_large": ("avatar.png", png + b"x" * (2 * 1024 * 1024 + 1 - len(png)), "image/png"),
        "wrong_extension": ("avatar.jpg", png, "image/png"),
        "wrong_mime": ("avatar.png", png, "image/jpeg"),
    }
    filename, content, content_type = files[case]
    response = signed_in.post(reverse(page_name), {
        **details, "display_name": "Should not save", "bio": "Should not save",
        "profile_picture": SimpleUploadedFile(filename, content, content_type=content_type),
    })
    assert response.status_code == 400
    assert "profile_picture" in response.context["errors"]
    assert response.context["values"]["display_name"] == "Should not save"
    if original is None:
        assert not Profile.objects.filter(user=user).exists()
        assert not Preference.objects.filter(user=user).exists()
    else:
        original.refresh_from_db()
        assert original.display_name == "Avery"
        assert original.bio == "I like cooking."
        assert bytes(original.profile_picture) == png
        assert Preference.objects.filter(user=user).values().get() == before_preference
        assert signed_in.get(reverse("profile-photo", args=[user.pk])).content == png


@pytest.mark.parametrize("pixel_limit", [100, 200])
def test_excessive_decoded_image_size_is_rejected(signed_in, user, details, monkeypatch, pixel_limit):
    # Lower Pillow's limit to test both its warning and error without a huge file.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", pixel_limit)
    response = signed_in.post(reverse("create-profile"), {
        **details, "profile_picture": photo_upload(),
    })
    assert response.status_code == 400
    assert "profile_picture" in response.context["errors"]
    assert not Profile.objects.filter(user=user).exists()


def test_photo_at_two_mb_limit_is_accepted(signed_in, user, details):
    png = image_bytes()
    data = png + b"\x00" * (2 * 1024 * 1024 - len(png))
    response = signed_in.post(reverse("create-profile"), {
        **details, "profile_picture": SimpleUploadedFile("avatar.png", data, content_type="image/png"),
    })
    assert response.status_code == 302
    assert len(Profile.objects.get(user=user).profile_picture) == 2 * 1024 * 1024


def test_invalid_name_does_not_replace_valid_photo(signed_in, profile):
    response = signed_in.post(reverse("my-profile"), {
        "display_name": "   ", "bio": "New bio", "profile_picture": photo_upload("JPEG"),
    })
    assert response.status_code == 400
    assert "display_name" in response.context["errors"]
    profile.refresh_from_db()
    assert profile.display_name == "Avery"
    assert profile.bio == "I like cooking."
    assert bytes(profile.profile_picture) == image_bytes()


@pytest.mark.parametrize("page_name", ["create-profile", "my-profile"])
def test_upload_requires_login(client, user, details, page_name):
    response = client.post(reverse(page_name), {**details, "profile_picture": photo_upload()})
    assert response.status_code == 302
    assert response.url.startswith("/login/?next=")
    assert not Profile.objects.filter(user=user).exists()


@pytest.mark.parametrize("page_name", ["create-profile", "my-profile"])
def test_photo_upload_requires_csrf(user, details, page_name):
    if page_name == "my-profile":
        services.create_profile(user, **details, profile_picture=photo_upload())
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    response = client.post(reverse(page_name), {
        **details, "profile_picture": photo_upload("JPEG"),
    })
    assert response.status_code == 403
    if page_name == "my-profile":
        assert bytes(Profile.objects.get(user=user).profile_picture) == image_bytes()
    else:
        assert not Profile.objects.filter(user=user).exists()
    client.get(reverse(page_name))
    response = client.post(reverse(page_name), {
        **details, "profile_picture": photo_upload("JPEG"),
        "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
    })
    assert response.status_code == 302
    assert bytes(Profile.objects.get(user=user).profile_picture) == image_bytes("JPEG")


def test_anonymous_users_cannot_read_photos(client, user, profile):
    assert client.get(reverse("profile-photo", args=[user.pk])).status_code == 401


def test_photo_visibility_matches_roommate_visibility(signed_in, user, profile, details):
    other = User.objects.create_user("visible-avatar@example.com", "Correct-Horse-42")
    services.create_profile(other, **details, profile_picture=photo_upload("JPEG"))
    url = reverse("profile-photo", args=[other.pk])
    assert signed_in.get(url).content == image_bytes("JPEG")
    Preference.objects.filter(user=other).delete()
    assert signed_in.get(url).status_code == 404
    # Owners can still read their own photos while completing preferences.
    signed_in.force_login(other)
    assert signed_in.get(url).content == image_bytes("JPEG")


def test_missing_profile_photo_returns_404(signed_in):
    response = signed_in.get(reverse("profile-photo", args=[uuid4()]))
    assert response.status_code == 404
    assert response.json() == {"error": "Profile photo not found."}


def test_upload_cannot_target_another_users_profile(signed_in, user, profile, details):
    other = User.objects.create_user("other-avatar@example.com", "Correct-Horse-42")
    other_profile = services.create_profile(other, **details, profile_picture=photo_upload())
    response = signed_in.post(reverse("my-profile"), {
        "user_id": str(other.pk), "display_name": "My new name", "bio": "My new bio",
        "profile_picture": photo_upload("JPEG"),
    })
    assert response.status_code == 302
    other_profile.refresh_from_db()
    assert other_profile.display_name == "Avery"
    assert other_profile.bio == "I like cooking."
    assert bytes(other_profile.profile_picture) == image_bytes()
    profile.refresh_from_db()
    assert profile.display_name == "My new name"
    assert bytes(profile.profile_picture) == image_bytes("JPEG")


@pytest.mark.parametrize("method", ["post", "patch", "delete"])
def test_read_photo_endpoint_cannot_modify_another_user(signed_in, details, method):
    other = User.objects.create_user("read-only-avatar@example.com", "Correct-Horse-42")
    profile = services.create_profile(other, **details, profile_picture=photo_upload())
    response = getattr(signed_in, method)(reverse("profile-photo", args=[other.pk]))
    assert response.status_code == 405
    profile.refresh_from_db()
    assert bytes(profile.profile_picture) == image_bytes()


def test_existing_profile_redirects_instead_of_overwriting_photo(signed_in, user, profile, details):
    for method in ("get", "post"):
        response = getattr(signed_in, method)(reverse("create-profile"), {
            **details, "profile_picture": photo_upload("JPEG"),
        })
        assert response.status_code == 302
        assert response.url == reverse("my-profile")
    profile.refresh_from_db()
    assert bytes(profile.profile_picture) == image_bytes()
    assert Profile.objects.filter(user=user).count() == 1


def test_delete_removes_profile_from_search_but_keeps_account_and_preferences(signed_in, user, profile):
    viewer = User.objects.create_user("search-viewer@example.com", "Correct-Horse-42")
    seeker = Client()
    seeker.force_login(viewer)
    search_url = reverse("roommate-list")
    detail_url = reverse("roommate-detail", args=[user.pk])
    photo_url = reverse("profile-photo", args=[user.pk])
    assert b"Avery" in seeker.get(search_url, {"name": "Avery"}).content
    assert seeker.get(detail_url).status_code == 200
    assert seeker.get(photo_url).status_code == 200
    before = Preference.objects.filter(user=user).values().get()
    assert signed_in.delete(reverse("profile-me")).status_code == 204
    assert not Profile.objects.filter(user=user).exists()
    assert User.objects.filter(pk=user.pk).exists()
    assert Preference.objects.filter(user=user).values().get() == before
    for filters in ({"name": "Avery"}, {"location": before["location_id"]}):
        results = seeker.get(search_url, filters)
        assert not results.context["roommates"].filter(user=user).exists()
        assert f'href="{detail_url}"'.encode() not in results.content
    assert seeker.get(detail_url).status_code == 404
    assert seeker.get(photo_url).status_code == 404
    assert signed_in.get(reverse("my-profile")).url == reverse("create-profile")
