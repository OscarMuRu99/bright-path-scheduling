import pytest

from app import database
from app.booking_service import (
    BookingValidationError,
    create_booking,
    validate_booking,
)
from app.models import BookingCreate


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    database.seed_database()

    return test_db


def test_accepts_valid_booking(isolated_db):
    booking = BookingCreate(
        lesson_id="TEST001",
        date="2026-03-07",
        start_time="13:00",
        duration_min=60,
        student="Test Student",
        tutor_id="T2",
        room="R1",
    )

    result = create_booking(booking)

    assert result["status"] == "booked"
    assert result["lesson_id"] == "TEST001"


def test_rejects_tutor_conflict(isolated_db):
    booking = BookingCreate(
        lesson_id="TEST002",
        date="2026-03-10",
        start_time="09:30",
        duration_min=60,
        student="Another Student",
        tutor_id="T1",
        room="R3",
    )

    with pytest.raises(BookingValidationError) as exc:
        validate_booking(booking)

    assert exc.value.code == "TUTOR_CONFLICT"


def test_rejects_room_conflict(isolated_db):
    booking = BookingCreate(
        lesson_id="TEST003",
        date="2026-03-03",
        start_time="09:30",
        duration_min=60,
        student="Another Student",
        tutor_id="T3",
        room="R1",
    )

    with pytest.raises(BookingValidationError) as exc:
        validate_booking(booking)

    assert exc.value.code == "ROOM_CONFLICT"


def test_rejects_student_conflict(isolated_db):
    booking = BookingCreate(
        lesson_id="TEST004",
        date="2026-03-03",
        start_time="09:30",
        duration_min=60,
        student="Le Minh Chau",
        tutor_id="T3",
        room="R3",
    )

    with pytest.raises(BookingValidationError) as exc:
        validate_booking(booking)

    assert exc.value.code == "STUDENT_CONFLICT"


def test_rejects_monday_booking(isolated_db):
    booking = BookingCreate(
        lesson_id="TEST005",
        date="2026-03-09",
        start_time="13:00",
        duration_min=60,
        student="Test Student",
        tutor_id="T2",
        room="R1",
    )

    with pytest.raises(BookingValidationError) as exc:
        validate_booking(booking)

    assert exc.value.code == "CENTRE_CLOSED"


def test_rejects_seventh_tutor_booking(isolated_db):
    booking = BookingCreate(
        lesson_id="TEST006",
        date="2026-03-06",
        start_time="22:00",
        duration_min=60,
        student="Test Student",
        tutor_id="T1",
        room="R1",
    )

    with pytest.raises(BookingValidationError) as exc:
        validate_booking(booking)

    assert exc.value.code == "TUTOR_DAILY_LIMIT"
