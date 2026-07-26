"""FastAPI application: auth + course/timetable endpoints with role-based access.

Scope is FACULTY-level: all endpoints operate on a faculty (FPAS or FSMS)
which includes all departments and all academic levels (100–400) combined.

Roles:
  - admin  : can generate, resolve, edit and export timetables, manage users
  - client : can only view and download (export) timetables
"""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from . import auth, schemas, timetable
from .database import Base, engine, get_db
from .models import Complaint, CourseItem, User
from .pdf_export import build_timetable_pdf
from .seed import DEPARTMENT_POOLS, FACULTIES, seed_all

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Timetable Conflict Detection API", version="2.0.0")

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
@app.get("/faculties", tags=["meta"])
def faculties(current: User = Depends(auth.get_current_user)):
    """Return the two faculties with their departments."""
    return [
        {
            "code": code,
            "name": data["name"],
            "departments": [
                {"code": d, "name": DEPARTMENT_POOLS[d]["name"]}
                for d in data["departments"]
            ],
        }
        for code, data in FACULTIES.items()
    ]


# --------------------------- Courses ----------------------------
@app.get("/courses", response_model=list[schemas.CourseItemOut], tags=["courses"])
def list_courses(
    faculty: str | None = Query(None),
    db: Session = Depends(get_db),
    current: User = Depends(auth.get_current_user),
):
    """List courses for a faculty (all departments, all levels combined).
    If faculty is omitted, return ALL courses."""
    query = db.query(CourseItem)
    if faculty:
        fac = faculty.upper()
        if fac not in FACULTIES:
            raise HTTPException(status_code=404, detail="Faculty not found")
        dept_codes = FACULTIES[fac]["departments"]
        query = query.filter(CourseItem.department.in_(dept_codes))
    return query.all()


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
    faculty: str = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
):
    """Generate a draft timetable for a faculty (all departments, all levels)."""
    fac = faculty.upper()
    if fac not in FACULTIES:
        raise HTTPException(status_code=404, detail="Faculty not found")
    dept_codes = FACULTIES[fac]["departments"]
    courses = db.query(CourseItem).filter(
        CourseItem.department.in_(dept_codes),
    ).all()
    if not courses:
        raise HTTPException(status_code=404, detail="No courses found for that faculty")
    result = timetable.generate_for(db, fac)
    if not result:
        raise HTTPException(status_code=404, detail="No courses for that faculty")
    return result


@app.put("/resolve", tags=["courses"])
def resolve(
    faculty: str = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
):
    """Resolve clashes with DSATUR graph-colouring scheduler for a faculty."""
    fac = faculty.upper()
    if fac not in FACULTIES:
        raise HTTPException(status_code=404, detail="Faculty not found")
    dept_codes = FACULTIES[fac]["departments"]
    courses = db.query(CourseItem).filter(
        CourseItem.department.in_(dept_codes),
    ).all()
    if not courses:
        raise HTTPException(status_code=404, detail="No courses found for that faculty")
    report = timetable.resolve_for(db, fac)
    resolved = db.query(CourseItem).filter(
        CourseItem.department.in_(dept_codes),
    ).all()
    return {
        "report": report,
        "courses": [schemas.CourseItemOut.model_validate(c) for c in resolved],
    }


@app.patch("/courses/{course_id}", response_model=schemas.CourseItemOut, tags=["courses"])
def update_course(
    course_id: int,
    payload: schemas.CourseUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
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
    faculty: str | None = Query(None),
    db: Session = Depends(get_db),
    current: User = Depends(auth.get_current_user),
):
    """Return ids of courses that currently clash within a faculty."""
    query = db.query(CourseItem)
    if faculty:
        fac = faculty.upper()
        if fac not in FACULTIES:
            raise HTTPException(status_code=404, detail="Faculty not found")
        dept_codes = FACULTIES[fac]["departments"]
        query = query.filter(CourseItem.department.in_(dept_codes))
    courses = query.all()
    return {"conflict_ids": sorted(timetable.find_conflicts(courses))}


# --------------------------- Export -----------------------------
@app.get("/export-pdf", tags=["export"])
def export_pdf(
    faculty: str = Query(...),
    db: Session = Depends(get_db),
    current: User = Depends(auth.get_current_user),
):
    fac = faculty.upper()
    if fac not in FACULTIES:
        raise HTTPException(status_code=404, detail="Faculty not found")
    dept_codes = FACULTIES[fac]["departments"]
    courses = db.query(CourseItem).filter(
        CourseItem.department.in_(dept_codes),
    ).all()
    if not courses:
        raise HTTPException(status_code=404, detail="No courses to export")
    fac_name = FACULTIES[fac]["name"]
    conflict_ids = sorted(timetable.find_conflicts(courses))
    pdf = build_timetable_pdf(courses, fac, fac_name, conflict_ids)
    filename = f"{fac}_Combined_Timetable.pdf"
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ------------------------ User Management ------------------------
@app.get("/users", response_model=list[schemas.UserOut], tags=["users"])
def list_users(db: Session = Depends(get_db), current: User = Depends(auth.require_admin)):
    return db.query(User).order_by(User.id).all()


