# Owner schedule view concept

> **Status:** Prepared follow-up concept. This is not an implemented endpoint or user interface.

The owner asked to open the laptop and see today's schedule. The assessment implementation focuses on preventing invalid new bookings, but this document makes the next read-only slice concrete without expanding the submitted feature.

## Example using the supplied data

Pinned date: **Tuesday, March 10, 2026**.

```text
BRIGHT PATH — DAILY SCHEDULE                          Tue, 10 Mar 2026

┌──────────────┬──────────────┬──────────────┐
│ 2 lessons    │ 2 students   │ 1 conflict   │
└──────────────┴──────────────┴──────────────┘

09:00–10:00
  R1  BOOKED   Le Minh Chau       T1 · Ngoc Anh     ⚠ tutor conflict
  R2  BOOKED   Tran Bao Long      T1 · Ngoc Anh     ⚠ tutor conflict
  R3  FREE     Based on rooms represented in the export

⚠ T1 appears in R1 and R2 at the same time.
```

The two bookings above come directly from `L033` and `L034` in `data/lessons_export.csv`. They remain in the database as historical seed records. The implemented validation prevents a new request from creating the same kind of conflict; it does not rewrite the historical export.

## What can be stated safely

| Indicator | Value | Evidence |
|---|---:|---|
| Booked lessons | 2 | `L033`, `L034` |
| Students scheduled | 2 | Le Minh Chau, Tran Bao Long |
| Tutor conflicts | 1 | T1 is assigned to both lessons |
| Occupied represented rooms | R1, R2 | Both have a 09:00 booking |
| Free represented rooms | R3 | No overlapping booking in the export |

The brief says the centre has six rooms, but the supplied export only identifies R1, R2, and R3. The other room identifiers must be confirmed before they can be shown as available. Exact opening hours are also unspecified, so the view should not manufacture all-day free slots.

## Proposed next endpoint

```http
GET /schedule?date=2026-03-10
```

Proposed response shape:

```json
{
  "date": "2026-03-10",
  "summary": {
    "booked_lessons": 2,
    "students_scheduled": 2,
    "conflicts": 1
  },
  "lessons": [
    {
      "lesson_id": "L033",
      "start_time": "09:00",
      "duration_min": 60,
      "student": "Le Minh Chau",
      "tutor_id": "T1",
      "room": "R1",
      "status": "booked",
      "warnings": ["TUTOR_CONFLICT"]
    },
    {
      "lesson_id": "L034",
      "start_time": "09:00",
      "duration_min": 60,
      "student": "Tran Bao Long",
      "tutor_id": "T1",
      "room": "R2",
      "status": "booked",
      "warnings": ["TUTOR_CONFLICT"]
    }
  ],
  "represented_room_availability": [
    {
      "room": "R3",
      "start_time": "09:00",
      "end_time": "10:00",
      "available": true
    }
  ]
}
```

## Acceptance criteria for the follow-up

- The owner can select a date and see every lesson in time order.
- `booked`, `cancelled`, and `no_show` are visually distinct.
- Historical conflicts are highlighted rather than silently corrected.
- Availability is shown only for configured rooms and opening hours.
- The view is read-only; creating and changing bookings remain separate actions.
- Later changes can be compared with the schedule published at the 16:00 cut-off.

## Data needed before implementation

- canonical IDs for all six rooms
- exact opening and closing times by day
- stable student IDs instead of name matching
- the definition of when a tutor has received or acknowledged a schedule
- whether paired exam lessons should be represented as one lesson with multiple students

This keeps the next step visible and testable while preserving the assessment's one-feature scope.
