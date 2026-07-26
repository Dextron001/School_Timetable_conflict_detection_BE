"""Seed users and a baseline set of courses.

Times are stored in 24-hour 'HH:MM' format, matching the institution pattern:
1-hour lecture slots with a lunch break at 12–1pm.

Faculty-based structure:
  FPAS = Faculty of Pure and Applied Sciences  (CSC, SEN, CYB, BCH, MCB, EEE)
  FSMS = Faculty of Social and Management Sciences (ECO, LAW, MAS, ACC, BUS)
"""
import random

from sqlalchemy.orm import Session

from .auth import hash_password
from .models import CourseItem, User

# ── Faculties ──────────────────────────────────────────────────────────────
FACULTIES = {
    "FPAS": {
        "name": "Faculty of Pure and Applied Sciences",
        "departments": ["CSC", "SEN", "CYB", "BCH", "MCB", "EEE"],
    },
    "FSMS": {
        "name": "Faculty of Social and Management Sciences",
        "departments": ["ECO", "LAW", "MAS", "ACC", "BUS"],
    },
}

# Reverse lookup: department code → faculty code
DEPT_TO_FACULTY: dict[str, str] = {}
for _fac_code, _fac_data in FACULTIES.items():
    for _dept_code in _fac_data["departments"]:
        DEPT_TO_FACULTY[_dept_code] = _fac_code

# ── Time slots (1-hour, 8am–5pm, no teaching at 12–1pm) ──────────────────
TIME_SLOTS = [
    ("08:00", "09:00"),
    ("09:00", "10:00"),
    ("10:00", "11:00"),
    ("11:00", "12:00"),
    # 12:00-13:00 = BREAK (not a teaching slot)
    ("13:00", "14:00"),
    ("14:00", "15:00"),
    ("15:00", "16:00"),
    ("16:00", "17:00"),
]

BREAK_SLOT = ("12:00", "13:00")  # lunch break — no courses scheduled here

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# ── Venues (faculty-specific + shared) ────────────────────────────────────
FACULTY_VENUES = {
    "FPAS": [
        "FPAS CSC LH", "FPAS CSC1 LH", "FPAS CSC2 LH",
        "FPAS BCH LH", "FPAS MCB LH", "FPAS MCB LAB",
        "FPAS PHY LH", "FPAS PHY LAB", "FPAS CYB LH",
        "FPAS LH 101", "FPAS 001 LH", "FPAS SEN LH",
        "NH LAB", "Auditorium",
    ],
    "FSMS": [
        "FSMS LH 101", "FSMS LH 102", "FSMS ECO LH",
        "FSMS LAW LH", "FSMS MAS LH", "FSMS ACC LH",
        "FSMS BUS LH", "FSMS AUD",
        "NH LAB", "Auditorium",
    ],
}

# Combined list (used by seed_courses for initial random assignment)
VENUES = FACULTY_VENUES["FPAS"] + [
    v for v in FACULTY_VENUES["FSMS"] if v not in FACULTY_VENUES["FPAS"]
]

