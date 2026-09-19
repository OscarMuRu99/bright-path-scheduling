from datetime import datetime, timedelta

from app.database import get_connection
from app.models import BookingCreate


class BookingValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _to_datetime(date: str, time: str) -> datetime:
    return datetime.fromisoformat(f"{date}T{time}")


def _overlaps(
    new_start: datetime,
    new_end: datetime,
    existing_start: datetime,
    existing_end: datetime,
) -> bool:
    return new_start < existing_end and new_end > existing_start


def validate_booking(booking: BookingCreate) -> None:
    booking_date = datetime.fromisoformat(booking.date).date()

    # Monday = 0
    if booking_date.weekday() == 0:
        raise BookingValidationError(
            "CENTRE_CLOSED",
            "The centre is closed on Mondays.",
        )

    if booking.duration_min not in (60, 90):
        raise BookingValidationError(
            "INVALID_DURATION",
            "Lessons must be 60 or 90 minutes long.",
        )

    new_start = _to_datetime(booking.date, booking.start_time)
    new_end = new_start + timedelta(minutes=booking.duration_min)

    with get_connection() as conn:
        if conn.execute(
            "SELECT 1 FROM bookings WHERE lesson_id = ?", (booking.lesson_id,)
        ).fetchone():
            raise BookingValidationError(
                "LESSON_ID_EXISTS",
                f"Lesson {booking.lesson_id} already exists.",
            )

        tutor = conn.execute(
            "SELECT tutor_id FROM tutors WHERE tutor_id = ?",
            (booking.tutor_id,),
        ).fetchone()

        if tutor is None:
            raise BookingValidationError(
                "UNKNOWN_TUTOR",
                f"Tutor {booking.tutor_id} does not exist.",
            )

        existing_bookings = conn.execute(
            """
            SELECT *
            FROM bookings
            WHERE status != 'cancelled'
            """,
        ).fetchall()

        tutor_count = sum(
            1
            for existing in existing_bookings
            if existing["tutor_id"] == booking.tutor_id
            and existing["date"] == booking.date
        )

        if tutor_count >= 6:
            raise BookingValidationError(
                "TUTOR_DAILY_LIMIT",
                f"Tutor {booking.tutor_id} already has at least six non-cancelled bookings that day.",
            )

        for existing in existing_bookings:
            existing_start = _to_datetime(
                existing["date"],
                existing["start_time"],
            )
            existing_end = existing_start + timedelta(
                minutes=existing["duration_min"]
            )

            if not _overlaps(
                new_start,
                new_end,
                existing_start,
                existing_end,
            ):
                continue

            if existing["tutor_id"] == booking.tutor_id:
                raise BookingValidationError(
                    "TUTOR_CONFLICT",
                    f"Tutor {booking.tutor_id} is already booked during this time.",
                )

            if existing["room"] == booking.room:
                raise BookingValidationError(
                    "ROOM_CONFLICT",
                    f"Room {booking.room} is already booked during this time.",
                )

            if existing["student"] == booking.student:
                raise BookingValidationError(
                    "STUDENT_CONFLICT",
                    f"{booking.student} already has a lesson during this time.",
                )


def create_booking(booking: BookingCreate):
    validate_booking(booking)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO bookings (
                lesson_id,
                date,
                start_time,
                duration_min,
                student,
                tutor_id,
                room,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'booked')
            """,
            (
                booking.lesson_id,
                booking.date,
                booking.start_time,
                booking.duration_min,
                booking.student,
                booking.tutor_id,
                booking.room,
            ),
        )

    return {
        **booking.model_dump(),
        "status": "booked",
        "cancelled_at": None,
        "note": None,
    }
