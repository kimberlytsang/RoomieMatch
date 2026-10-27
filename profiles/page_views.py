"""HTML views for discovering roommate profiles."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from . import services
from .models import BudgetRange, Location, PetsPreference, Profile


def _selected_filters(request):
    """Return validated GET filters and ignore malformed query parameters."""
    raw_location_id = request.GET.get("location", "")
    location_id = int(raw_location_id) if raw_location_id.isdigit() else None
    budget_range = request.GET.get("budget", "")
    pets_preference = request.GET.get("pets", "")
    return {
        "location": location_id,
        "budget": budget_range if budget_range in BudgetRange.values else "",
        "pets": pets_preference if pets_preference in PetsPreference.values else "",
    }


@login_required(login_url="login-page")
def roommate_list(request):
    """US-07 / US-12: show browseable roommates and apply selected filters."""
    selected_filters = _selected_filters(request)
    roommates = services.list_available_roommates(
        request.user,
        location_id=selected_filters["location"],
        budget_range=selected_filters["budget"],
        pets_preference=selected_filters["pets"],
    )
    return render(
        request,
        "profiles/roommate_list.html",
        {
            "roommates": roommates,
            "locations": Location.objects.order_by("city", "state"),
            "budget_ranges": BudgetRange.choices,
            "pets_preferences": PetsPreference.choices,
            "selected_filters": selected_filters,
            "filters_active": any(selected_filters.values()),
        },
    )


@login_required(login_url="login-page")
def roommate_detail(request, user_id):
    """Open the selected roommate's shared profile summary."""
    try:
        roommate = services.get_available_roommate(request.user, user_id)
    except Profile.DoesNotExist:
        return render(request, "profiles/roommate_unavailable.html", status=404)
    return render(request, "profiles/roommate_detail.html", {"roommate": roommate})
