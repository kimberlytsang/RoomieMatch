"""Browser page routes owned by the messaging component."""

from django.urls import path

from . import page_views

urlpatterns = [
    path("roommates/<uuid:user_id>/message/", page_views.send_message_page, name="send-message"),
    path("conversations/", page_views.conversation_list, name="conversation-list"),
    path(
        "conversations/<uuid:conversation_id>/",
        page_views.conversation_detail,
        name="conversation-detail",
    ),
]
