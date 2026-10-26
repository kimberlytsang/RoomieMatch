"""HTML views for discovering roommate profiles."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from . import services
from .models import Profile


@login_required(login_url="login-page")
def roommate_list(request):
    """US-07: show every currently browseable roommate."""
    roommates = services.list_available_roommates(request.user)
    return render(request, "profiles/roommate_list.html", {"roommates": roommates})


@login_required(login_url="login-page")
def roommate_detail(request, user_id):
    """Open the selected roommate's shared profile summary."""
    try:
        roommate = services.get_available_roommate(request.user, user_id)
    except Profile.DoesNotExist:
        return render(request, "profiles/roommate_unavailable.html", status=404)
    return render(request, "profiles/roommate_detail.html", {"roommate": roommate})
