# RoomieMatch

A roommate-discovery web app: students create a profile and housing preferences, search and filter other profiles, and message potential roommates.

CS-GY 6063, Section I2, Group "Software Engineering I I2 - 2". Instructor: Raz Saremi.

**Stack (from the Sprint 2 design):** Python, Django (HTML templates + JSON endpoints), PostgreSQL. Runs on localhost; AWS is optional.

## Current status

Track progress in [`docs/STORY_TRACKER.md`](docs/STORY_TRACKER.md).

## Run it locally

You need Python 3.12+, Git, and PostgreSQL 14+ installed on your computer (the default setup). Docker is an optional shortcut for the database only.

### One-time setup

**1. Get the code and install dependencies**

```bash
git clone <repository-url>
cd roomiematch
python -m venv .venv
```

Activate the virtual environment:

| Shell | Command |
|---|---|
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows cmd | `.venv\Scripts\activate.bat` |
| Git Bash / macOS / Linux | `source .venv/Scripts/activate` (Git Bash on Windows) or `source .venv/bin/activate` (macOS/Linux) |

If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.

```bash
pip install -r requirements.txt
```

**2. Create the database in PostgreSQL**

Open `psql` (SQL Shell from the Start menu, or `psql -U postgres`), sign in as the `postgres` user, and run:

```sql
CREATE USER roomiematch WITH SUPERUSER PASSWORD 'roomiematch';
CREATE DATABASE roomiematch OWNER roomiematch;
```

The user needs superuser rights because the first migration runs `CREATE EXTENSION citext`. If `roomiematch` already exists as a user, skip the first line.

*Prefer to use your own `postgres` user?* Run only `CREATE DATABASE roomiematch;` and set `DATABASE_URL` in `.env` (step 3) to `postgres://postgres:YOURPASSWORD@localhost:5432/roomiematch`.

**3. Configure environment variables**

```bash
cp .env.example .env               # Windows PowerShell: Copy-Item .env.example .env
```

The defaults in `.env.example` match the SQL in step 2, so no edits are needed in that case.

**4. Create the tables and load demo data**

```bash
python manage.py migrate
python manage.py seed_demo
```

`migrate` builds the tables from the models (`models.py` in each app folder) and is the only thing that creates the schema. `seed_demo` loads the locations and demo accounts, and is safe to run again.

### Every time you work on the project

1. Activate the virtual environment.
2. Make sure the PostgreSQL service is running (it normally starts with Windows).
3. Start the app:

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ . You should see the RoomieMatch home page with links to log in or create an account.

Run `python manage.py migrate` again only after pulling changes that add a migration file.

### Optional: PostgreSQL in Docker instead

If you would rather not install PostgreSQL, skip step 2 and run `docker compose up -d db`. It starts a PostgreSQL 16 container with the same database, user and password as above. Then continue from step 3.

## Inspect the database

To check what is stored (for example, that a registration landed), connect with `psql`:

```bash
psql -U roomiematch -d roomiematch -h localhost
```

The password is `roomiematch` (local development only). On Windows, if `psql` is not recognized, use the full path to the executable, for example `& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U roomiematch -d roomiematch -h localhost` (change `18` to your installed version).

At the `roomiematch=#` prompt:

```sql
SELECT user_id, email, role FROM users;   -- registered accounts
SELECT email, password_hash FROM users;   -- passwords are stored as hashes, never plain text
\dt                                       -- list all tables
\q                                        -- quit
```

Every SQL statement ends with a semicolon. Without psql, you can use Django instead: run `python manage.py shell`, then `from accounts.models import User` and `list(User.objects.values("email", "role"))`.

## Implemented endpoints

| Method | Endpoint | Story | Success | Errors |
|---|---|---|---|---|
| POST | `/api/auth/register` | US-01 | 201, `user_id`, session cookie | 400, 409, 422 |
| POST | `/api/auth/login` | US-02 | 200, `user_id`, session cookie | 400, 401 |
| POST | `/api/auth/logout` | US-03 | 204, no body | 401 |

Send JSON bodies with an `X-CSRFToken` header (state-changing requests without it get 403). Pages: `/` (shows who is signed in, with a Log out button), `/login/`, `/register/`.

## Run the tests

```bash
python -m pytest
```

Tests use their own temporary database, so your demo data is not touched. Each completed story adds tests under `tests/` (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Demo data

`python manage.py seed_demo` is safe to run repeatedly. It creates:

| Account | Role | Password |
|---|---|---|
| admin@roomiematch.test | App Administrator | DemoPass123! |
| alex@, sam@, jordan@, taylor@, casey@, riley@ `roomiematch.test` | Seeker (with profile and preferences) | DemoPass123! |

It also loads the list of locations (Manhattan, Brooklyn, Queens, The Bronx, Staten Island, Jersey City, Hoboken). These passwords are for local demos only.

## Project layout

The code follows the layered design from Sprint 2: URL routing, middleware, views, services, models.

| Folder | Component (Sprint 2) | Contains |
|---|---|---|
| `config/` | Routing and middleware settings | `settings.py`, `urls.py` |
| `accounts/` | Authentication | `User`, `Session` models; auth views/services (to come) |
| `profiles/` | Profile Management, Preferences, Search | `Profile`, `Preference`, `Location` models |
| `messaging/` | Messaging | `Conversation`, `Message` models |
| `support/` | Support | `SupportRequest` model |
| `templates/` | Frontend pages | `base.html` (includes the CSRF token for `fetch` calls) |
| `tests/` | Automated tests | Setup and schema checks so far |
| `docs/` | Sprint documents | Story tracker, design changes |

Each component has `urls.py` (routes), `views.py` (request handling and permissions), and `services.py` (business logic). Views call services, and only services and models touch the database.

## Configuration

Set in `.env` (see `.env.example`):

| Variable | Meaning |
|---|---|
| `DEBUG` | `True` for local development. When off, HTTPS redirect, secure cookies and HSTS turn on. |
| `SECRET_KEY` | Required when `DEBUG` is off. |
| `ALLOWED_HOSTS` | Comma-separated host names. |
| `DATABASE_URL` | PostgreSQL connection string. |

## Troubleshooting

- **`permission denied to create extension "citext"`**: the database user needs superuser rights (or ownership of a database where citext is allowed). Use the SQL in step 2 of the setup (or the Docker option).
- **`connection refused`**: PostgreSQL is not running or `DATABASE_URL` is wrong. Start the PostgreSQL service (or `docker compose up -d db` if you use Docker) and check the user, password and database name in `.env`.
- **`password authentication failed`**: the user or password in `DATABASE_URL` does not match PostgreSQL. Fix `.env` or reset the password in `psql`.
- **`database "roomiematch" does not exist`**: run step 2 of the setup.
- **`No module named 'django'`**: activate the virtual environment and run `pip install -r requirements.txt`.
