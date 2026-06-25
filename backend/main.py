from fastapi import FastAPI, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from fastapi.middleware.cors import CORSMiddleware
import random
from io import BytesIO
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
API_SECRET_KEY = "secure_university_key_2026"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. DATABASE SCHEMA UPDATED WITH DEPT AND LEVEL COLUMNS
class CourseItemDB(Base):
    __tablename__ = "COURSEITEM"
    id = Column(Integer, primary_key=True, index=True)
    department = Column(String, index=True)         
    academic_level = Column(String, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    course_code = Column(String, unique=True, index=True)
    lecturer_name = Column(String)
    day_of_the_week = Column(String)
    time_start = Column(String)
    time_end = Column(String)

class CourseItems(BaseModel):
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

# 2. SEPARATED DEPARTMENTS POOLS
DEPARTMENT_POOLS = {
    "CSC": {
        "courses": ['Data Structure', 'Artificial Intelligence', 'Compiler Construction', 'Computer Simulations', 'IT Hardware', 'Computer Center Management', 'System Analysis', 'Digital Computer Logic Design', 'Computer Hardware', 'Computer Operating Systems', 'Experts Systems', 'Database Management', 'Game Development', 'Data and Object Structuring'],
        "lecturers": ['Mr Andrew', 'Mrs Bukola', 'Mr Taiwo', 'Mr Grayson', 'Mrs Jade', 'Mr Olubiyi', 'Mr Adisa', 'Mr Richard', 'Mrs Oyewale', 'Mr Adekunle']
    },
    "ECO": {
        "courses": ['Introduction to Economics', 'Microeconomics I', 'Macroeconomics I', 'Statistics for Economists', 'Development Economics', 'Monetary Economics', 'Public Finance', 'International Trade', 'Econometrics I', 'Nigerian Economic History', 'Labour Economics', 'Agricultural Economics', 'Industrial Economics', 'Economic Planning'],
        "lecturers": ['Dr. Emeka Okafor', 'Mrs. Funmi Adeyemi', 'Prof. Chukwudi Nwachukwu', 'Mr. Tunde Fashola', 'Dr. Amaka Eze']
    },
    "EEE": {
        "courses": ['Engineering Mathematics I', 'Circuit Theory', 'Electronics I', 'Electromagnetic Fields', 'Digital Electronics', 'Power Systems Analysis', 'Control Systems', 'Communication Systems', 'Microprocessors & Microcontrollers', 'Electrical Machines', 'Signal Processing', 'Power Electronics', 'Instrumentation'],
        "lecturers": ['Engr. Babatunde Ogundimu', 'Dr. Ifeanyi Obi', 'Prof. Segun Adeleke', 'Mrs. Ngozi Ike', 'Mr. Kayode Salami']
    },
    "CVE": {
        "courses": ['Engineering Drawing', 'Strength of Materials', 'Fluid Mechanics', 'Soil Mechanics', 'Structural Analysis', 'Highway Engineering', 'Environmental Engineering', 'Construction Management', 'Water Resources Engineering', 'Geotechnical Engineering', 'Bridge Design', 'Concrete Technology', 'Surveying I'],
        "lecturers": ['Engr. Chidi Okonkwo', 'Dr. Seun Lawal', 'Prof. Musa Abdullahi', 'Mrs. Amara Eze', 'Mr. Femi Coker']
    },
    "LAW": {
        "courses": ['Nigerian Legal System', 'Law of Contract', 'Constitutional Law', 'Criminal Law I', 'Law of Torts', 'Land Law', 'Company Law', 'International Law', 'Equity & Trusts', 'Evidence', 'Family Law', 'Administrative Law', 'Jurisprudence'],
        "lecturers": ['Barrister Adaeze Nwosu', 'Prof. Olumide Akintunde', 'Dr. Chisom Okonkwo', 'Mrs. Yetunde Balogun', 'Mr. Emeka Dike']
    },
    "MED": {
        "courses": ['Human Anatomy I', 'Medical Biochemistry', 'Human Physiology I', 'Pathology I', 'Pharmacology I', 'Microbiology & Parasitology', 'Community Medicine', 'Internal Medicine I', 'Surgery I', 'Obstetrics & Gynaecology', 'Paediatrics', 'Psychiatry', 'Radiology & Imaging'],
        "lecturers": ['Dr. Obinna Chukwu', 'Prof. Kemi Adewale', 'Dr. Uche Osuji', 'Mrs. Folake Ogundipe', 'Dr. Nnamdi Eze']
    },
    "BUS": {
        "courses": ['Principles of Management', 'Business Mathematics', 'Organisational Behaviour', 'Business Communication', 'Marketing Management', 'Financial Management', 'Human Resource Management', 'Operations Management', 'Strategic Management', 'Business Ethics', 'Entrepreneurship', 'Project Management', 'Supply Chain Management'],
        "lecturers": ['Dr. Patience Onyekachi', 'Mr. Lanre Afolabi', 'Prof. Chinwe Obi', 'Mrs. Shade Adebisi', 'Dr. Gbenga Owolabi']
    },
    "ACT": {
        "courses": ['Financial Accounting I', 'Cost Accounting', 'Auditing I', 'Taxation I', 'Management Accounting', 'Public Sector Accounting', 'Advanced Financial Accounting', 'Corporate Reporting', 'Forensic Accounting', 'Business Law for Accountants', 'Financial Statement Analysis', 'Accounting Information Systems', 'Auditing II'],
        "lecturers": ['Mrs. Bisi Oduya', 'Dr. Emeka Igwe', 'Prof. Yinka Adeyinka', 'Mr. Chukwuemeka Onwu', 'Dr. Toyin Akinwande']
    },
    "MCB": {
        "courses": ['General Microbiology', 'Cell Biology', 'Bacteriology I', 'Virology I', 'Mycology', 'Immunology', 'Medical Microbiology', 'Industrial Microbiology', 'Environmental Microbiology', 'Molecular Biology', 'Parasitology', 'Food Microbiology', 'Microbial Genetics'],
        "lecturers": ['Dr. Ngozi Anyanwu', 'Prof. Aliyu Garba', 'Mrs. Chidinma Nwofor', 'Dr. Sola Adeniyi', 'Mr. Tayo Olatunji']
    },
    "MAS": {
        "courses": ['Introduction to Mass Communication', 'Media Writing', 'Broadcast Journalism', 'Print Journalism', 'Media Law & Ethics', 'Public Relations', 'Advertising', 'Online & Digital Media', 'Media Management', 'Developmental Communication', 'Documentary Production', 'Media Research Methods', 'Photojournalism'],
        "lecturers": ['Dr. Aisha Musa', 'Prof. Biodun Olawale', 'Mrs. Ifeoma Okafor', 'Mr. Hakeem Saliu', 'Dr. Nneka Oduah']
    },
    "SOC": {
        "courses": ['Introduction to Sociology', 'Social Research Methods', 'African Sociology', 'Social Psychology', 'Urban Sociology', 'Gender & Society', 'Political Sociology', 'Sociology of Education', 'Social Stratification', 'Sociology of Religion', 'Development Sociology', 'Crime & Deviance', 'Population Studies'],
        "lecturers": ['Prof. Emeka Duru', 'Dr. Funke Adesanya', 'Mrs. Zainab Usman', 'Mr. Chukwudi Agu', 'Dr. Lola Bello']
    }
}

TIME_SLOTS = [
    ('7:00', '8:30'), ('8:30', '10:00'), ('10:00', '11:30'),
    ('11:30', '1:00'), ('1:00', '2:30'), ('2:30', '4:00')        
]

Base.metadata.create_all(bind=engine)

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Access Denied: Invalid Key")

@app.get("/courses/", response_model=list[CourseItems])
async def get_all_course(
    department: str = Query(...), 
    academic_level: str = Query(None),
    db: Session = Depends(get_db), 
    _ = Depends(verify_api_key)
):
    query = db.query(CourseItemDB).filter(
        CourseItemDB.department == department.upper()
    )
    if academic_level:
        query = query.filter(CourseItemDB.academic_level == academic_level)

    courses = query.all()
    return courses

@app.get("/courses/{day_of_the_week}", response_model=list[CourseItems])
async def get_courses_by_day(
    day_of_the_week: str,
    department: str = Query(...),
    academic_level: str = Query(None),
    db: Session = Depends(get_db),
    _ = Depends(verify_api_key)
):
    query = db.query(CourseItemDB).filter(
        CourseItemDB.day_of_the_week == day_of_the_week.capitalize(),
        CourseItemDB.department == department.upper()
    )
    if academic_level:
        query = query.filter(CourseItemDB.academic_level == academic_level)

    courses = query.all()
    return courses


@app.put("/generate/", response_model=list[CourseItems])
async def generate_timetable(
    department: str = Query(...), 
    academic_level: str = Query(...),
    db: Session = Depends(get_db), 
    _ = Depends(verify_api_key)
):
    dept_upper = department.upper()
    if dept_upper not in DEPARTMENT_POOLS:
        raise HTTPException(status_code=400, detail="Invalid department code")

    # Get courses for this department and level
    all_courses = db.query(CourseItemDB).filter(
        CourseItemDB.department == dept_upper,
        CourseItemDB.academic_level == academic_level
    ).all()
    
    pool = DEPARTMENT_POOLS[dept_upper]

    if not all_courses:
        # Auto-populate if none exist
        selected_course_names = random.sample(pool["courses"], k=min(8, len(pool["courses"])))

        for name in selected_course_names:
            random_time = random.choice(TIME_SLOTS)
            random_day = random.choice(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])

            new_course = CourseItemDB(
                department=dept_upper,
                academic_level=academic_level,
                name=name,
                course_code=f"{dept_upper}-TEMP-{random.randint(1000, 9999)}",
                lecturer_name=random.choice(pool["lecturers"]),
                day_of_the_week=random_day,
                time_start=random_time[0],
                time_end=random_time[1]
            )
            db.add(new_course)
        db.commit()

        # Re-fetch all courses for this dept/level
        all_courses = db.query(CourseItemDB).filter(
            CourseItemDB.department == dept_upper,
            CourseItemDB.academic_level == academic_level
        ).all()
    
    # Parse the academic level
    try:
        level_num = int(academic_level)
    except ValueError:
        level_num = 100
    
    # Set the range for ALL course codes based on level
    start_range = level_num
    end_range = level_num + 99
    
    # Generate unique numbers for ALL courses
    unique_numbers = random.sample(range(start_range, end_range + 1), len(all_courses))
    
    # Update course codes for ALL courses first
    for idx, course in enumerate(all_courses):
        course.course_code = f"{dept_upper}{unique_numbers[idx]}"
    
    # Now randomly select which courses to update other fields (3-9 courses)
    number_of_course_to_edit = random.randint(3, min(9, len(all_courses)))
    random_selected = random.sample(all_courses, number_of_course_to_edit)
    
    # Update the selected courses with new data
    for course in random_selected:
        random_time = random.choice(TIME_SLOTS)
        random_day = random.choice(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
        
        course.lecturer_name = random.choice(pool["lecturers"])
        course.name = random.choice(pool["courses"])
        course.day_of_the_week = random_day
        course.time_start = random_time[0]
        course.time_end = random_time[1]
        course.academic_level = academic_level
        course.description = None
        
    db.commit()
    
    # Return ALL courses (all now have correct level codes)
    return all_courses

# 5. RESOLVE ENDPOINT SCOPED BY DEPT AND LEVEL
def time_to_min(time_str: str) -> int:
    hr_str, min_str = time_str.split(":")
    return (int(hr_str) * 60) + int(min_str)

@app.put("/resolve/", response_model=list[CourseItems])
async def fix_all_course_time(
    department: str = Query(...), 
    academic_level: str = Query(...),
    db: Session = Depends(get_db), 
    _ = Depends(verify_api_key)
):
    DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    for day in DAYS_OF_WEEK:
        daily_course = db.query(CourseItemDB).filter(
            CourseItemDB.day_of_the_week == day,
            CourseItemDB.department == department.upper(),
            CourseItemDB.academic_level == academic_level
        ).all()
        
        time_track = []
        for course in daily_course:
            start_min = time_to_min(course.time_start)
            end_min = time_to_min(course.time_end)
            time_track.append((course.id, start_min, end_min))

        for i in time_track:
            id_i, start_i, end_i = i
            for j in time_track:
                id_j, start_j, end_j = j
                if id_i == id_j:
                    continue
                if start_i < end_j and end_i > start_j:
                    for potential_slot in TIME_SLOTS:
                        pot_start = time_to_min(potential_slot[0])
                        pot_end = time_to_min(potential_slot[1])
                        slot_is_busy = False

                        for track in time_track:
                            t_id, t_start, t_end = track
                            if pot_start < t_end and pot_end > t_start:
                                slot_is_busy = True
                                break

                        if not slot_is_busy:
                            for course in daily_course:
                                if course.id == id_j:
                                    course.time_end = potential_slot[1]
                                    course.time_start = potential_slot[0]
                                    break
                            time_track.remove(j)
                            time_track.append((id_j, pot_start, pot_end))
                            break
                    break
    db.commit()
    return db.query(CourseItemDB).filter(
        CourseItemDB.department == department.upper(),
        CourseItemDB.academic_level == academic_level
    ).all()

# 6. EXPORT PDF SCOPED BY DEPT AND LEVEL
@app.get("/export-pdf/")
async def export_timetable_pdf(
    department: str = Query(...),
    academic_level: str = Query(None),
    db: Session = Depends(get_db),
    _ = Depends(verify_api_key)
):
    query = db.query(CourseItemDB).filter(CourseItemDB.department == department.upper())
    if academic_level:
        query = query.filter(CourseItemDB.academic_level == academic_level)
    courses = query.all()
    if not courses:
        raise HTTPException(status_code=404, detail="No course records found for this department")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#1e293b'), spaceAfter=4)
    meta_style = ParagraphStyle('DocMeta', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#475569'), spaceAfter=15)
    
    story.append(Paragraph(f"OFFICIAL ACADEMIC TIMETABLE: DEPT OF {department.upper()}", title_style))
    story.append(Paragraph("Academic Session: 2025/2026 | First Semester Allocation Matrix", meta_style))
    story.append(Spacer(1, 10))
    
    DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for day in DAYS_OF_WEEK:
        day_courses = [c for c in courses if c.day_of_the_week == day]
        if not day_courses:
            continue
            
        day_heading_style = ParagraphStyle(f'DayHead_{day}', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#0f172a'), spaceBefore=12, spaceAfter=6)
        story.append(Paragraph(f"{day.upper()} ALLOCATIONS", day_heading_style))
        
        table_data = [['Duration Block', 'Course Structure', 'Location Space', 'Assigned Personnel']]
        for c in day_courses:
            course_level = f"{c.academic_level} Level" if c.academic_level else "N/A"
            
            table_data.append([
                f"{c.time_start} - {c.time_end}",
                f"{c.course_code}: {c.name} ({course_level})",
                c.description if c.description else 'General Facility Space',
                c.lecturer_name
            ])
            
        t = Table(table_data, colWidths=[110, 240, 180, 170])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8fafc')),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={department}_Timetable.pdf"})