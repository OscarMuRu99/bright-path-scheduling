import sqlite3

from fastapi import FastAPI, HTTPException

from app.booking_service import (
    BookingUnavailableError,
    BookingValidationError,
    create_booking,
)
from app.database import get_connection, seed_database
from app.models import BookingCreate, BookingResponse


app = FastAPI(
    title="Bright Path Scheduling API",
    description="API for preventing invalid lesson bookings.",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    seed_database()


@app.get(
    "/health",
    responses={503: {"description": "Booking database unavailable"}},
)
def health():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ok"}
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": "The booking database is unavailable.",
            },
        ) from exc


@app.post(
    "/bookings",
    response_model=BookingResponse,
    status_code=201,
    responses={
        409: {"description": "Booking violates a scheduling rule"},
        503: {"description": "Booking database unavailable"},
    },
)
def create_booking_endpoint(booking: BookingCreate):
    try:
        return create_booking(booking)

    except BookingValidationError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": exc.code,
                "message": exc.message,
            },
        ) from exc

    except BookingUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": str(exc),
            },
        ) from exc
