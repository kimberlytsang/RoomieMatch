"""Business rules and database queries for roommate discovery."""

from .models import Profile


def list_available_roommates(viewer):
    """Return profiles a signed-in seeker can browse.

    A seeker never appears in their own results, and profiles without the
    preference information shown on a roommate card are not browseable yet.
    """
    return (
        Profile.objects.select_related("user__preference__location")
        .filter(user__preference__isnull=False)
        .exclude(user=viewer)
        .order_by("display_name")
    )


def get_available_roommate(viewer, user_id):
    """Return one browseable roommate, or raise Profile.DoesNotExist.

    Keeping this lookup here ensures a URL cannot expose the signed-in
    seeker's own profile or a profile that is no longer available.
    """
    return list_available_roommates(viewer).get(user_id=user_id)
