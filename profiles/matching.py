"""Rule-based compatibility scoring for roommate preferences."""

from .models import (
    PartyPreference,
    PetsPreference,
    SleepPreference,
)


PREFERENCE_WEIGHTS = (
    ("location_id", 30, None),
    ("budget_range", 30, None),
    ("pets_preference", 15, PetsPreference.NO_PREFERENCE),
    ("sleep_preference", 15, SleepPreference.NO_PREFERENCE),
    ("party_preference", 10, PartyPreference.NO_PREFERENCE),
)


def compatibility_percentage(first, second):
    """Score equal preferences, excluding categories neutral for either user."""
    earned = 0
    applicable = 0

    for field, weight, neutral_value in PREFERENCE_WEIGHTS:
        first_value = getattr(first, field, None)
        second_value = getattr(second, field, None)
        if first_value is None or second_value is None:
            continue
        if neutral_value is not None and (
            first_value == neutral_value or second_value == neutral_value
        ):
            continue

        applicable += weight
        if first_value == second_value:
            earned += weight

    if applicable == 0:
        return None
    return round(earned / applicable * 100)
