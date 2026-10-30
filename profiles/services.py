"""Business rules and database queries for roommate discovery."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import BudgetRange, Location, PetsPreference, Preference, Profile


def list_available_roommates(
    viewer, *, location_id=None, budget_range=None, pets_preference=None
):
    """Return profiles a signed-in seeker can browse.

    A seeker never appears in their own results, and profiles without the
    preference information shown on a roommate card are not browseable yet.
    """
    roommates = (
        Profile.objects.select_related("user__preference__location")
        .filter(user__preference__isnull=False)
        .exclude(user=viewer)
    )
    if location_id is not None:
        roommates = roommates.filter(user__preference__location_id=location_id)
    if budget_range in BudgetRange.values:
        roommates = roommates.filter(user__preference__budget_range=budget_range)
    if pets_preference in PetsPreference.values:
        roommates = roommates.filter(user__preference__pets_preference=pets_preference)
    return roommates.order_by("display_name")


def get_available_roommate(viewer, user_id):
    """Return one browseable roommate, or raise Profile.DoesNotExist.

    Keeping this lookup here ensures a URL cannot expose the signed-in
    seeker's own profile or a profile that is no longer available.
    """
    return list_available_roommates(viewer).get(user_id=user_id)


class ProfileAlreadyExists(Exception):
    pass


def create_profile(user, *, display_name, bio, location_id, budget_range, pets_preference):
    """US-15: validate and create a profile and its preferences together."""
    display_name = display_name.strip()
    bio = bio.strip()
    errors = {}
    if not display_name:
        errors["display_name"] = "Enter your name."
    elif "\x00" in display_name:
        errors["display_name"] = "Name cannot contain null characters."
    elif len(display_name) > 50:
        errors["display_name"] = "Name must be at most 50 characters."
    if "\x00" in bio:
        errors["bio"] = "About me cannot contain null characters."
    elif len(bio) > 500:
        errors["bio"] = "About me must be at most 500 characters."
    try:
        location_id = int(location_id)
    except (TypeError, ValueError):
        location_id = 0
    location = (
        Location.objects.filter(pk=location_id).first()
        if 0 < location_id <= 2147483647 else None
    )
    if location is None:
        errors["location_id"] = "Choose a valid location."
    if budget_range not in BudgetRange.values:
        errors["budget_range"] = "Choose a valid monthly budget."
    if pets_preference not in PetsPreference.values:
        errors["pets_preference"] = "Choose a pet preference."
    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        # Lock the owner so repeated submissions cannot create two profiles.
        get_user_model().objects.select_for_update().get(pk=user.pk)
        if Profile.objects.filter(user=user).exists():
            raise ProfileAlreadyExists
        Preference.objects.update_or_create(
            user=user,
            defaults={
                "location": location,
                "budget_range": budget_range,
                "pets_preference": pets_preference,
            },
        )
        return Profile.objects.create(user=user, display_name=display_name, bio=bio)


def _clean_profile_text(values):
    """Validate the supplied name and bio fields for updates."""
    cleaned = {}
    errors = {}

    for field, label, max_length in (
        ("display_name", "Name", 50),
        ("bio", "About me", 500),
    ):
        if field not in values:
            continue

        value = values[field]
        if not isinstance(value, str):
            errors[field] = f"{label} must be text."
            continue

        value = value.strip()
        if field == "display_name" and not value:
            errors[field] = "Enter your name."
        elif "\x00" in value:
            errors[field] = f"{label} cannot contain null characters."
        elif len(value) > max_length:
            errors[field] = f"{label} must be at most {max_length} characters."
        else:
            cleaned[field] = value

    if errors:
        raise ValidationError(errors)

    return cleaned


def get_profile(user):
    """Get the current user's profile."""
    return Profile.objects.get(user=user)


def update_profile(user, changes):
    """Update only the supplied name and bio fields."""
    if not isinstance(changes, dict):
        raise ValidationError("Profile changes must be an object.")

    allowed_fields = {"display_name", "bio"}
    if set(changes) - allowed_fields:
        raise ValidationError("Only name and about me can be updated.")
    if not changes:
        raise ValidationError("Provide a name or about me to update.")

    cleaned = _clean_profile_text(changes)

    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        profile = get_profile(user)

        for field, value in cleaned.items():
            setattr(profile, field, value)

        profile.save(update_fields=list(cleaned))
        return profile


def delete_profile(user):
    """Delete the profile while keeping the account and preferences."""
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        profile = get_profile(user)
        profile.delete()
