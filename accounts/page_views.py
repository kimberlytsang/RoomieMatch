"""Page views: render HTML templates. All data changes go through the JSON API."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from . import services
from .models import SupportRequestStatus

def home(request):
    return render(request, "home.html")


def register_page(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "register.html")


def login_page(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "login.html")


@login_required(login_url="login-page")
def account_settings(request):
    return render(request, "account_settings.html")


@login_required(login_url="login-page")
def app_admin(request):
    if not request.user.is_admin:
        return redirect("home")
    support_requests = list(services.get_support_requests())
    for support_request in support_requests:
        support_request.contact_user = services.get_user_by_email(support_request.user)
    return render(
        request,
        "app_admin.html",
        {
            "support_requests": support_requests,
            "status_choices": SupportRequestStatus.choices,
        },
    )
