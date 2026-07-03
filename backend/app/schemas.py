"""Pydantic request/response schemas."""
from pydantic import BaseModel


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Users ----------
class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: str = "client"  # 'admin' or 'client'


class UserUpdate(BaseModel):
    """Fields an admin can edit on a user (all optional)."""
    full_name: str | None = None
    password: str | None = None
    role: str | None = None


# ---------- Courses ----------
class CourseItemOut(BaseModel):
    id: int
    department: str
    academic_level: str
    name: str
    description: str | None = None
    course_code: str
    lecturer_name: str
    day_of_the_week: str
    time_start: str
    time_end: str

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    department: str
    academic_level: str
    name: str
    description: str | None = None
    course_code: str
    lecturer_name: str
    day_of_the_week: str = "Monday"
    time_start: str = "08:30"
    time_end: str = "10:00"


class CourseUpdate(BaseModel):
    """Fields an admin can edit on a course (all optional)."""
    name: str | None = None
    description: str | None = None
    lecturer_name: str | None = None
    day_of_the_week: str | None = None
    time_start: str | None = None
    time_end: str | None = None