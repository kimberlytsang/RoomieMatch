"""View layer: parse the request, enforce permissions, call services, return JSON.
Business rules live in services.py, not here."""
from django.contrib.auth import login, logout, update_session_auth_hash
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods, require_POST

from config.api import BadRequest, authenticated_only, error, json_body

from . import services


def _credentials(request, *, list_missing_fields=False):
    """Return (email, password) from the JSON body, or an error response.

    Both fields must be non-empty strings (400 otherwise)."""
    try:
        data = json_body(request)
    except BadRequest as exc:
        return None, error(400, str(exc))
    email, password = data.get("email"), data.get("password")
    missing_fields = []
    if not isinstance(email, str) or not email.strip():
        missing_fields.append("Email")
    if not isinstance(password, str) or not password:
        missing_fields.append("Password")
    if missing_fields:
        if list_missing_fields:
            missing = " and ".join(missing_fields)
            return None, error(400, f"Please fill out the missing fields: {missing}.")
        return None, error(400, "Email or password not provided.")
    return (email, password), None


@require_POST
def register(request):
    """POST /api/auth/register (US-01). Public. 201, 400, 409, 422."""
    creds, problem = _credentials(request, list_missing_fields=True)
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


@require_POST
@authenticated_only
def change_password(request):
    """POST /api/auth/password/change. Authenticated. 200, 400, 401, 422."""
    try:
        data = json_body(request)
    except BadRequest as exc:
        return error(400, str(exc))

    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")
    if not all(isinstance(value, str) and value for value in (
        current_password, new_password, confirm_password
    )):
        return error(400, "Current password, new password, and confirmation are required.")
    if new_password != confirm_password:
        return error(400, "New password and confirmation password do not match.")

    try:
        services.change_password(request.user, current_password, new_password)
    except services.IncorrectCurrentPassword:
        return error(400, "Current password is incorrect.")
    except services.PasswordUnchanged:
        return error(400, "This is your current password. Please create a different one.")
    except services.WeakPassword as exc:
        return error(422, str(exc))

    update_session_auth_hash(request, request.user)
    return JsonResponse({"message": "Password updated successfully."})


@require_http_methods(["DELETE"])
@authenticated_only
def delete_account(request):
    """DELETE /api/users/me (US-14). Requires {"confirmation": true}; returns 204."""
    try:
        data = json_body(request)
    except BadRequest as exc:
        return error(400, str(exc))
    if data.get("confirmation") is not True:
        return error(400, "Account deletion confirmation is required.")

    services.delete_account(request.user)
    logout(request)
    return HttpResponse(status=204)