# ── Department pools (courses & lecturers per department) ──────────────────
DEPARTMENT_POOLS = {
    "CSC": {
        "name": "Computer Science",
        "courses": ["Data Structures", "Artificial Intelligence", "Compiler Construction",
                    "Computer Simulations", "System Analysis", "Digital Logic Design",
                    "Operating Systems", "Expert Systems", "Database Management",
                    "Game Development", "Computer Networks", "Software Engineering"],
        "lecturers": ["Mr Andrew", "Mrs Bukola", "Mr Taiwo", "Mr Grayson", "Mrs Jade",
                      "Mr Olubiyi", "Mr Adisa", "Mr Richard", "Mrs Oyewale", "Mr Adekunle"],
    },
    "SEN": {
        "name": "Software Engineering",
        "courses": ["Software Requirements Engineering", "Software Design & Architecture",
                    "Object-Oriented Programming", "Web Application Development",
                    "Software Testing & QA", "Agile & DevOps", "Mobile App Development",
                    "Database Systems", "Software Project Management", "Human-Computer Interaction",
                    "Distributed Systems", "Cloud Computing"],
        "lecturers": ["Mr. David Okon", "Mrs. Sandra Ike", "Dr. Tobi Aluko",
                      "Mr. Chidi Umeh", "Prof. Lola Adeniran"],
    },
    "CYB": {
        "name": "Cyber Security",
        "courses": ["Introduction to Cyber Security", "Network Security", "Cryptography",
                    "Ethical Hacking", "Digital Forensics", "Information Security Management",
                    "Malware Analysis", "Secure Software Development", "Cloud Security",
                    "Incident Response", "Penetration Testing", "Security Governance & Compliance"],
        "lecturers": ["Dr. Ahmed Bello", "Mrs. Joy Eke", "Mr. Kelvin Obi",
                      "Dr. Funke Ojo", "Prof. Hassan Ibrahim"],
    },
    "BCH": {
        "name": "Biochemistry",
        "courses": ["General Biochemistry", "Enzymology", "Metabolism", "Molecular Biology",
                    "Clinical Biochemistry", "Bioenergetics", "Protein Chemistry",
                    "Nucleic Acid Biochemistry", "Membrane Biochemistry", "Immunochemistry",
                    "Pharmaceutical Biochemistry", "Plant Biochemistry"],
        "lecturers": ["Prof. Ngozi Obi", "Dr. Emeka Nwankwo", "Mrs. Bola Fashola",
                      "Dr. Yusuf Bello", "Prof. Adaeze Okeke"],
    },
    "MCB": {
        "name": "Microbiology",
        "courses": ["General Microbiology", "Bacteriology", "Virology", "Mycology",
                    "Medical Microbiology", "Industrial Microbiology", "Food Microbiology",
                    "Environmental Microbiology", "Microbial Genetics", "Immunology",
                    "Parasitology", "Pharmaceutical Microbiology"],
        "lecturers": ["Dr. Ifeoma Eze", "Prof. Kunle Adebayo", "Mrs. Hauwa Sani",
                      "Dr. Chibuzo Anyaegbu", "Prof. Femi Olaniyi"],
    },
    "EEE": {
        "name": "Electrical Engineering",
        "courses": ["Circuit Theory", "Electronics I", "Electromagnetic Fields",
                    "Digital Electronics", "Power Systems Analysis", "Control Systems",
                    "Communication Systems", "Microprocessors", "Electrical Machines",
                    "Signal Processing", "Power Electronics", "Instrumentation"],
        "lecturers": ["Engr. Babatunde Ogundimu", "Dr. Ifeanyi Obi", "Prof. Segun Adeleke",
                      "Mrs. Ngozi Ike", "Mr. Kayode Salami"],
    },
    "ECO": {
        "name": "Economics",
        "courses": ["Microeconomics I", "Macroeconomics I", "Statistics for Economists",
                    "Development Economics", "Monetary Economics", "Public Finance",
                    "International Trade", "Econometrics I", "Labour Economics",
                    "Agricultural Economics", "Industrial Economics", "Economic Planning"],
        "lecturers": ["Dr. Emeka Okafor", "Mrs. Funmi Adeyemi", "Prof. Chukwudi Nwachukwu",
                      "Mr. Tunde Fashola", "Dr. Amaka Eze"],
    },
    "LAW": {
        "name": "Law",
        "courses": ["Nigerian Legal System", "Law of Contract", "Constitutional Law",
                    "Criminal Law I", "Law of Torts", "Land Law", "Company Law",
                    "International Law", "Equity & Trusts", "Evidence", "Family Law",
                    "Administrative Law"],
        "lecturers": ["Barr. Adaeze Nwosu", "Prof. Olumide Akintunde", "Dr. Chisom Okonkwo",
                      "Mrs. Yetunde Balogun", "Mr. Emeka Dike"],
    },
    "MAS": {
        "name": "Mass Communication",
        "courses": ["Media Writing", "Broadcast Journalism", "Print Journalism",
                    "Media Law & Ethics", "Public Relations", "Advertising",
                    "Online & Digital Media", "Media Management", "Documentary Production",
                    "Media Research Methods", "Photojournalism", "Development Communication"],
        "lecturers": ["Dr. Aisha Musa", "Prof. Biodun Olawale", "Mrs. Ifeoma Okafor",
                      "Mr. Hakeem Saliu", "Dr. Nneka Oduah"],
    },
    "ACC": {
        "name": "Accounting",
        "courses": ["Financial Accounting I", "Cost Accounting", "Management Accounting",
                    "Auditing & Assurance", "Taxation", "Corporate Reporting",
                    "Public Sector Accounting", "Forensic Accounting", "Accounting Theory",
                    "Financial Management", "Advanced Financial Accounting", "Business Law"],
        "lecturers": ["Dr. Tunde Bakare", "Mrs. Chidinma Eze", "Prof. Sola Adewale",
                      "Mr. Gbenga Adeyemi", "Dr. Patience Udo"],
    },
    "BUS": {
        "name": "Business Administration",
        "courses": ["Principles of Management", "Business Communication", "Organisational Behaviour",
                    "Marketing Management", "Human Resource Management", "Operations Management",
                    "Strategic Management", "Entrepreneurship", "Business Ethics",
                    "Corporate Finance", "Project Management", "International Business"],
        "lecturers": ["Dr. Halima Yusuf", "Prof. Chukwuma Eze", "Mrs. Toyin Bankole",
                      "Mr. Segun Afolayan", "Dr. Amaka Nwosu"],
    },
}

LEVELS = ["100", "200", "300", "400"]


def seed_users(db: Session) -> None:
    if db.query(User).count() > 0:
        return
    users = [
        User(username="admin", full_name="System Administrator",
             hashed_password=hash_password("admin123"), role="admin"),
        User(username="client", full_name="Student User",
             hashed_password=hash_password("client123"), role="client"),
    ]
    db.add_all(users)
    db.commit()


def _make_course(dept: str, level: str, idx: int, pool: dict) -> CourseItem:
    start, end = random.choice(TIME_SLOTS)
    code_num = int(level) + random.randint(1, 98)
    return CourseItem(
        department=dept,
        academic_level=level,
        name=pool["courses"][idx % len(pool["courses"])],
        description=random.choice(VENUES),
        course_code=f"{dept}{code_num}",
        lecturer_name=random.choice(pool["lecturers"]),
        day_of_the_week=random.choice(DAYS),
        time_start=start,
        time_end=end,
    )


def seed_courses(db: Session) -> None:
    # Find which departments already exist in the DB
    existing_depts = {row[0] for row in db.query(CourseItem.department).distinct().all()}

    items: list[CourseItem] = []
    for dept, pool in DEPARTMENT_POOLS.items():
        if dept in existing_depts:
            continue  # already seeded — skip
        for level in LEVELS:
            # 4 courses per dept/level — gives breathing space (gaps) between lectures
            for i in range(4):
                items.append(_make_course(dept, level, i, pool))

    if items:
        db.add_all(items)
        db.commit()


def seed_all(db: Session) -> None:
    seed_users(db)
    seed_courses(db)