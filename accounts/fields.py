from django.db import models


class CIEmailField(models.EmailField):
    """Email stored as PostgreSQL citext, so uniqueness ignores case.
    (Django 5 removed its built-in CIEmailField, so we define the column type here.)"""

    def db_type(self, connection):
        return "citext"
