import re
from datetime import date, time
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


RequiredText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class BookingCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "lesson_id": "TEST001",
                "date": "2026-03-07",
                "start_time": "13:00",
                "duration_min": 60,
                "student": "Test Student",
                "tutor_id": "T2",
                "room": "R1",
            }
        },
    )

    lesson_id: RequiredText
    date: str
    start_time: str
    duration_min: int = Field(gt=0)
    student: RequiredText
    tutor_id: RequiredText
    room: RequiredText

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
