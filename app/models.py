from pydantic import BaseModel, Field
from typing import Optional, Literal


class BookingCreate(BaseModel):
    lesson_id: str
    date: str
    start_time: str
    duration_min: int = Field(gt=0)
    student: str
    tutor_id: str
    room: str


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