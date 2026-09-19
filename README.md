# Bright Path Scheduling

A small FastAPI service for the Bright Path Learning Centre engineering assessment.

It implements one feature: **preventing invalid lesson bookings before they are added to the schedule**. A proposed booking is either stored in SQLite or rejected with a clear conflict code.

| Item | Details |
|---|---|
| Runtime | Python 3.10+ |
| API | FastAPI |
| Database | SQLite, created locally |
| Tests | pytest, 43 passing |
| Main endpoint | `POST /bookings` |
| Interactive documentation | `http://127.0.0.1:8000/docs` |

No Docker, external database, API key, or environment variables are required.

## What the feature enforces

For every new booking, the service checks:

- the centre is open that day (Tuesday to Sunday)
- the duration is 60 or 90 minutes
- the tutor exists
- the tutor, room, and student are not already booked during that time
- the tutor has fewer than six non-cancelled bookings that day
- the `lesson_id` has not already been used
- required text fields are not empty and unknown request fields are rejected

Cancelled lessons free the tutor, room, student, and daily booking count. A `no_show` still occupies its original slot and counts toward the limit.

The supplied CSV files are historical seed data. They are loaded exactly as provided, including records that conflict with the stated business rules. The assumptions and scope decisions are explained in [DECISIONS.md](DECISIONS.md).

## Reviewer quick start

The complete path is:

```text
clone -> create virtual environment -> install -> run tests -> start API -> open /docs
```

### 1. Prerequisites

Install:

