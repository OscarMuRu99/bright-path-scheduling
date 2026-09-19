import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app import database
from app.booking_service import BookingValidationError, create_booking
from app.main import app
from app.models import BookingCreate


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as client:
        yield client


def proposal(**changes):
    return dict(
        lesson_id="NEW", date="2026-03-07", start_time="13:00",
        duration_min=60, student="Test Student", tutor_id="T2", room="R1",
    ) | changes


def test_readme_examples_and_persistence(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert client.post("/bookings", json=proposal()).status_code == 201
    with database.get_connection() as conn:
        assert conn.execute("SELECT status FROM bookings WHERE lesson_id='NEW'").fetchone()[0] == "booked"
    conflict = client.post("/bookings", json=proposal(
        lesson_id="CONFLICT", date="2026-03-10", start_time="09:30", tutor_id="T1", room="R3",
    ))
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "TUTOR_CONFLICT"
    closed = client.post("/bookings", json=proposal(lesson_id="CLOSED", date="2026-03-09"))
    assert closed.status_code == 409
    assert closed.json()["detail"]["code"] == "CENTRE_CLOSED"


def test_openapi_documents_example_and_error_responses(client):
    schema = client.get("/openapi.json").json()
    post_booking = schema["paths"]["/bookings"]["post"]
    example = schema["components"]["schemas"]["BookingCreate"]["example"]

    assert example == proposal(lesson_id="TEST001")
    assert {"201", "409", "422", "503"}.issubset(post_booking["responses"])


@pytest.mark.parametrize("changes", [
    {"date": "invalid"}, {"date": "2026-02-30"}, {"date": "20260307"},
    {"date": "2026-03-07T00:00:00"}, {"start_time": "25:00"},
    {"start_time": "1300"}, {"start_time": "13:00+01:00"},
])
def test_invalid_date_or_time_is_422(client, changes):
    assert client.post("/bookings", json=proposal(**changes)).status_code == 422
    with database.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 34


@pytest.mark.parametrize("field", [
    "lesson_id", "date", "start_time", "duration_min", "student", "tutor_id", "room",
])
def test_missing_required_field_is_422_without_writing(client, field):
    request = proposal()
    request.pop(field)

    assert client.post("/bookings", json=request).status_code == 422
    with database.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 34


@pytest.mark.parametrize("field", ["lesson_id", "student", "tutor_id", "room"])
def test_blank_required_text_is_422(client, field):
    response = client.post("/bookings", json=proposal(**{field: "   "}))

    assert response.status_code == 422


def test_malformed_json_and_unknown_fields_are_422(client):
    malformed = client.post(
        "/bookings",
        content="{",
        headers={"content-type": "application/json"},
    )
    unknown_field = client.post(
        "/bookings",
        json=proposal(unexpected="value"),
    )

    assert malformed.status_code == 422
    assert unknown_field.status_code == 422


def test_text_is_trimmed_before_validation_and_storage(client):
    response = client.post("/bookings", json=proposal(
        lesson_id="  TRIMMED  ",
        student="  Test Student  ",
        tutor_id="  T2  ",
        room="  R1  ",
    ))

    assert response.status_code == 201
    assert response.json()["lesson_id"] == "TRIMMED"
    with database.get_connection() as conn:
        stored = conn.execute(
            "SELECT student, tutor_id, room FROM bookings WHERE lesson_id = 'TRIMMED'"
        ).fetchone()
    assert tuple(stored) == ("Test Student", "T2", "R1")


def test_valid_future_date_is_allowed(client):
    response = client.post(
        "/bookings",
        json=proposal(lesson_id="FUTURE", date="2030-01-05"),
    )

    assert response.status_code == 201


def test_duplicate_id_is_409_without_overwriting(client):
    response = client.post("/bookings", json=proposal(lesson_id="L001"))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "LESSON_ID_EXISTS"
    with database.get_connection() as conn:
        assert conn.execute("SELECT date FROM bookings WHERE lesson_id='L001'").fetchone()[0] == "2026-03-03"


@pytest.mark.parametrize("changes,code", [
    ({"duration_min": 45}, "INVALID_DURATION"),
    ({"tutor_id": "UNKNOWN"}, "UNKNOWN_TUTOR"),
])
def test_other_documented_rules(client, changes, code):
    response = client.post("/bookings", json=proposal(**changes))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == code


def test_cancelled_slot_can_be_reused(client):
    response = client.post("/bookings", json=proposal(
        date="2026-03-03", start_time="14:00", student="Vu Ha My", room="R2",
    ))
    assert response.status_code == 201


def test_no_show_still_blocks_the_slot(client):
    response = client.post("/bookings", json=proposal(
        date="2026-03-05", start_time="13:00", room="R2",
    ))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "TUTOR_CONFLICT"


def test_back_to_back_90_minute_booking(client):
    response = client.post("/bookings", json=proposal(
        date="2026-03-03", start_time="10:00", duration_min=90, room="R2",
    ))
    assert response.status_code == 201


def test_daily_limit_accepts_six_and_rejects_seven(client):
    with database.get_connection() as conn:
        conn.execute("DELETE FROM bookings")
    for index in range(6):
        assert client.post("/bookings", json=proposal(
            lesson_id=f"DAY{index}", start_time=f"{9+index:02}:00",
        )).status_code == 201
    with database.get_connection() as conn:
        conn.execute("UPDATE bookings SET status='no_show' WHERE lesson_id='DAY0'")
    response = client.post("/bookings", json=proposal(start_time="16:00"))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "TUTOR_DAILY_LIMIT"
    with database.get_connection() as conn:
        conn.execute("UPDATE bookings SET status='cancelled' WHERE lesson_id='DAY1'")
    assert client.post("/bookings", json=proposal(start_time="16:00")).status_code == 201


@pytest.mark.parametrize("reverse", [False, True])
def test_overlap_across_midnight(client, reverse):
    # Exact opening hours are unspecified; accepted intervals must still not overlap.
    bookings = [proposal(lesson_id="NIGHT", start_time="23:30"),
                proposal(lesson_id="NEXT", date="2026-03-08", start_time="00:00")]
    if reverse:
        bookings.reverse()
    assert client.post("/bookings", json=bookings[0]).status_code == 201
    response = client.post("/bookings", json=bookings[1])
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "TUTOR_CONFLICT"


def test_seed_is_idempotent_and_independent_of_working_directory(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with database.get_connection() as conn:
        before = [tuple(row) for row in conn.execute("SELECT * FROM bookings ORDER BY lesson_id")]
    database.seed_database()
    with database.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tutors").fetchone()[0] == 3
        assert [tuple(row) for row in conn.execute("SELECT * FROM bookings ORDER BY lesson_id")] == before
        with pytest.raises(sqlite3.IntegrityError) as exc:
            conn.execute("INSERT INTO bookings (lesson_id,date,start_time,duration_min,student,tutor_id,room,status) VALUES ('BAD','2026-03-07','13:00',60,'Test','UNKNOWN','R1','booked')")
        assert "FOREIGN KEY" in str(exc.value)


def test_transaction_rolls_back_if_an_error_occurs(client):
    with pytest.raises(RuntimeError):
        with database.get_connection() as conn:
            conn.execute(
                "INSERT INTO bookings (lesson_id,date,start_time,duration_min,student,tutor_id,room,status) VALUES ('ROLLBACK','2030-01-05','13:00',60,'Test','T2','R1','booked')"
            )
            raise RuntimeError("simulated failure after insert")

    with database.get_connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE lesson_id = 'ROLLBACK'"
        ).fetchone()[0] == 0


def test_concurrent_conflicting_requests_create_only_one_booking(client):
    requests = [
        BookingCreate(**proposal(
            lesson_id=lesson_id,
            date="2030-01-05",
            start_time="15:00",
        ))
        for lesson_id in ("CONCURRENT_A", "CONCURRENT_B")
    ]

    def submit(booking):
        try:
            return create_booking(booking)
        except BookingValidationError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit, requests))

    assert sum(isinstance(result, dict) for result in results) == 1
    assert results.count("TUTOR_CONFLICT") == 1
    with database.get_connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE lesson_id LIKE 'CONCURRENT_%'"
        ).fetchone()[0] == 1


def test_database_failure_returns_503(client, tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "missing" / "test.db")

    health = client.get("/health")
    booking = client.post("/bookings", json=proposal())

    assert health.status_code == 503
    assert health.json()["detail"]["code"] == "DATABASE_UNAVAILABLE"
    assert booking.status_code == 503
    assert booking.json()["detail"]["code"] == "DATABASE_UNAVAILABLE"


def test_committed_booking_survives_application_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "restart.db")

    with TestClient(app) as first_run:
        assert first_run.post(
            "/bookings",
            json=proposal(lesson_id="PERSISTED"),
        ).status_code == 201

    with TestClient(app) as restarted:
        assert restarted.get("/health").status_code == 200
        duplicate = restarted.post(
            "/bookings",
            json=proposal(lesson_id="PERSISTED"),
        )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "LESSON_ID_EXISTS"