@app.post("/users", response_model=schemas.UserOut, tags=["users"])
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db), current: User = Depends(auth.require_admin)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(username=payload.username, full_name=payload.full_name,
                hashed_password=auth.hash_password(payload.password), role=payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.patch("/users/{user_id}", response_model=schemas.UserOut, tags=["users"])
def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db), current: User = Depends(auth.require_admin)):
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
def delete_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(auth.require_admin)):
    if user_id == current.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}


# ------------------------ Complaints ----------------------------
@app.post("/complaints", response_model=schemas.ComplaintOut, tags=["complaints"])
def create_complaint(
    payload: schemas.ComplaintCreate,
    db: Session = Depends(get_db),
    current: User = Depends(auth.get_current_user),
):
    """Client submits a timetable complaint."""
    fac = payload.faculty.upper()
    if fac not in FACULTIES:
        raise HTTPException(status_code=404, detail="Faculty not found")
    complaint = Complaint(
        user_id=current.id,
        faculty=fac,
        course_code=payload.course_code,
        subject=payload.subject,
        message=payload.message,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    # ── Email notification (disabled by default, enable via .env) ──
    try:
        from .email_service import send_complaint_notification
        send_complaint_notification(complaint, current, db)
    except Exception as e:
        print(f"[Email] Could not send notification: {e}")

    return _complaint_to_out(complaint, db)


@app.get("/complaints", tags=["complaints"])
def list_complaints(
    faculty: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
):
    """Admin views all complaints. Optional filters: faculty, status."""
    query = db.query(Complaint)
    if faculty:
        fac = faculty.upper()
        if fac not in FACULTIES:
            raise HTTPException(status_code=404, detail="Faculty not found")
        query = query.filter(Complaint.faculty == fac)
    if status:
        query = query.filter(Complaint.status == status)
    complaints = query.order_by(Complaint.created_at.desc()).all()
    return [_complaint_to_out(c, db) for c in complaints]


@app.patch("/complaints/{complaint_id}", response_model=schemas.ComplaintOut, tags=["complaints"])
def resolve_complaint(
    complaint_id: int,
    payload: schemas.ComplaintResolve,
    db: Session = Depends(get_db),
    current: User = Depends(auth.require_admin),
):
    """Admin resolves or dismisses a complaint."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaint.status = payload.status
    complaint.admin_note = payload.admin_note
    complaint.resolved_at = datetime.now(timezone.utc)
    complaint.resolved_by = current.id
    db.commit()
    db.refresh(complaint)
    return _complaint_to_out(complaint, db)


@app.get("/complaints/my", tags=["complaints"])
def my_complaints(
    db: Session = Depends(get_db),
    current: User = Depends(auth.get_current_user),
):
    """Client views their own complaints."""
    complaints = db.query(Complaint).filter(
        Complaint.user_id == current.id,
    ).order_by(Complaint.created_at.desc()).all()
    return [_complaint_to_out(c, db) for c in complaints]


def _complaint_to_out(complaint: Complaint, db: Session) -> dict:
    """Convert a Complaint ORM object to a dict matching ComplaintOut schema."""
    submitter = db.query(User).filter(User.id == complaint.user_id).first()
    resolver = db.query(User).filter(User.id == complaint.resolved_by).first() if complaint.resolved_by else None

    def fmt_dt(dt):
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d %H:%M")

    return {
        "id": complaint.id,
        "user_id": complaint.user_id,
        "username": submitter.username if submitter else None,
        "full_name": submitter.full_name if submitter else None,
        "faculty": complaint.faculty,
        "course_code": complaint.course_code,
        "subject": complaint.subject,
        "message": complaint.message,
        "status": complaint.status,
        "admin_note": complaint.admin_note,
        "created_at": fmt_dt(complaint.created_at),
        "resolved_at": fmt_dt(complaint.resolved_at),
        "resolved_by": resolver.username if resolver else None,
    }


# ----------------------------- Root -----------------------------
@app.get("/", tags=["meta"])
def root():
    return {"status": "ok", "service": "ResolvIt API", "version": "2.0.0"}