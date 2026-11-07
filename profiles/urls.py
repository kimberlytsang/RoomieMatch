"""JSON API routes for the profiles component."""
from django.urls import path

from . import views

urlpatterns = [
    path("preferences/me", views.preferences_me, name="preferences-me"),
    path("locations", views.locations, name="locations"),
    path("profiles/me", views.profile_me, name="profile-me"),
]
