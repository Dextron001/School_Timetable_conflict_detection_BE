"""FastAPI application: auth + course/timetable endpoints with role-based access.

Roles:
  - admin  : can generate, resolve, edit and export timetables, manage users
  - client : can only view and download (export) timetables
"""
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from . import auth, schemas, timetable
from .database import Base, engine, get_db
from .models import CourseItem, User
from .pdf_export import build_timetable_pdf
from .seed import DEPARTMENT_POOLS, seed_all

load_dotenv()

# Create tables and seed on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Timetable Conflict Detection API", version="2.0.0")

# ---- CORS from environment ----
_cors_origins_str = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
CORS_ORIGINS = [o.strip() for o in _cors_origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    from .database import SessionLocal

    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()


# ----------------------------- Auth -----------------------------
@app.post("/auth/login", response_model=schemas.TokenResponse, tags=["auth"])
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not auth.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = auth.create_access_token({"sub": user.username, "role": user.role})
    return schemas.TokenResponse(access_token=token, user=user)


@app.get("/auth/me", response_model=schemas.UserOut, tags=["auth"])
def me(current: User = Depends(auth.get_current_user)):
    return current


# --------------------------- Metadata ---------------------------
@app.get("/departments", tags=["meta"])
def departments(current: User = Depends(auth.get_current_user)):
    return [{"code": code, "name": pool["name"]} for code, pool in DEPARTMENT_POOLS.items()]


# --------------------------- Courses ----------------------------
@app.get("/courses", response_model=list[schemas.CourseItemOut], tags=["courses"])
def list_courses(
    department: str = Query(...),
    academic_level: str = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(auth.get_current_user),  # any logged-in user
):
    return (
        db.query(CourseItem)
        .filter(
            CourseItem.department == department.upper(),
            CourseItem.academic_level == academic_level,
        )
        .all()
    )


@app.post("/courses", response_model=schemas.CourseItemOut, tags=["courses"])
def create_course(
    payload: schemas.CourseCreate,
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
):
    course = CourseItem(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@app.put("/generate", response_model=list[schemas.CourseItemOut], tags=["courses"])
def generate(
    department: str = Query(...),
    academic_level: str = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),  # admin only
):
    result = timetable.generate_for(db, department, academic_level)
    if not result:
        raise HTTPException(status_code=404, detail="No courses for that department/level")
    return result


@app.put("/resolve", tags=["courses"])
def resolve(
    department: str = Query(...),
    academic_level: str = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),  # admin only
):
    """Resolve clashes with the DSATUR graph-colouring scheduler.

    Returns both the algorithm report and the updated course list so the UI can
    show what happened (e.g. "DSATUR graph colouring · 6 nodes · 5 colours").
    """
    report = timetable.resolve_for(db, department, academic_level)
    courses = (
        db.query(CourseItem)
        .filter(
            CourseItem.department == department.upper(),
            CourseItem.academic_level == academic_level,
        )
        .all()
    )
    return {
        "report": report,
        "courses": [schemas.CourseItemOut.model_validate(c) for c in courses],
    }


@app.patch("/courses/{course_id}", response_model=schemas.CourseItemOut, tags=["courses"])
def update_course(
    course_id: int,
    payload: schemas.CourseUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),  # admin only
):
    course = db.query(CourseItem).filter(CourseItem.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


@app.delete("/courses/{course_id}", tags=["courses"])
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
):
    course = db.query(CourseItem).filter(CourseItem.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()
    return {"detail": "Course deleted"}


@app.get("/conflicts", tags=["courses"])
def conflicts(
    department: str = Query(...),
    academic_level: str = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(auth.get_current_user),
):
    """Return ids of courses that currently clash (used to highlight in the UI)."""
    courses = (
        db.query(CourseItem)
        .filter(
            CourseItem.department == department.upper(),
            CourseItem.academic_level == academic_level,
        )
        .all()
    )
    return {"conflict_ids": sorted(timetable.find_conflicts(courses))}


# --------------------------- Export -----------------------------
@app.get("/export-pdf", tags=["export"])
def export_pdf(
    department: str = Query(...),
    academic_level: str = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(auth.get_current_user),  # clients can download too
):
    courses = (
        db.query(CourseItem)
        .filter(
            CourseItem.department == department.upper(),
            CourseItem.academic_level == academic_level,
        )
        .all()
    )
    if not courses:
        raise HTTPException(status_code=404, detail="No courses to export")
    pdf = build_timetable_pdf(courses, department, academic_level)
    filename = f"{department.upper()}_{academic_level}_Timetable.pdf"
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ------------------------ User Management ------------------------
@app.get("/users", response_model=list[schemas.UserOut], tags=["users"])
def list_users(
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
):
    return db.query(User).order_by(User.id).all()


@app.post("/users", response_model=schemas.UserOut, tags=["users"])
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=auth.hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.patch("/users/{user_id}", response_model=schemas.UserOut, tags=["users"])
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.hashed_password = auth.hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@app.delete("/users/{user_id}", tags=["users"])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
):
    if user_id == current.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}


# ----------------------------- Root -----------------------------
@app.get("/", tags=["meta"])
def root():
    return {"status": "ok", "service": "ResolvIt API", "version": "2.0.0"}