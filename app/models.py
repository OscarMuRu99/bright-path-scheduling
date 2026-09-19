from datetime import date, time
import re

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal


class BookingCreate(BaseModel):
    lesson_id: str
    date: str
    start_time: str
    duration_min: int = Field(gt=0)
    student: str
    tutor_id: str
    room: str


    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Use YYYY-MM-DD for the lesson date.")
        date.fromisoformat(value)
        return value

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9]{2}:[0-9]{2}", value):
            raise ValueError("Use HH:MM in local 24-hour time.")
        time.fromisoformat(value)
        return value


class BookingResponse(BaseModel):
    lesson_id: str
    date: str
    start_time: str
    duration_min: int
    student: str
    tutor_id: str
    room: str
    status: Literal["booked", "cancelled", "no_show"]
    cancelled_at: Optional[str] = None
    note: Optional[str] = None
