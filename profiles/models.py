from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Length, Trim


class BudgetRange(models.TextChoices):
    UNDER_1500 = "UNDER_1500", "Under $1,500"
    B1501_2000 = "B1501_2000", "$1,501-$2,000"
    B2001_2500 = "B2001_2500", "$2,001-$2,500"
    B2501_3000 = "B2501_3000", "$2,501-$3,000"
    B3001_3500 = "B3001_3500", "$3,001-$3,500"
    B3501_4000 = "B3501_4000", "$3,501-$4,000"
    OVER_4000 = "OVER_4000", "$4,001+"


class PetsPreference(models.TextChoices):
    PET_FRIENDLY = "PET_FRIENDLY", "Pet friendly"
    NO_PETS = "NO_PETS", "No pets"
    NO_PREFERENCE = "NO_PREFERENCE", "No preference"


class Location(models.Model):
    location_id = models.AutoField(primary_key=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)

    class Meta:
        db_table = "locations"
        constraints = [
            models.UniqueConstraint(fields=["city", "state"], name="uniq_location_city_state"),
        ]

    def __str__(self):
        return f"{self.city}, {self.state}"


class Preference(models.Model):
    """One preferences record per user: user_id is both primary key and foreign key."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="preference",
    )
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="preferences")
    budget_range = models.CharField(max_length=20, choices=BudgetRange.choices)
    pets_preference = models.CharField(max_length=20, choices=PetsPreference.choices)

    class Meta:
        db_table = "preferences"
        indexes = [models.Index(fields=["location", "budget_range", "pets_preference"])]


class Profile(models.Model):
    """One profile per user: user_id is both primary key and foreign key."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=50)
    profile_picture = models.BinaryField(null=True, blank=True)  # JPEG/PNG bytes, 2 MB max (enforced in service)
    bio = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "profiles"
        constraints = [
            models.CheckConstraint(
                condition=Q(display_name__regex=r"\S"),
                name="profile_display_name_not_blank",
            ),
        ]
