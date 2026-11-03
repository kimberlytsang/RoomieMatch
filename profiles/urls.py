"""JSON API routes for the profiles component."""
from django.urls import path

from . import views

urlpatterns = [
    path("profiles/me", views.profile_me, name="profile-me"),
]
