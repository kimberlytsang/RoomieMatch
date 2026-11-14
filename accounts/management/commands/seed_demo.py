"""Load demo data for localhost demos and tests.  Safe to run repeatedly.

    python manage.py seed_demo

Creates the location list, one App Administrator, and a few Seekers with
preferences and profiles. These are demo accounts for LOCAL USE ONLY.
"""
from django.core.management.base import BaseCommand

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

DEMO_PASSWORD = "DemoPass123!"
ADMIN_EMAIL = "admin@roomiematch.test"

LOCATIONS = [
    ("Manhattan", "NY"),
    ("Brooklyn", "NY"),
    ("Queens", "NY"),
    ("The Bronx", "NY"),
    ("Staten Island", "NY"),
    ("Jersey City", "NJ"),
    ("Hoboken", "NJ"),
]

# (email, display name, bio, location, budget, pets, sleep, parties)
SEEKERS = [
    ("alex@roomiematch.test", "Alex", "I am a graduate student who likes baking and wants a clean, quiet home.", "Manhattan", BudgetRange.B1501_2000, PetsPreference.NO_PETS, SleepPreference.EARLY, PartyPreference.NO_PARTIES),
    ("sam@roomiematch.test", "Sam", "I study design and want a friendly home with space for my plants.", "Brooklyn", BudgetRange.B1001_1500, PetsPreference.PET_FRIENDLY, SleepPreference.LATE, PartyPreference.SOMETIMES),
    ("jordan@roomiematch.test", "Jordan", "I am starting a new job and enjoy cooking in a quiet home.", "Brooklyn", BudgetRange.B1501_2000, PetsPreference.NO_PREFERENCE, SleepPreference.EARLY, PartyPreference.NO_PARTIES),
    ("taylor@roomiematch.test", "Taylor", "I enjoy Sunday walks and would like to share meals with roommates sometimes.", "Manhattan", BudgetRange.B2001_2500, PetsPreference.NO_PETS, SleepPreference.VARIES, PartyPreference.OFTEN),
    ("casey@roomiematch.test", "Casey", "I have a cat and am looking for considerate roommates who enjoy a relaxed home.", "Queens", BudgetRange.B501_1000, PetsPreference.PET_FRIENDLY, SleepPreference.EARLY, PartyPreference.SOMETIMES),
    ("riley@roomiematch.test", "Riley", "I am flexible on location and value clear communication and a welcoming shared space.", "Jersey City", BudgetRange.B1001_1500, PetsPreference.NO_PREFERENCE, SleepPreference.VARIES, PartyPreference.NO_PREFERENCE),
]


class Command(BaseCommand):
    help = "Seed locations, one admin, and demo seekers (idempotent)."

    def handle(self, *args, **options):
        locations = {}
        for city, state in LOCATIONS:
            locations[city], _ = Location.objects.get_or_create(city=city, state=state)

        if not User.objects.filter(email=ADMIN_EMAIL).exists():
            User.objects.create_admin(ADMIN_EMAIL, DEMO_PASSWORD)

        for email, name, bio, city, budget, pets, sleep, parties in SEEKERS:
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(email, DEMO_PASSWORD)
            Preference.objects.update_or_create(
                user=user,
                defaults={
                    "location": locations[city],
                    "budget_range": budget,
                    "pets_preference": pets,
                    "sleep_preference": sleep,
                    "party_preference": parties,
                },
            )
            Profile.objects.update_or_create(
                user=user,
                defaults={"display_name": name, "bio": bio},
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(LOCATIONS)} locations, 1 admin ({ADMIN_EMAIL}), "
            f"{len(SEEKERS)} seekers. Demo password: {DEMO_PASSWORD}"
        ))
