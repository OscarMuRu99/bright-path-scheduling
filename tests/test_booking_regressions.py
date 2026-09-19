import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app


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


@pytest.mark.parametrize("changes", [
    {"date": "invalid"}, {"date": "2026-02-30"}, {"date": "20260307"},
    {"date": "2026-03-07T00:00:00"}, {"start_time": "25:00"},
    {"start_time": "1300"}, {"start_time": "13:00+01:00"},
])
def test_invalid_date_or_time_is_422(client, changes):
    assert client.post("/bookings", json=proposal(**changes)).status_code == 422
    with database.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 34


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
