"""JSON routes for the messaging component."""

from django.urls import path

from . import views


urlpatterns = [
    path("conversations/sidebar", views.conversation_sidebar, name="conversation-sidebar"),
    path("conversations/<uuid:conversation_id>/pin", views.pin_conversation, name="conversation-pin"),
    path("conversations/<uuid:conversation_id>/delete", views.remove_conversation, name="conversation-delete"),
    path("conversations/<uuid:conversation_id>/messages/<int:message_id>/remove", views.remove_message, name="message-remove"),
    path(
        "conversations/<uuid:conversation_id>/messages",
        views.conversation_messages,
        name="conversation-messages",
    ),
]
