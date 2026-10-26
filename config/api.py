"""Small helpers shared by every component's JSON views (request parsing,
error responses, authentication check). Business rules do not belong here."""
import json
from functools import wraps

from django.http import JsonResponse


class BadRequest(Exception):
    """Raised when the request body is not a JSON object."""


def error(status, message):
    """Every error response has the same shape: {"error": "<message>"}."""
    return JsonResponse({"error": message}, status=status)


def json_body(request):
    """Parse the request body as a JSON object, or raise BadRequest."""
    try:
        data = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        raise BadRequest("Request body must be valid JSON.")
    if not isinstance(data, dict):
        raise BadRequest("Request body must be a JSON object.")
    return data


def authenticated_only(view):
    """Permission check for 'Authenticated' endpoints: 401 without a valid session."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return error(401, "Authentication required.")
        return view(request, *args, **kwargs)

    return wrapper
