"""URL routing layer. Each component owns its routes in <app>/urls.py."""
from django.urls import include, path

urlpatterns = [
    path("", include("accounts.page_urls")),
    path("", include("profiles.page_urls")),
    path("api/", include("accounts.urls")),
    path("api/", include("profiles.urls")),
    path("api/", include("messaging.urls")),
    path("api/", include("support.urls")),
]
