# Design changes (Sprint 3, Section 6)

Where the code departs from the Sprint 2 design: one line naming what changed and why. Write "None" at submission if nothing differs. **Draft entries below came from project setup; confirm or delete each one.**

| # | Change | Why |
|---|---|---|
| 1 | The database has Django's framework tables (`django_migrations`, `django_content_type`, `auth_*`, `django_session`) in addition to the 8 tables in the ER diagram. | Django creates them for migrations, permissions, and sessions. They hold no RoomieMatch data. |
| 2 | `users.password_hash` is Django's `password` field stored in a column named `password_hash`; there is no `last_login` column. | Uses Django's password hashing and keeps the ER column names. |
| 3 | **Open decision:** the `sessions` table from the ER diagram exists but is unused. Login will use Django's built-in `django_session` store (30-minute idle timeout configured). | Decide when building US-02 / US-10: either write a custom session backend for `sessions`, or drop that table and update the ER diagram. |
| 4 | Email column uses a small custom `citext` field. | Django 5 removed its built-in case-insensitive email field; the column type is unchanged. |
| 5 | Added an HTML home page at `/` (not in the interface table). | The design calls for HTML templates; this is the public landing page. |
