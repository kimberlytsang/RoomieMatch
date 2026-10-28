"""Page views: render HTML templates. All data changes go through the JSON API."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


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
