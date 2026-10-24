"""Setup check: there are no pending model changes (every model change has a migration)."""
import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_no_pending_migrations():
    # Fails if someone changed a model without committing its migration.
    call_command("makemigrations", "--check", "--dry-run")
