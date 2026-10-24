from django.db import connection
from django.http import JsonResponse


def health(request):
    """Deployment smoke check: confirms the app is up and can reach PostgreSQL."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})
