"""SQLAlchemy ORM models."""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from .database import Base


class User(Base):
    """Application user. role is either 'admin' or 'client'."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False, default="")
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="client")  # 'admin' | 'client'


class CourseItem(Base):
    """A single scheduled course/lecture slot.

    NOTE: time_start / time_end are stored as 24-hour 'HH:MM' strings
    (e.g. '13:00' for 1pm). This fixes the old bug where '1:00' was parsed
    as 1am and broke conflict detection.
    """
    __tablename__ = "course_items"

    id = Column(Integer, primary_key=True, index=True)
    department = Column(String, index=True, nullable=False)
    academic_level = Column(String, index=True, nullable=False, default="100")
    name = Column(String, index=True, nullable=False, default="Untitled Course")
    description = Column(String, nullable=True)  # used as venue/room
    course_code = Column(String, index=True, nullable=False, default="GEN000")
    lecturer_name = Column(String, nullable=False, default="TBA")
    day_of_the_week = Column(String, nullable=False, default="Monday")
    time_start = Column(String, nullable=False, default="08:30")
    time_end = Column(String, nullable=False, default="10:00")


class Complaint(Base):
    """A timetable complaint submitted by a client user."""
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    faculty = Column(String, nullable=False)           # FPAS or FSMS
    course_code = Column(String, nullable=True)        # specific course if applicable
    subject = Column(String, nullable=False)           # short title
    message = Column(Text, nullable=False)             # full complaint text
    status = Column(String, nullable=False, default="pending")  # pending / resolved / dismissed
    admin_note = Column(Text, nullable=True)           # admin's reply/note
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)