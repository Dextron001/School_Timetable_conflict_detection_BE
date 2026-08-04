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
    """A single scheduled course/lecture session.

    NOTE: time_start / time_end are stored as 24-hour 'HH:MM' strings.
    For 1-unit courses: 1-hour slot (e.g. 08:00-09:00).
    For 2-unit courses: 2-hour block on one day (e.g. 08:00-10:00).
    For 3-unit courses: two sessions — session A (2hr block) + session B (1hr, different day).

    units: credit units (1, 2, or 3). Determines total weekly hours.
    session: "A" for main session, "B" for additional session (3-unit courses only).
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
    time_start = Column(String, nullable=False, default="08:00")
    time_end = Column(String, nullable=False, default="09:00")
    units = Column(Integer, nullable=False, default=1)  # 1, 2, or 3 credit units
    session = Column(String, nullable=False, default="A")  # "A" or "B" (for 3-unit courses)


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


class ComplaintMessage(Base):
    """A chat message in a complaint thread — supports back-and-forth between student and admin."""
    __tablename__ = "complaint_messages"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_role = Column(String, nullable=False)  # "admin" or "client"
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))