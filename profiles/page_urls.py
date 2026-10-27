"""Browser page routes owned by the profiles component."""

from django.urls import path

from . import page_views

urlpatterns = [
    path("roommates/", page_views.roommate_list, name="roommate-list"),
    path("roommates/<uuid:user_id>/", page_views.roommate_detail, name="roommate-detail"),
]
