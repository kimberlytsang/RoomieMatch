"""Page views: render HTML templates. All data changes go through the JSON API."""
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
