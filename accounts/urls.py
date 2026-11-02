"""Routes for this component. Endpoints are added as each story is built.
Mounted under /api/ by config/urls.py."""
from django.urls import path

from . import views

urlpatterns = [
    path("auth/register", views.register, name="auth-register"),  # US-01
    path("auth/login", views.login_view, name="auth-login"),  # US-02
    path("auth/logout", views.logout_view, name="auth-logout"),  # US-03
    path("auth/password/change", views.change_password, name="auth-password-change"),
    path("auth/support", views.support_request, name="support-request"),
]
