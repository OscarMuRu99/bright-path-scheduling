from contextlib import contextmanager
import csv
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "bright_path.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tutors (
                tutor_id TEXT PRIMARY KEY,
                tutor_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                phone TEXT
            );

            CREATE TABLE IF NOT EXISTS bookings (
                lesson_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                duration_min INTEGER NOT NULL CHECK (duration_min > 0),
                student TEXT NOT NULL,
                tutor_id TEXT NOT NULL,
                room TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK (status IN ('booked', 'cancelled', 'no_show')),
                cancelled_at TEXT,
                note TEXT,
                FOREIGN KEY (tutor_id) REFERENCES tutors(tutor_id)
            );
            """
        )


def seed_tutors():
    path = DATA_DIR / "tutors.csv"

    with path.open(newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file)

        with get_connection() as conn:
            for row in rows:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO tutors
                    (tutor_id, tutor_name, subject, phone)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        row["tutor_id"],
                        row["tutor_name"],
                        row["subject"],
                        row["phone"],
                    ),
                )


def seed_bookings():
    path = DATA_DIR / "lessons_export.csv"

    with path.open(newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file)

        with get_connection() as conn:
            for row in rows:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO bookings
                    (
                        lesson_id,
                        date,
                        start_time,
                        duration_min,
                        student,
                        tutor_id,
                        room,
                        status,
                        cancelled_at,
                        note
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["lesson_id"],
                        row["date"],
                        row["start_time"],
                        int(row["duration_min"]),
                        row["student"],
                        row["tutor_id"],
                        row["room"],
                        row["status"],
                        row["cancelled_at"] or None,
                        row["note"] or None,
                    ),
                )


def seed_database():
    init_db()
    seed_tutors()
    seed_bookings()


if __name__ == "__main__":
    seed_database()
    print(f"Database seeded at {DB_PATH}")
