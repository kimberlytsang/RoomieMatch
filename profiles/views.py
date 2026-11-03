"""View layer: parse the request, enforce permissions, call services, return JSON.
Business rules live in services.py, not here."""
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from config.api import BadRequest, authenticated_only, error, json_body

from . import services
from .models import Profile


@require_http_methods(["GET", "POST", "PATCH", "DELETE"])
@authenticated_only
def profile_me(request):
    """Manage the signed-in user's profile. Photo uploads are not supported yet."""
    try:
        if request.method == "GET":
            profile = services.get_profile(request.user)
        elif request.method == "POST":
            data = json_body(request)
            fields = {"display_name", "bio", "location_id", "budget_range", "pets_preference"}
            if set(data) - fields:
                return error(400, "Unsupported profile fields.")
            values = {field: data.get(field, "") for field in fields}
            for field in ("display_name", "bio", "budget_range", "pets_preference"):
                if not isinstance(values[field], str):
                    return error(400, f"{field} must be text.")
            location_id = values["location_id"]
            if isinstance(location_id, bool) or not isinstance(location_id, (str, int)):
                return error(400, "location_id must be an integer or a string.")
            profile = services.create_profile(request.user, **values)
        elif request.method == "PATCH":
            profile = services.update_profile(request.user, json_body(request))
        else:
            services.delete_profile(request.user)
            return HttpResponse(status=204)
    except BadRequest as exc:
        return error(400, str(exc))
    except ValidationError as exc:
        return error(400, " ".join(exc.messages))
    except services.ProfileAlreadyExists:
        return error(409, "A profile already exists for this account.")
    except Profile.DoesNotExist:
        return error(404, "Profile not found.")

    return JsonResponse(
        {
            "user_id": str(profile.user_id),
            "display_name": profile.display_name,
            "bio": profile.bio,
        },
        status=201 if request.method == "POST" else 200,
    )
