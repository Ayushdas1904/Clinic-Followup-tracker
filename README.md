# Clinic Follow-up Tracker (Lite)

Backend-focused Django app to manage clinic-scoped patient follow-ups.
Staff users (login required) can create and track follow-ups, and share a public token link with patients.
Every public page visit is logged.

## Tech

- Python 3.10+
- Django 5.x
- MySQL (recommended for local per SRS) or SQLite (default if MySQL env vars are not set)
- No DRF, no Celery

## Setup

### 1) Create a virtualenv + install deps

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure MySQL (recommended)

Create a MySQL database (example: `cftlite`). Then set env vars:

```bash
export MYSQL_DATABASE=cftlite
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306

# optional
export DJANGO_SECRET_KEY='change-me'
export DJANGO_DEBUG=1
export DJANGO_ALLOWED_HOSTS='127.0.0.1,localhost'
```

If `MYSQL_DATABASE` is not set, the app will use SQLite (`db.sqlite3`).

### 3) Run migrations

```bash
python manage.py migrate
```

### 4) Create a superuser

```bash
python manage.py createsuperuser
```

### 5) Create Clinic + UserProfile

This app enforces clinic-level data isolation.
Each staff user must have a `UserProfile` pointing to exactly one `Clinic`.

Quick way (admin):

1. Start server: `python manage.py runserver`
2. Open admin: `http://127.0.0.1:8000/admin/`
3. Create a `Clinic`
4. Create a `UserProfile` for each user, linking them to a clinic

> Note: If a user does not have a `UserProfile`, dashboard pages will return 404.

## Run the app

```bash
python manage.py runserver
```

- Admin: `http://127.0.0.1:8000/admin/`
- Login: `http://127.0.0.1:8000/accounts/login/`
- Dashboard: `http://127.0.0.1:8000/`

## Public follow-up link

Public pages do not require login:

- URL format: `/p/<public_token>/`
- Each visit creates a `PublicViewLog` entry.

## Dashboard pagination

The dashboard is paginated (25 rows per page).

- Use `?page=N` to navigate pages
- Existing filters (`status`, `due_start`, `due_end`) are preserved when paging

## CSV import (management command)

Command:

```bash
python manage.py import_followups --csv sample.csv --username <username>
```

Rules:

- Required columns: `patient_name, phone, language, due_date`
- Optional columns: `notes, status`
- `language` must be `en` or `hi`
- `status` must be `pending` or `done`
- Invalid rows are skipped; processing continues

A sample file is included: [sample.csv](sample.csv)

## Export follow-ups to CSV (stretch)

Export the current clinic's follow-ups as a CSV download:

- URL: `/followups/export/`
- Supports the same filters as the dashboard:
	- `status=pending|done`
	- `due_start=YYYY-MM-DD`
	- `due_end=YYYY-MM-DD`

Example:

```bash
open "http://127.0.0.1:8000/followups/export/?status=pending&due_start=2026-01-01&due_end=2026-12-31"
```

## Tests

```bash
python manage.py test
```

Covers the required minimum 5 tests:

- Unique `clinic_code` generation
- Unique `public_token` generation
- Dashboard requires login
- Cross-clinic access is blocked
- Public page creates a `PublicViewLog`

## Submission checklist

- Repo contains the full code (push to GitHub/GitLab).
- README includes:
  - setup steps
  - creating a superuser
  - creating `Clinic` + `UserProfile`
  - running tests
  - running CSV import
- Proof of functionality:
  - either a 2–4 minute screen recording, OR
  - 4 screenshots (dashboard, create/edit, public page, view log)

## Proof of functionality (4 screenshots)

Suggested screenshots to match the rubric:

1) Dashboard
	- URL: `http://127.0.0.1:8000/`
	- Show: follow-up list, view counts, filters, and/or overdue badge

2) Create/Edit form
	- URL: `http://127.0.0.1:8000/followups/new/` (or edit any row)
	- Show: the form fields and validation UI

3) Public page
	- From the dashboard, open any public link like `/p/<token>/`
	- Show: language-based instructions + due date (and notes if present)

4) View log
	- Open admin: `http://127.0.0.1:8000/admin/`
	- Go to: Tracker → Public view logs
	- Show: a log entry created by visiting the public page

Tip: To guarantee there is at least one view log before taking screenshot #4, open the public link once in a private/incognito window and refresh it.
