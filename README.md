# Bright Path Scheduling

A small scheduling API built for the Bright Path Learning Centre engineering assessment.

The goal of this project is intentionally narrow:

> Prevent invalid lesson bookings before they are added to the schedule.

The API checks the proposed booking against the existing schedule and either:

- creates the lesson, or
- rejects it with a clear scheduling conflict.

---

## What this project checks

When a new lesson is created, the API checks:

- whether the tutor is already busy
- whether the room is already busy
- whether the student is already in another lesson
- whether the tutor already has six non-cancelled bookings that day
- whether the centre is open that day
- whether the lesson duration is 60 or 90 minutes

Cancelled lessons do not block a tutor, room, or student. `no_show` bookings still block their slots and count toward the daily limit. “Availability” here means no conflicting bookings; tutor working hours are not modelled.

The existing CSV data is treated as historical seed data. It is not corrected or rewritten, even when it contains situations that do not match the stated business rules.

---

# Quick start

If you only want to run the project, follow these steps in order.

You need:

- Git
- Python 3.10 or newer
- an internet connection for installing Python packages

You do **not** need:

- PostgreSQL
- MySQL
- Docker
- Node.js
- any external database server

The project uses SQLite, which stores the database in a local file and does not require a separate database server.

---

# 1. Clone the repository

Open a terminal.

Clone the repository:

```bash
git clone https://github.com/OscarMuRu99/bright-path-scheduling.git
```

Then enter the project folder:

```bash
cd bright-path-scheduling
```

---

# 2. Check your Python version

Run:

```bash
python --version
```

If that does not work on macOS or Linux, try:

```bash
python3 --version
```

You should see Python 3.10 or newer.

Example:

```text
Python 3.13.4
```

---

# 3. Create a virtual environment

A virtual environment keeps this project's Python packages separate from the rest of your computer.

## macOS / Linux

Run:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Your terminal should now start with something similar to:

```text
(.venv)
```

## Windows PowerShell

Run:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt below. You can also skip activation and use `.\.venv\Scripts\python.exe` instead of `python` in the remaining commands.

## Windows Command Prompt

Run:

```cmd
python -m venv .venv
```

Activate it:

```cmd
.venv\Scripts\activate.bat
```

---

# 4. Install the dependencies

With the virtual environment active, run:

```bash
python -m pip install -r requirements.txt
```

Wait until the installation finishes.

---

# 5. Start the API

Run:

```bash
python -m uvicorn app.main:app --reload
```

You should see output similar to:

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

The application automatically creates and seeds its local SQLite database from:

```text
data/tutors.csv
data/lessons_export.csv
```

You do not need to create the database manually.

To stop the server later, press:

```text
Ctrl + C
```

---

# 6. Open the API in your browser

With the server still running, open:

```text
http://127.0.0.1:8000/docs
```

This opens FastAPI's interactive Swagger documentation.

From there, the API can be tested without Postman or any additional software.

You can also check:

```text
http://127.0.0.1:8000/health
```

Expected result:

```json
{
  "status": "ok"
}
```

---

# Try the booking endpoint

In:

```text
http://127.0.0.1:8000/docs
```

Dates must be real calendar dates in `YYYY-MM-DD` format; times must use local 24-hour `HH:MM`, without a timezone suffix. Invalid values return `422`.

Find:

```text
POST /bookings
```

Click:

1. `POST /bookings`
2. `Try it out`
3. Replace the example request with one of the examples below
4. Click `Execute`

---

## Example 1: valid booking

Use:

```json
{
  "lesson_id": "TEST001",
  "date": "2026-03-07",
  "start_time": "13:00",
  "duration_min": 60,
  "student": "Test Student",
  "tutor_id": "T2",
  "room": "R1"
}
```

Expected response:

```text
201 Created
```

The lesson is added to the schedule. Use a new `lesson_id` for each new lesson. Reusing an existing ID returns `409 LESSON_ID_EXISTS`; it does not update that lesson.

---

## Example 2: tutor conflict

Use:

```json
{
  "lesson_id": "TEST002",
  "date": "2026-03-10",
  "start_time": "09:30",
  "duration_min": 60,
  "student": "Another Student",
  "tutor_id": "T1",
  "room": "R3"
}
```

T1 already has a lesson that overlaps this time.

Expected response:

```text
409 Conflict
```

Example response body:

```json
{
  "detail": {
    "code": "TUTOR_CONFLICT",
    "message": "Tutor T1 is already booked during this time."
  }
}
```

---

## Example 3: centre closed

Use:

```json
{
  "lesson_id": "TEST003",
  "date": "2026-03-09",
  "start_time": "13:00",
  "duration_min": 60,
  "student": "Test Student",
  "tutor_id": "T2",
  "room": "R1"
}
```

March 9, 2026 is a Monday.

Expected response:

```text
409 Conflict
```

with:

```text
CENTRE_CLOSED
```

---

# Run the automated tests

Stop the API first with:

```text
Ctrl + C
```

Then run:

```bash
python -m pytest -v
```

Expected result:

```text
24 passed
```

The test suite covers:

- valid booking creation
- tutor conflicts
- room conflicts
- student conflicts
- Monday bookings
- the six-booking tutor daily limit
- invalid date/time input and duplicate IDs through the HTTP API
- cancelled and no-show bookings
- back-to-back lessons, 90-minute lessons and overlaps across midnight
- seed idempotency and paths independent of the working directory

The tests use a temporary SQLite database, so they do not depend on the database created when manually running the application.

