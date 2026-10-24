"""Setup checks: the project boots, reaches PostgreSQL, and has no pending model changes."""
import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_health_endpoint_reports_ok(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_no_pending_migrations():
    # Fails if someone changed a model without committing its migration.
    call_command("makemigrations", "--check", "--dry-run")
