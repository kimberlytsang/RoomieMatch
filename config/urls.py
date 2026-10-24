"""URL routing layer. Each component owns its routes in <app>/urls.py."""
from django.urls import include, path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("api/", include("accounts.urls")),
    path("api/", include("profiles.urls")),
    path("api/", include("messaging.urls")),
    path("api/", include("support.urls")),
]