---

# Verified locally

On macOS with Python 3.13.4, in a newly created virtual environment:

| Command | Observed result |
|---|---|
| `python -m pip install -r requirements.txt` | Installation completed |
| `python -m pip check` | No broken requirements found |
| `python -m pytest -v` | 24 passed |
| `python -m app.database` (run twice) | 3 tutors and 34 lessons, no duplicated seed rows |

The HTTP tests also verified `/health`, `/docs`, booking persistence, and the three examples above: `201`, `409 TUTOR_CONFLICT`, and `409 CENTRE_CLOSED`.

Windows and Linux instructions have been reviewed but have not been executed on those systems. The direct dependencies are pinned to the versions tested; their transitive dependencies are resolved by pip. `httpx` is used by the HTTP tests, and `pydantic` is declared explicitly because the app imports it.

The suite currently emits dependency/startup deprecation warnings. They do not fail the tests; updating the startup hook and test transport is deferred to keep this submission focused.

---

# Project structure

```text
bright-path-scheduling/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   └── booking_service.py
│
├── data/
│   ├── lessons_export.csv
│   └── tutors.csv
│
├── tests/
│   ├── test_bookings.py
│   └── test_booking_regressions.py
│
├── DECISIONS.md
├── README.md
├── requirements.txt
├── pytest.ini
└── .gitignore
```

## What each file does

### `app/main.py`

Defines the HTTP API.

It exposes:

```text
GET /health
POST /bookings
```

It also initializes the seed database when the application starts.

### `app/models.py`

Defines the request and response models used by the API.

### `app/database.py`

Handles:

- the SQLite connection
- database tables
- loading tutors from CSV
- loading lessons from CSV

The seed operation is idempotent: tutor and lesson IDs are primary keys, and seed inserts use `INSERT OR IGNORE`, so running it again does not duplicate the provided records. It does not reset existing records or remove bookings created through the API.

### `app/booking_service.py`

Contains the scheduling business rules.

This is where the application checks:

- tutor conflicts
- room conflicts
- student conflicts
- tutor daily booking limits
- opening days
- lesson duration

### `data/`

Contains the provided assessment data.

These files are loaded into SQLite as seed data.

### `tests/test_bookings.py`

Contains the automated tests for the scheduling rules.

### `DECISIONS.md`

Documents:

- questions I would ask the client
- unclear or contradictory requirements
- assumptions
- scope decisions
- design decisions
- trade-offs
- AI usage
- what I would build next

---

# How a booking moves through the application

The flow is intentionally small:

```text
             POST /bookings
                    |
                    v
             FastAPI endpoint
                main.py
                    |
                    v
             BookingCreate
                models.py
                    |
                    v
        Scheduling validation
          booking_service.py
                    |
             +------+------+
             |             |
          valid          conflict
             |             |
             v             v
          SQLite       409 response
             |
             v
        201 Created
```

The important idea is:

> Before inserting a booking, check whether that booking would make the schedule invalid.

---

# Database

The project uses SQLite.

The local database file is:

```text
bright_path.db
```

It is generated automatically and is intentionally excluded from Git.

To manually initialize or seed the database, you can run:

```bash
python -m app.database
```

The seed operation uses the CSV files in the `data/` directory.

---

# Why SQLite?

SQLite was chosen because this assessment is small and time-boxed.

It allows the reviewer to run the project without configuring:

- database credentials
- a database server
- Docker
- networking
- external infrastructure

For the scope of this exercise, the database is only responsible for persistence and basic integrity.

Scheduling rules remain explicit in the application layer.

---

# HTTP responses

The main responses are:

| Status | Meaning |
|---|---|
| `201 Created` | The booking was valid and was created |
| `409 Conflict` | The request is valid, but violates a scheduling rule |
| `422 Unprocessable Entity` | The request itself does not match the expected API structure |

Possible scheduling conflict codes include:

```text
TUTOR_CONFLICT
ROOM_CONFLICT
STUDENT_CONFLICT
TUTOR_DAILY_LIMIT
CENTRE_CLOSED
INVALID_DURATION
UNKNOWN_TUTOR
LESSON_ID_EXISTS
```

---

# Scope

This implementation intentionally focuses on one feature:

> Preventing invalid new bookings.

I did not implement:

- WhatsApp notifications
- billing
- cancellation charges
- automatic rescheduling
- paired-lesson pricing
- a user interface
- complete booking-change history

Those are useful features, but they are outside the scope I chose for this time-boxed exercise.

The reasoning behind these decisions is documented in:

```text
DECISIONS.md
```

---

# Troubleshooting

## `python: command not found`

On macOS or Linux, try:

```bash
python3 --version
```

and use `python3` instead of `python` when creating the virtual environment.

After activating `.venv`, `python` should normally point to the virtual environment.

---

## `No module named ...`

Make sure the virtual environment is activated.

Your terminal should begin with:

```text
(.venv)
```

Then reinstall the dependencies:

```bash
python -m pip install -r requirements.txt
```

---

## `No module named app` when running tests

Make sure you are inside the repository root:

```text
bright-path-scheduling/
```

Then run:

```bash
python -m pytest -v
```

Do not run the test file directly.

---

## Port 8000 is already in use

Start the application on another port:

```bash
python -m uvicorn app.main:app --reload --port 8001
```

Then open:

```text
http://127.0.0.1:8001/docs
```

---

# Design notes

For questions, assumptions, trade-offs, and implementation decisions, see:

[`DECISIONS.md`](DECISIONS.md)