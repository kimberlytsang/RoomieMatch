"""HTML views for discovering roommate profiles."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from . import services
from .models import BudgetRange, Location, PetsPreference, Preference, Profile


def _selected_filters(request):
    """Return validated GET filters and ignore malformed query parameters."""
    raw_location_id = request.GET.get("location", "")
    location_id = int(raw_location_id) if raw_location_id.isdigit() else None
    budget_range = request.GET.get("budget", "")
    pets_preference = request.GET.get("pets", "")
    name = request.GET.get("name", "")
    return {
        "location": location_id,
        "budget": budget_range if budget_range in BudgetRange.values else "",
        "pets": pets_preference if pets_preference in PetsPreference.values else "",
        "name": name,
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
        name=selected_filters["name"],
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
            "filters_active": any(
                (
                    selected_filters["location"],
                    selected_filters["budget"],
                    selected_filters["pets"],
                    selected_filters["name"].strip(),
                )
            ),
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


@login_required(login_url="login-page")
def my_profile(request):
    profile = Profile.objects.filter(user=request.user).first()
    if profile is None:
        return redirect("create-profile")
    preference = Preference.objects.filter(
        user=request.user
    ).select_related("location").first()

    return render(
        request,
        "profiles/my_profile.html",
        {"profile": profile, "preference": preference},
    )


@login_required(login_url="login-page")
@require_http_methods(["GET", "POST"])
def create_profile(request):
    if Profile.objects.filter(user=request.user).exists():
        return redirect("my-profile")

    values = {
        "display_name": "",
        "bio": "",
        "location_id": "",
        "budget_range": BudgetRange.B1001_1500,
        "pets_preference": "",
    }
    errors = {}
    if request.method == "POST":
        values = {field: request.POST.get(field, "") for field in values}
        try:
            services.create_profile(request.user, **values)
        except ValidationError as exc:
            errors = exc.message_dict
        except services.ProfileAlreadyExists:
            return redirect("my-profile")
        else:
            return redirect("my-profile")

    return render(
        request,
        "profiles/create_profile.html",
        {
            "values": values,
            "errors": errors,
            "locations": Location.objects.order_by("city", "state"),
            "budget_ranges": BudgetRange.choices,
            "pets_preferences": PetsPreference.choices,
        },
        status=400 if errors else 200,
    )
