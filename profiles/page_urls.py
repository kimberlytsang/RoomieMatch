"""Browser page routes owned by the profiles component."""

from django.urls import path

from . import page_views

urlpatterns = [
    path("create-profile/", page_views.create_profile, name="create-profile"),
    path("roommates/", page_views.roommate_list, name="roommate-list"),
    path("roommates/<uuid:user_id>/", page_views.roommate_detail, name="roommate-detail"),
    path("my-profile/", page_views.my_profile, name="my-profile"),
]
