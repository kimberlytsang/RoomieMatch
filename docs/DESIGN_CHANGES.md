# Design changes (Sprint 3, Section 6)

Where the code departs from the Sprint 2 design: one line naming what changed and why. Write "None" at submission if nothing differs. **Draft entries below came from project setup; confirm or delete each one.**

| # | Change | Why |
|---|---|---|
| 1 | The database has Django's framework tables (`django_migrations`, `django_content_type`, `auth_*`, `django_session`) in addition to the 8 tables in the ER diagram. | Django creates them for migrations, permissions, and sessions. They hold no RoomieMatch data. |
| 2 | `users.password_hash` is Django's `password` field stored in a column named `password_hash`; there is no `last_login` column. | Uses Django's password hashing and keeps the ER column names. |
| 3 | **Open decision:** the `sessions` table from the ER diagram exists but is unused. US-01 to US-03 use Django's built-in `django_session` store (30-minute idle timeout configured). | Still to decide before US-10: either write a custom session backend for `sessions`, or drop that table and update the ER diagram. |
| 4 | Email column uses a small custom `citext` field. | Django 5 removed its built-in case-insensitive email field; the column type is unchanged. |
| 5 | Added HTML pages `/`, `/login/` and `/register/` (not in the interface table). | The design calls for HTML templates; these call the JSON auth endpoints with `fetch`. |
| 6 | Error responses are JSON of the form `{"error": "<message>"}`. Registering with a malformed email returns 400. | The interface table lists status codes only; a malformed email counts as an invalid field. |
| 7 | "Weak password" (422) means Django's validators: at least 8 characters, not a common password, not all digits, at most 128 characters. | The interface table does not define "weak"; confirm or change the rule. |
