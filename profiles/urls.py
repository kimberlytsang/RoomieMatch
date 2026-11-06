"""JSON API routes for the profiles component."""
from django.urls import path

from . import views

urlpatterns = [
    path("profiles/me", views.profile_me, name="profile-me"),
    path("profiles/<uuid:user_id>/photo", views.profile_photo, name="profile-photo"),
]
