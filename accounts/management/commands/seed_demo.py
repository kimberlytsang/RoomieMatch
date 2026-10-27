"""Load demo data for localhost demos and tests.  Safe to run repeatedly.

    python manage.py seed_demo

Creates the location list, one App Administrator, and a few Seekers with
preferences and profiles. These are demo accounts for LOCAL USE ONLY.
"""
from django.core.management.base import BaseCommand

from accounts.models import User
from profiles.models import BudgetRange, Location, PetsPreference, Preference, Profile

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

# (email, display name, bio, location, budget, pets)
SEEKERS = [
    ("alex@roomiematch.test", "Alex", "Grad student, early riser.", "Manhattan", BudgetRange.B1501_2000, PetsPreference.NO_PETS),
    ("sam@roomiematch.test", "Sam", "Works nights, very tidy.", "Brooklyn", BudgetRange.B1001_1500, PetsPreference.PET_FRIENDLY),
    ("jordan@roomiematch.test", "Jordan", "Quiet, likes to cook.", "Brooklyn", BudgetRange.B1501_2000, PetsPreference.NO_PREFERENCE),
    ("taylor@roomiematch.test", "Taylor", "Undergrad looking near campus.", "Manhattan", BudgetRange.B2001_2500, PetsPreference.NO_PETS),
    ("casey@roomiematch.test", "Casey", "Has a cat.", "Queens", BudgetRange.B501_1000, PetsPreference.PET_FRIENDLY),
    ("riley@roomiematch.test", "Riley", "Flexible on location.", "Jersey City", BudgetRange.B1001_1500, PetsPreference.NO_PREFERENCE),
]


class Command(BaseCommand):
    help = "Seed locations, one admin, and demo seekers (idempotent)."

    def handle(self, *args, **options):
        locations = {}
        for city, state in LOCATIONS:
            locations[city], _ = Location.objects.get_or_create(city=city, state=state)

        if not User.objects.filter(email=ADMIN_EMAIL).exists():
            User.objects.create_admin(ADMIN_EMAIL, DEMO_PASSWORD)

        for email, name, bio, city, budget, pets in SEEKERS:
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(email, DEMO_PASSWORD)
            Preference.objects.update_or_create(
                user=user,
                defaults={"location": locations[city], "budget_range": budget, "pets_preference": pets},
            )
            Profile.objects.get_or_create(user=user, defaults={"display_name": name, "bio": bio})

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(LOCATIONS)} locations, 1 admin ({ADMIN_EMAIL}), "
            f"{len(SEEKERS)} seekers. Demo password: {DEMO_PASSWORD}"
        ))
