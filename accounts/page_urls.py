"""HTML page routes for accounts (the pages call the JSON API with fetch)."""
from django.urls import path

from . import page_views

urlpatterns = [
    path("", page_views.home, name="home"),
    path("register/", page_views.register_page, name="register-page"),
    path("login/", page_views.login_page, name="login-page"),
]
