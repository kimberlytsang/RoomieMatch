"""JSON routes for the messaging component."""

from django.urls import path

from . import views


urlpatterns = [
    path("conversations/sidebar", views.conversation_sidebar, name="conversation-sidebar"),
    path(
        "conversations/<uuid:conversation_id>/messages",
        views.conversation_messages,
        name="conversation-messages",
    ),
]