- [Git](https://git-scm.com/downloads)
- [Python](https://www.python.org/downloads/) 3.10 or newer

Check the installed versions:

```bash
git --version
python --version
```

On macOS or Linux, use `python3 --version` if `python` is not available.

### 2. Clone the repository

```bash
git clone https://github.com/OscarMuRu99/bright-path-scheduling.git
cd bright-path-scheduling
```

Run all remaining commands from the `bright-path-scheduling` directory.

### 3. Create and activate a virtual environment

Choose the instructions for your operating system.

#### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, use Windows Command Prompt below. You can also keep using PowerShell and replace `python` in later commands with `.\.venv\Scripts\python.exe`.

#### Windows Command Prompt

```cmd
py -m venv .venv
.venv\Scripts\activate.bat
```

After activation, the terminal prompt normally begins with `(.venv)`. Confirm that the active Python is new enough:

```bash
python --version
```

### 4. Install the dependencies

```bash
python -m pip install -r requirements.txt
```

This installs the exact direct dependency versions used for the final verification.

### 5. Run the automated tests

```bash
python -m pytest -v
```

Expected summary:

```text
43 passed
```

The tests use temporary SQLite databases. They do not change the database used when you run the API manually.

### 6. Start the API

```bash
python -m uvicorn app.main:app --reload
```

Leave this terminal open. A successful start includes:

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

On first startup, the application creates `bright_path.db` and loads:

```text
data/tutors.csv
data/lessons_export.csv
```

To stop the API, return to this terminal and press `Ctrl+C`.

### 7. Open the API documentation

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in a browser while the API is running.

This is FastAPI's interactive Swagger UI, so the endpoint can be exercised without Postman. A quick health check is also available at [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health):

```json
{
  "status": "ok"
}
```

## Manual API walkthrough

In `/docs`:

1. Expand `POST /bookings`.
2. Select **Try it out**.
3. Replace the request body with an example below.
4. Select **Execute**.

Dates must be real calendar dates in `YYYY-MM-DD` format. Times use local 24-hour `HH:MM` format without a timezone suffix.

### Example 1: create a valid booking

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

Expected status:

```text
201 Created
```

The booking is stored in `bright_path.db`. Each booking needs a unique `lesson_id`; executing this exact example again returns `409 LESSON_ID_EXISTS`.

### Example 2: reject a tutor conflict

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

Tutor T1 has a seeded lesson that overlaps this time. Expected status and response:

```text
409 Conflict
```

```json
{
  "detail": {
    "code": "TUTOR_CONFLICT",
    "message": "Tutor T1 is already booked during this time."
  }
}
```

### Example 3: reject a Monday booking

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

March 9, 2026 is a Monday. Expected result:

```text
409 Conflict
CENTRE_CLOSED
```

## Copy/paste conflict examples

Each request below is independent and can be pasted directly into `POST /bookings` in `/docs`. Every request should return `409 Conflict` with the stated `detail.code`. Rejected requests are not stored, so they can be executed again.

### `TUTOR_CONFLICT`

T1 already has a seeded lesson from 09:00 to 10:00 on March 10.

```json
{
  "lesson_id": "EX_TUTOR_CONFLICT",
  "date": "2026-03-10",
  "start_time": "09:30",
  "duration_min": 60,
  "student": "Test Student",
  "tutor_id": "T1",
  "room": "R3"
}
```

Expected: `409 TUTOR_CONFLICT`.

### `ROOM_CONFLICT`

R1 already has a seeded lesson from 09:00 to 10:00 on March 3.

```json
{
  "lesson_id": "EX_ROOM_CONFLICT",
  "date": "2026-03-03",
  "start_time": "09:30",
  "duration_min": 60,
  "student": "Test Student",
  "tutor_id": "T3",
  "room": "R1"
}
```

Expected: `409 ROOM_CONFLICT`.

### `STUDENT_CONFLICT`

Le Minh Chau already has a seeded lesson from 09:00 to 10:00 on March 3.

```json
{
  "lesson_id": "EX_STUDENT_CONFLICT",
  "date": "2026-03-03",
  "start_time": "09:30",
  "duration_min": 60,
  "student": "Le Minh Chau",
  "tutor_id": "T3",
  "room": "R3"
}
```

Expected: `409 STUDENT_CONFLICT`.

### `TUTOR_DAILY_LIMIT`

T1 already has more than six non-cancelled seeded bookings on March 6.

```json
{
  "lesson_id": "EX_TUTOR_DAILY_LIMIT",
  "date": "2026-03-06",
  "start_time": "22:00",
  "duration_min": 60,
  "student": "Test Student",
  "tutor_id": "T1",
  "room": "R3"
}
```

Expected: `409 TUTOR_DAILY_LIMIT`.

### `CENTRE_CLOSED`

March 9, 2026 is a Monday.

```json
{
  "lesson_id": "EX_CENTRE_CLOSED",
  "date": "2026-03-09",
  "start_time": "13:00",
  "duration_min": 60,
  "student": "Test Student",
  "tutor_id": "T2",
  "room": "R1"
}
```

Expected: `409 CENTRE_CLOSED`.

### `INVALID_DURATION`

Lessons must last 60 or 90 minutes.

```json
{
  "lesson_id": "EX_INVALID_DURATION",
  "date": "2026-03-07",
  "start_time": "13:00",
  "duration_min": 45,
  "student": "Test Student",
  "tutor_id": "T2",
  "room": "R1"
}
```

Expected: `409 INVALID_DURATION`.

### `UNKNOWN_TUTOR`

The tutor ID does not appear in `data/tutors.csv`.

```json
{
  "lesson_id": "EX_UNKNOWN_TUTOR",
  "date": "2026-03-07",
  "start_time": "13:00",
  "duration_min": 60,
  "student": "Test Student",
  "tutor_id": "UNKNOWN",
  "room": "R1"
}
```

Expected: `409 UNKNOWN_TUTOR`.

### `LESSON_ID_EXISTS`

`L001` already exists in the supplied lesson export.

```json
{
  "lesson_id": "L001",
  "date": "2026-03-07",
  "start_time": "13:00",
  "duration_min": 60,
  "student": "Test Student",
  "tutor_id": "T2",
  "room": "R1"
}
```

Expected: `409 LESSON_ID_EXISTS`.

## API contract

### `GET /health`

Returns `200 OK` when the service is running.

### `POST /bookings`

Required request fields:

| Field | Type | Example | Notes |
|---|---|---|---|
| `lesson_id` | string | `TEST001` | Must be unique |
| `date` | string | `2026-03-07` | Valid `YYYY-MM-DD` date |
| `start_time` | string | `13:00` | Local 24-hour `HH:MM` |
| `duration_min` | integer | `60` | Must be 60 or 90 |
| `student` | string | `Test Student` | Compared with existing student names |
| `tutor_id` | string | `T2` | Must exist in the tutor seed data |
| `room` | string | `R1` | Cannot overlap another lesson in that room |

Text fields are trimmed, must contain 1–100 characters, and cannot contain only spaces. Missing fields, additional unknown fields, and malformed JSON return `422` without writing a booking. Any real calendar date is accepted when it satisfies the centre's rules; the service does not depend on the computer's current date.

Responses:

| Status | Meaning |
|---|---|
| `201 Created` | Booking passed every rule and was stored |
| `409 Conflict` | Valid request shape, but a business rule was violated |
| `422 Unprocessable Entity` | Missing field, wrong type, or invalid date/time format |
| `503 Service Unavailable` | SQLite could not be reached or could not complete the write |

Possible `409` codes:

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

## Database and repeat runs

SQLite keeps setup local and requires no database server. The generated file is:

```text
bright_path.db
```

The application seeds the database automatically at startup. It can also be initialized manually:

```bash
python -m app.database
```

Seeding is idempotent: tutor and lesson IDs are primary keys, and seed inserts use `INSERT OR IGNORE`. Running it again does not duplicate the 3 tutors or 34 supplied lessons. It also does not delete bookings created through the API.

### Transactions and recovery

Validation and insertion happen inside one `BEGIN IMMEDIATE` SQLite transaction. This provides the following behavior:

- a successful request commits the complete booking
- an exception rolls the transaction back, leaving no partial booking
- concurrent booking requests are serialized before conflict validation, so two conflicting requests cannot both be accepted
- database connection or write failures return `503 DATABASE_UNAVAILABLE`
- `/health` returns `503` when the application cannot connect to SQLite

If the API process stops, committed bookings remain in `bright_path.db`. Restart it with the same Uvicorn command; startup safely initializes missing tables and reloads missing seed rows. Automatic process restart is a deployment concern and is not included in this local assessment.

To repeat a manual example, use a new `lesson_id`. To return to only the supplied seed data, stop the API, delete the generated `bright_path.db` file, and start the API again:

```bash
# macOS or Linux
rm bright_path.db
```

```powershell
# Windows PowerShell
Remove-Item bright_path.db
```

```cmd
:: Windows Command Prompt
del bright_path.db
```

## Project structure

```text
bright-path-scheduling/
├── app/
│   ├── main.py                 # HTTP endpoints and startup
│   ├── models.py               # Request and response validation
│   ├── database.py             # SQLite schema and CSV seeding
│   └── booking_service.py      # Scheduling rules and insertion
├── data/
│   ├── lessons_export.csv      # Supplied lesson export
│   └── tutors.csv              # Supplied tutor export
├── tests/
│   ├── test_bookings.py        # Core scheduling-rule tests
│   └── test_booking_regressions.py
├── DECISIONS.md                # Questions, assumptions, design, reflection
├── README.md
├── requirements.txt
└── pytest.ini
```

The request flow is intentionally small:

```text
POST /bookings
      |
      v
Pydantic request validation
      |
      v
Scheduling-rule validation
      |
      +---- conflict ----> 409 response
      |
      v
SQLite insert -----------> 201 response
```

## Tests and observed results

The suite covers:

- valid booking creation and persistence
- tutor, room, and student overlap
- Monday closure and allowed durations
- the sixth-versus-seventh daily booking boundary
- cancelled and no-show behavior
- malformed dates/times and duplicate IDs
- missing fields, blank text, malformed JSON, and unexpected fields
- back-to-back and 90-minute lessons
- overlaps that cross midnight
- atomic rollback and concurrent conflicting requests
- database-unavailable `503` responses and database-aware health checks
- persistence across application restart
- idempotent seeding and working-directory-independent paths
- database foreign-key enforcement

Final verification was performed in a newly created virtual environment on macOS with Python 3.13.4:

| Command | Observed result |
|---|---|
| `python -m pip install -r requirements.txt` | Installation completed |
| `python -m pip check` | No broken requirements found |
| `python -m pytest -v` | 43 passed |
| `python -m app.database` twice | 3 tutors and 34 lessons; no duplicate seed rows |
| Start Uvicorn and request `/health` | `200 OK`, `{"status":"ok"}` |

The macOS commands were executed. Windows and Linux instructions follow the standard Python virtual-environment workflow and were reviewed, but were not executed on those operating systems.

The current dependency versions emit deprecation warnings for the FastAPI startup hook and test transport. They do not fail the tests. Updating those interfaces is intentionally deferred because it does not change the assessment feature.

## Scope and limitations

This assessment implements only new-booking validation. It does not include:

- a receptionist-facing user interface or today's schedule view
- booking updates, cancellations, or automatic rescheduling
- tutor notifications or WhatsApp integration
- billing and cancellation charges
- paired-lesson pricing
- schedule-change history after the 16:00 cut-off

Tutor availability hours and exact centre opening hours are not present in the supplied data, so “available” means “has no conflicting non-cancelled booking.” Students are matched by the provided name string because the export has no student ID. SQLite serializes writes for this single-process assessment; a multi-instance production deployment would require a server database and database-level conflict protection.

See [DECISIONS.md](DECISIONS.md) for the questions I would ask the owner, contradictions in the brief and seed data, assumptions, rejected scope, data-model reasoning, AI usage, and next steps.

### Prepared follow-up: owner schedule view

A read-only [owner schedule view concept](docs/OWNER_VIEW_CONCEPT.md) shows how the supplied March 10 data could become a daily schedule: booked lessons, represented free rooms, and the historical tutor conflict are visible in one place. It also defines a proposed `GET /schedule?date=...` response and the missing business data required before implementation.

This concept is intentionally not presented as working functionality. It makes the next product slice tangible while keeping the submitted implementation focused on booking validation.

## Troubleshooting

### `python` is not found

- macOS/Linux: use `python3` to create `.venv`, then activate it.
- Windows: use `py` to create `.venv`, then activate it.

### `No module named ...`

Confirm that `(.venv)` appears in the prompt, then reinstall:

```bash
python -m pip install -r requirements.txt
```

### `No module named app` when running tests

Run the tests from the repository root with:

```bash
python -m pytest -v
```

### Port 8000 is already in use

Start the API on another port:

```bash
python -m uvicorn app.main:app --reload --port 8001
```

Then open [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs).
