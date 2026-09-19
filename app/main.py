from fastapi import FastAPI, HTTPException

from app.booking_service import BookingValidationError, create_booking
from app.database import seed_database
from app.models import BookingCreate, BookingResponse


app = FastAPI(
    title="Bright Path Scheduling API",
    description="API for preventing invalid lesson bookings.",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    seed_database()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/bookings",
    response_model=BookingResponse,
    status_code=201,
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
        )