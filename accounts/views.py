"""View layer: parse the request, enforce permissions, call services, return JSON.
Business rules live in services.py, not here."""
from django.contrib.auth import login, logout
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from config.api import BadRequest, authenticated_only, error, json_body

from . import services


def _credentials(request):
    """Return (email, password) from the JSON body, or an error response.

    Both fields must be non-empty strings (400 otherwise)."""
    try:
        data = json_body(request)
    except BadRequest as exc:
        return None, error(400, str(exc))
    email, password = data.get("email"), data.get("password")
    if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password:
        return None, error(400, "Email and password are required.")
    return (email, password), None


@require_POST
def register(request):
    """POST /api/auth/register (US-01). Public. 201, 400, 409, 422."""
    creds, problem = _credentials(request)
    if problem:
        return problem
    email, password = creds
    try:
        user = services.register_user(email, password)
    except services.InvalidEmail as exc:
        return error(400, str(exc))
    except services.DuplicateEmail as exc:
        return error(409, str(exc))
    except services.WeakPassword as exc:
        return error(422, str(exc))
    login(request, user)  # starts the session and sets the session cookie
    return JsonResponse({"user_id": str(user.user_id)}, status=201)


@require_POST
def login_view(request):
    """POST /api/auth/login (US-02). Public. 200, 400, 401."""
    creds, problem = _credentials(request)
    if problem:
        return problem
    email, password = creds
    user = services.authenticate_user(request, email, password)
    if user is None:
        return error(401, "Invalid email or password.")
    login(request, user)  # new session key each login; sets the session cookie
    return JsonResponse({"user_id": str(user.user_id)})


@require_POST
@authenticated_only
def logout_view(request):
    """POST /api/auth/logout (US-03). Authenticated. 204 with no body, 401."""
    logout(request)  # deletes the server-side session and clears the cookie
    return HttpResponse(status=204)
