"""Seed users and a baseline set of courses with unit-based scheduling.

Real course data for CSC, SEN, CYB (FPAS) and IRS, MCM, ECO, ACC, BUS (FSMS)
from PCU CCMAS curriculum and course allocation documents.

Times are stored in 24-hour 'HH:MM' format, matching the institution pattern.
Multi-unit courses:
  - 3-unit: 3 hours/week → session A (2hr block on one day) + session B (1hr on another day)
  - 2-unit: 2 hours/week → one 2-hour block on one day
  - 1-unit: 1 hour/week → one 1-hour slot
  - 1-unit: 1 hour/week → one 1-hour slot

Faculty-based structure:
  FPAS = Faculty of Pure and Applied Sciences  (CSC, SEN, CYB, BCH, MCB, PHY)
  FSMS = Faculty of Social and Management Sciences (IRS, MCM, ECO, ACC, BUS)
"""
import random

from sqlalchemy.orm import Session

from .auth import hash_password
from .models import CourseItem, User

# ── Faculties ──────────────────────────────────────────────────────────────
FACULTIES = {
    "FPAS": {
        "name": "Faculty of Pure and Applied Sciences",
        "departments": ["CSC", "SEN", "CYB", "BCH", "MCB", "PHY"],
    },
    "FSMS": {
        "name": "Faculty of Social and Management Sciences",
        "departments": ["IRS", "MCM", "ECO", "ACC", "BUS"],
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

BREAK_SLOT = ("12:00", "13:00")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# ── Venues (faculty-specific + shared) ────────────────────────────────────
FACULTY_VENUES = {
    "FPAS": [
        "FPAS CSC LH", "FPAS CSC1 LH", "FPAS CSC2 LH",
        "FPAS BCH LH", "FPAS BCH LAB", "FPAS MCB LH", "FPAS MCB LAB",
        "FPAS PHY LH", "FPAS PHY LAB", "FPAS CYB LH",
        "FPAS LH 101", "FPAS LH 102", "FPAS LH 103", "FPAS 001 LH", "FPAS SEN LH",
        "NH LAB", "NW HORIZON LB", "Auditorium",
    ],
    "FSMS": [
        "FSMS LH 101", "FSMS LH 102", "FSMS LH 103",
        "FSMS ECO LH", "FSMS IRS LH", "FSMS MCM LH",
        "FSMS ACC LH", "FSMS BUS LH", "FSMS AUD",
        "NH LAB", "Auditorium",
    ],
}

VENUES = FACULTY_VENUES["FPAS"] + [
    v for v in FACULTY_VENUES["FSMS"] if v not in FACULTY_VENUES["FPAS"]
]

# ── Department pools (courses & lecturers per department) ──────────────────
DEPARTMENT_POOLS = {
    "CSC": {
        "name": "Computer Science",
        "courses": [""],  # not used for real-data depts
        "lecturers": ["Mr Andrew", "Mrs Bukola", "Mr Taiwo", "Mr Grayson", "Mrs Jade",
                      "Mr Olubiyi", "Mr Adisa", "Mr Richard", "Mrs Oyewale", "Mr Adekunle"],
    },
    "SEN": {
        "name": "Software Engineering",
        "courses": [""],
        "lecturers": ["Mr. David Okon", "Mrs. Sandra Ike", "Dr. Tobi Aluko",
                      "Mr. Chidi Umeh", "Prof. Lola Adeniran"],
    },
    "CYB": {
        "name": "Cyber Security",
        "courses": [""],
        "lecturers": ["Dr. Ahmed Bello", "Mrs. Joy Eke", "Mr. Kelvin Obi",
                      "Dr. Funke Ojo", "Prof. Hassan Ibrahim"],
    },
    "BCH": {
        "name": "Biochemistry",
        "courses": [""],
        "lecturers": ["Prof. Ngozi Obi", "Dr. Emeka Nwankwo", "Mrs. Bola Fashola",
                      "Dr. Yusuf Bello", "Prof. Adaeze Okeke"],
    },
    "MCB": {
        "name": "Microbiology",
        "courses": [""],
        "lecturers": ["Dr. Ifeoma Eze", "Prof. Kunle Adebayo", "Mrs. Hauwa Sani",
                      "Dr. Chibuzo Anyaegbu", "Prof. Femi Olaniyi"],
    },
    "PHY": {
        "name": "Physics",
        "courses": [""],
        "lecturers": ["Mr. Adedamola Agbelemoge", "Dr. Olatunde Ogunwande", "Prof. Adebayo Adekoya",
                      "Mrs. Funke Ogunleye", "Dr. Segun Oladipo"],
    },
    "IRS": {
        "name": "International Relations",
        "courses": [""],
        "lecturers": ["Dr. Adebayo Fasanya", "Prof. Chukwuemeka Eze", "Mrs. Folake Adeniyi",
                      "Mr. Ibrahim Musa", "Dr. Ngozi Okafor"],
    },
    "MCM": {
        "name": "Mass Communication",
        "courses": [""],
        "lecturers": ["Dr. Aisha Musa", "Prof. Biodun Olawale", "Mrs. Ifeoma Okafor",
                      "Mr. Hakeem Saliu", "Dr. Nneka Oduah"],
    },
    "ECO": {
        "name": "Economics",
        "courses": [""],
        "lecturers": ["Dr. Emeka Okafor", "Mrs. Funmi Adeyemi", "Prof. Chukwudi Nwachukwu",
                      "Mr. Tunde Fashola", "Dr. Amaka Eze"],
    },
    "ACC": {
        "name": "Accounting",
        "courses": [""],
        "lecturers": ["Dr. Tunde Bakare", "Mrs. Chidinma Eze", "Prof. Sola Adewale",
                      "Mr. Gbenga Adeyemi", "Dr. Patience Udo"],
    },
    "BUS": {
        "name": "Business Administration",
        "courses": [""],
        "lecturers": ["Dr. Sodeinde", "Mrs. Kutu", "Mr. Abolade",
                      "Dr. Mrs. Adegoke", "Mr. Segun Afolayan"],
    },
}

LEVELS = ["100", "200", "300", "400"]

# ── Real course data from PCU CCMAS curriculum ────────────────────────────
# Format: (course_code, course_title, units)
# Service courses shared across departments are included under each department
# since they represent different student cohorts.

REAL_COURSES = {
    # ═══════════════════════════════════════════════════════════════════════
    # FPAS — CSC, SEN, CYB  (from CCMAS PDFs)
    # ═══════════════════════════════════════════════════════════════════════
    "CSC": {
        "100": [
            ("PHY 101", "General Physics I", 2),
            ("PHY 107", "General Practical Physics I", 1),
            ("MTH 101", "Elementary Mathematics I", 2),
            ("STAT 101", "Descriptive Statistics", 3),
            ("COS 101", "Introduction to Computer Sciences", 3),
            ("PCU-COS 103", "Introduction to Front End Programming I", 2),
            ("PCU-COS 105", "Living Online I", 2),
            ("PCU-COS 107", "Introduction of Software Packages I", 2),
            ("GNS 101", "Use of English and Library Skill", 2),
            ("GNS 103", "Nigerian People and Culture", 2),
            ("HDS 101", "Principles and Parameters of Life", 1),
            ("PHY 102", "General Physics II", 2),
            ("PHY 108", "General Practical Physics II", 1),
            ("MTH 102", "Elementary Mathematics II", 2),
            ("COS 102", "Introduction to Problem Solving II", 3),
            ("PCU-COS 104", "Introduction to Front End Programming II", 2),
            ("PCU-COS 106", "Living Online II", 2),
            ("PCU-COS 108", "Introduction to Software Packages II", 2),
            ("PCU-COS 110", "Overview of Computing Technology", 2),
            ("HDS 102", "Principles of Dominion", 1),
        ],
        "200": [
            ("COS 201", "Computer Programming I", 3),
            ("CSC 203", "Discrete Structures", 2),
            ("MTH 201", "Mathematical Methods I", 2),
            ("IFT 211", "Digital Logic Design", 2),
            ("SEN 201", "Introduction to Software Engineering", 2),
            ("HDS 201", "Leadership Development", 1),
            ("PCU-CSC 205", "Introduction to Back-End Programming", 2),
            ("GNS 203", "Peace Studies and Conflict Resolution", 2),
            ("ENT 211", "Enterpreneurship and Innovation", 2),
            ("CYB 201", "Introduction to Cybersecurity & Strategy", 2),
            ("COS 202", "Computer Programming II", 3),
            ("INS 204", "System Analysis and Design", 3),
            ("MTH 202", "Mathematical Methods II", 2),
            ("IFT 212", "Computer Architecture and Organisation", 2),
            ("PCU-CSC 206", "Introduction to Back-End Programming II", 2),
            ("GST 212", "Philosophy Logic and Human Existence", 2),
            ("HDS 202", "Health Education", 1),
            ("PCU-CSC 204", "Fundamentals of Computer Hardware", 3),
        ],
        "300": [
            ("ENT 312", "Venture Creation", 2),
            ("COS 301", "Data Structure", 3),
            ("CSC 308", "Operating Systems", 3),
            ("CSC 309", "Artificial Intelligence", 2),
            ("CSC 322", "Computer Sci. Innovation & New Technology", 2),
            ("DTS 304", "Data Management I", 3),
            ("ICT 305", "Data Communication System & Network", 3),
            ("CYB 305", "Digital Forensics & Investigation Methods", 2),
        ],
        "400": [
            ("COS 409", "Research Method and Technical Report", 2),
            ("CSC 401", "Algorithms and Complexity Analysis", 2),
            ("INS 401", "Project Management", 2),
            ("PCU-CSC 404", "Special Topics in Computer Science (Seminar)", 3),
            ("PCU-CSC 403", "Cloud Computing", 3),
            ("PCU-CSC 405", "Big Data Analytics", 3),
            ("PCU-CSC 411", "Current Trends in Artificial Intelligence", 3),
            ("CSC 402", "Object-Oriented Programming", 2),
            # CSC 498 (Project, 6-unit) excluded — not a timetabled course
            ("PCU-CSC 406", "Fundamentals of IoT", 2),
            ("PCU-CSC 410", "Fundamentals of Edge Computing", 2),
            ("PCU-CSC 412", "Logic Programming", 3),
        ],
    },
    "SEN": {
        "100": [
            ("PHY 101", "General Physics I", 2),
            ("PHY 107", "General Practical Physics I", 1),
            ("MTH 101", "Elementary Mathematics I", 2),
            ("STAT 101", "Descriptive Statistics", 3),
            ("COS 101", "Introduction to Computer Sciences", 3),
            ("PCU-COS 103", "Introduction to Front End Programming I", 2),
            ("PCU-COS 105", "Living Online I", 2),
            ("PCU-COS 107", "Introduction of Software Packages I", 2),
            ("GNS 101", "Use of English and Library Skill", 2),
            ("GNS 103", "Nigerian People and Culture", 2),
            ("HDS 101", "Principles and Parameters of Life", 1),
            ("PHY 102", "General Physics II", 2),
            ("PHY 108", "General Practical Physics II", 1),
            ("MTH 102", "Elementary Mathematics II", 2),
            ("COS 102", "Introduction to Problem Solving II", 3),
            ("PCU-COS 104", "Introduction to Front End Programming II", 2),
            ("PCU-COS 106", "Living Online II", 2),
            ("PCU-COS 108", "Introduction to Software Packages II", 2),
            ("PCU-COS 110", "Overview of Computing Technology", 2),
            ("HDS 102", "Principles of Dominion", 1),
        ],
        "200": [
            ("COS 201", "Computer Programming I", 3),
            ("CSC 203", "Discrete Structures", 2),
            ("SEN 201", "Introduction to Software Engineering", 2),
            ("MTH 201", "Mathematical Methods I", 2),
            ("PCU-SEN 205", "Software Engineering Process", 2),
            ("IFT 211", "Digital Logic Design", 2),
            ("ENT 211", "Enterpreneurship and Innovation", 2),
            ("PCU-CSC 205", "Introduction to Backend Programming I", 2),
            ("PCU-SEN 203", "Software Requirements Engineering", 3),
            ("COS 202", "Computer Programming II", 3),
            ("INS 204", "System Analysis and Design", 3),
            ("IFT 212", "Computer Architecture and Organisation", 2),
            ("PCU-CSC 206", "Introduction to Backend Programming II", 2),
            ("PCU-CYB 206", "Fundamentals of Open-Source Intelligence II", 2),
            ("GST 212", "Philosophy Logic and Human Existence", 2),
            ("MTH 202", "Mathematical Method II", 2),
            ("HDS 202", "Health Education", 1),
        ],
        "300": [
            ("SEN 301", "Object Oriented Analysis and Design", 2),
            ("SEN 304", "Software Testing & Quality Assurance", 2),
            ("SEN 306", "Software Construction", 2),
            ("SEN 322", "Software Engineering Innovation & New Technology", 2),
            ("CSC 301", "Data Structure", 3),
            ("CSC 308", "Operating Systems", 3),
            ("PCU-SEN 309", "Introduction to Agile Software Methodology", 3),
            ("ENT 312", "Venture Creation", 2),
        ],
        "400": [
            ("COS 409", "Research Methodology & Technical Report Writing", 3),
            ("INS 401", "Project Management", 2),
            ("SEN 401", "Software Architecture and Design", 2),
            ("PCU-SEN 403", "Software Engineering Economics", 2),
            ("PCU-SEN 405", "Software Engineering Group Project", 3),
            ("PCU-COS 411", "Current Trends in Artificial Intelligence", 3),
            ("SEN 410", "Software Architecture & Design", 2),
            # SEN 498 (Final Year Student Project II, 6-unit) excluded — not a timetabled course
            ("PCU-SEN 402", "Open Source Software Development & Application", 3),
            ("PCU-SEN 404", "Software Architecture & Design", 3),
            ("PCU-SEN 406", "Global Best Practices in Software Engineering", 2),
            ("PCU-SEN 408", "Overview of DevOps Engineering", 2),
            ("PCU-SEN 412", "Mobile Application Development Technologies", 2),
        ],
    },
    "CYB": {
        "100": [
            ("PHY 101", "General Physics I", 2),
            ("PHY 107", "General Practical Physics I", 1),
            ("MTH 101", "Elementary Mathematics I", 2),
            ("STAT 101", "Descriptive Statistics", 3),
            ("COS 101", "Introduction to Computer Sciences", 3),
            ("PCU-COS 103", "Introduction to Front End Programming I", 2),
            ("PCU-COS 105", "Living Online I", 2),
            ("PCU-COS 107", "Introduction of Software Packages I", 2),
            ("GNS 101", "Use of English and Library Skill", 2),
            ("GNS 103", "Nigerian People and Culture", 2),
            ("HDS 101", "Principles and Parameters of Life", 1),
            ("PHY 102", "General Physics II", 2),
            ("PHY 108", "General Practical Physics II", 1),
            ("MTH 102", "Elementary Mathematics II", 2),
            ("COS 102", "Introduction to Problem Solving II", 3),
            ("PCU-COS 104", "Introduction to Front End Programming II", 2),
            ("PCU-COS 106", "Living Online II", 2),
            ("PCU-COS 108", "Introduction to Software Packages II", 2),
            ("PCU-COS 110", "Overview of Computing Technology", 2),
            ("HDS 102", "Principles of Dominion", 1),
        ],
        "200": [
            ("COS 201", "Computer Programming I", 3),
            ("CYB 201", "Introduction to Cybersecurity & Strategy", 2),
            ("CYB 203", "Cybercrime Law & Countermeasures", 2),
            ("SEN 201", "Introduction to Software Engineering", 2),
            ("HDS 201", "Leadership Development", 1),
            ("GNS 203", "Peace Studies and Conflict Resolution", 2),
            ("PCU-CYB 207", "Wireshark for Ethical Hacking", 3),
            ("PCU-CYB 209", "Fundamentals of Android Security", 2),
            ("ENT 211", "Enterpreneurship & Innovation", 2),
            ("GST 212", "Philosophy Logic and Human Existence", 2),
            ("COS 202", "Computer Programming II", 3),
            ("INS 204", "System Analysis and Design", 3),
            ("PCU-CYB 208", "Security Operations Center Management", 3),
            ("PCU-CYB 210", "Essentials of Windows Penetration Testing", 2),
            ("HDS 202", "Health Education", 1),
            ("PCU-CYB 212", "Overview of Identity & Access Management", 2),
        ],
        "300": [
            ("CYB 301", "Cryptography Techniques", 2),
            ("CYB 303", "Cybersecurity Risks Analysis", 2),
            ("CYB 305", "Digital Forensics & Investigation Methods", 2),
            ("CYB 302", "Biometric Security", 2),
            ("CYB 309", "Systems Security", 2),
            ("CYB 304", "Information & Big Data Security", 2),
            ("CYB 322", "Cybersecurity Innovation & New Technology", 2),
            ("ENT 312", "Venture Creation", 2),
            ("PCU-CYB 313", "Overview of Network Security Protocol", 3),
        ],
        "400": [
            ("CYB 401", "Systems Vulnerability Assessment & Testing", 2),
            ("CYB 403", "Cyber Threat Intelligence & Cyber Conflict", 2),
            ("CYB 405", "Ethical Hacking & Reverse Engineering", 2),
            ("COS 409", "Systems Vulnerability Assessment & Testing", 2),
            ("PCU-CYB 407", "Special Topics in Cybersecurity", 3),
            ("PCU-CSC 411", "Current Trends in Artificial Intelligence", 3),
            ("CYB 402", "Steganography-Access Methods & Data Hiding", 2),
            ("CYB 404", "Cloud Computing Security", 2),
            ("CYB 406", "Deep and Dark Web Security", 2),
            ("PCU-CYB 408", "Security Wireless & Mobile Network", 3),
            ("PCU-CYB 410", "Cybersecurity Analytics and Big Data", 2),
            # CYB 498 (Final Year Student Project, 6-unit) excluded — not a timetabled course
            ("PCU-CYB 412", "Cybersecurity for Critical Infrastructure", 2),
            ("PCU-CYB 414", "Cyber Security Group Project", 3),
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # FSMS — IRS, MCM, ECO, ACC, BUS  (from PCU course allocation PDFs)
    # ═══════════════════════════════════════════════════════════════════════
    "IRS": {
        "100": [
            ("IRS 101", "Ancestors of the Contemporary International System", 2),
            ("IRS 103", "Introduction to African Politics", 2),
            ("IRS 105", "History of Nigeria", 2),
            ("IRS 107", "Introduction to Political Science", 2),
            ("PCU-IRS 101", "Basic French Grammar 1", 2),
            ("PCU-IRS 103", "Concepts in International Relations", 3),
        ],
        "200": [
            ("IRS 203", "Introduction to Political Analysis", 2),
            ("IRS 205", "Political Thought Since Hobbes", 2),
            ("IRS 207", "New States in World Politics", 2),
            ("PCU-IRS 201", "French Grammar and Composition", 3),
            ("PCU-IRS 205", "Elements of Contemporary Global Studies", 3),
        ],
        "300": [
            ("IRS 301", "International Economic Relations", 2),
            ("IRS 303", "The International Political System", 2),
            ("IRS 305", "Law of Nations (International Law)", 2),
            ("IRS 307", "International Politics in the Post-Cold War Era", 2),
            ("IRS 311", "Theory and Practice of Administration", 2),
            ("PCU-IRS 303", "Gender Studies in International Relations", 2),
        ],
        "400": [
            ("IRS 401", "Nigerian Foreign Policy", 3),
            ("IRS 403", "International Politics in the Post-Cold War Era", 3),
            ("IRS 407", "Contemporary Strategic Studies", 3),
            ("IRS 409", "Theories and Practice of Administration", 3),
            ("IRS 413", "Technology, Ecology and Environmental Issues in IR", 2),
            ("IRS 415", "The Middle East in World Politics", 2),
        ],
    },
    "MCM": {
        "100": [
            ("CMS 101", "Introduction to Human Communication", 2),
            ("MCM 103", "Introduction to Advertising", 2),
            ("MCM 105", "Introduction to Book Publishing", 2),
            ("MCM 107", "Introduction to Photojournalism", 2),
        ],
        "200": [
            ("CMS 201", "History of Nigerian Mass Media", 2),
            ("MCM 201", "Critical and Review Writing", 2),
            ("MCM 203", "Feature Writing", 2),
            ("MCM 205", "Technique in Book Publishing", 2),
            ("MCM 207", "Radio/TV News Reporting and Production", 2),
            ("MCM 209", "Drama, Film and Documentary Production", 2),
            ("MCM 211", "Basics of Screenwriting and Film Animation", 2),
            ("MCM 213", "Writing for Public Relations", 2),
            ("MCM 215", "Advertising Media Planning", 2),
            ("PCU-MCM 201", "Editorial Writing", 2),
            ("PCU-MCM 203", "Issues in Nigerian Mass Media", 2),
        ],
        "300": [
            ("MAC 301", "International Communication", 2),
            ("MAC 303", "Newspapers Management & Production", 2),
            ("MAC 305", "Science and Technology Reporting", 2),
            ("MAC 309", "Broadcasting Management and Programming", 2),
            ("MAC 311", "Investigative and Interpretative Reporting", 2),
            ("MAC 313", "Foreign Correspondence", 2),
            ("MAC 315", "General Media Management", 2),
            ("MAC 319", "Film Production", 2),
            ("MCM 313", "Advertising and PR Research", 2),
            ("MCM 315", "Consumer Affairs", 2),
            ("PCU-MCM 303", "Station Management and Operations", 2),
            ("PCU-MCM 307", "Integrated Marketing Communication", 2),
        ],
        "400": [
            ("MAC 401", "Mass Media Laws & Ethics", 3),
            ("MAC 403", "Data Analysis in Communication Research", 3),
            ("MAC 405", "Issues in Broadcasting", 2),
            ("MAC 407", "Station Management and Operations", 2),
            ("MAC 409", "Economic and Social Issues in Advertising & PR", 2),
            ("MAC 413", "International Advertising", 2),
            ("MAC 415", "Integrated Marketing Communication", 2),
            ("MAC 417", "Public Relations Case Studies", 2),
        ],
    },
    "ECO": {
        "100": [
            ("ECO 101", "Principles of Economics", 2),
        ],
        "200": [
            ("ECO 201", "Introduction to Microeconomics", 2),
            ("ECO 203", "Introduction to Macroeconomics", 2),
            ("ECO 205", "Structure of the Nigerian Economy I", 2),
            ("ECO 207", "Mathematics for Economics", 2),
            ("PCU-ECO 201", "Economics of Production", 2),
            ("PCU-ECO 203", "Urban and Regional Planning", 2),
        ],
        "300": [
            ("ECO 301", "Intermediate Microeconomics", 2),
            ("ECO 303", "Intermediate Macroeconomics", 2),
            ("ECO 305", "History of Economic Thought", 2),
            ("ECO 307", "Project Evaluation", 2),
            ("ECO 309", "Economics of Innovation", 2),
            ("PCU-ECO 301", "Environmental Economics", 2),
            ("PCU-ECO 303", "Introduction to Migration", 2),
        ],
        "400": [
            ("ECO 401", "Advanced Microeconomics", 2),
            ("ECO 403", "Advanced Macroeconomics", 2),
            ("ECO 405", "Comparative Economic System", 2),
            ("ECO 407", "Taxation and Fiscal Policy", 2),
            ("ECO 411", "Applied Econometrics I", 2),
            ("ECO 413", "Seminar in Economics", 1),
            ("ECO 415", "Public Policy Analysis", 2),
            ("ECO 419", "Petroleum Economics", 2),
            ("SSC 301", "Innovation in Social Sciences", 2),
        ],
    },
    "ACC": {
        "100": [
            ("ACC 101", "Introduction to Financial Accounting", 2),
            ("AMS 101", "Principles of Management", 2),
            ("AMS 103", "Introduction to Computing", 2),
            ("GNS 111", "Communication in English & Uses of Library", 2),
            ("PCU-BUA 101", "Introduction to Business Management", 3),
            ("PCU-ACC 103", "Introduction to Accounting", 1),
            ("PCU-HDS 101", "Principles & Parameter of Life", 1),
            ("PCU-ECO 101", "Principle of Economics", 2),
            ("PCU-GNS 103", "Nigeria Peoples & Culture", 2),
            ("PCU-SMC 103", "Introduction to Psychology", 2),
        ],
        "200": [
            ("ENT 201", "Entrepreneurship and Innovation", 2),
            ("ACC 201", "Financial Accounting and Reporting", 2),
            ("ACC 203", "Cost Accounting", 2),
            ("PCU-BUA 203", "Business Statistics", 2),
            ("PCU-BUA 205", "Introduction to Microeconomics", 2),
            ("PCU-ACC 205", "PCU Accounting Course I", 2),
            ("PCU-ACC 207", "PCU Accounting Course II", 2),
            ("PCU-GNS 203", "Peace Studies and Conflict Resolution", 2),
            ("PCU-HDS 201", "Leadership Development", 1),
        ],
        "300": [
            ("ACC 301", "Corporate Accounting", 3),
            ("ACC 303", "Management Accounting", 3),
            ("ACC 305", "Auditing and Assurance", 3),
            ("ACC 307", "Taxation", 3),
            ("ACC 311", "Public Sector Accounting", 3),
            ("PCU-BUA 303", "Business Ethics", 3),
            ("PCU-HDS 301", "Principles of Dominion", 1),
            ("PCU-ACC 309", "Advanced Accounting Practice", 3),
        ],
        "400": [
            ("ACC 401", "Advanced Financial Accounting", 2),
            ("ACC 403", "Advanced Auditing", 2),
            ("ACC 405", "Corporate Reporting", 2),
            ("ACC 407", "Forensic Accounting", 2),
            ("ACC 409", "Accounting Theory", 2),
            ("ACC 411", "International Accounting", 2),
            ("ACC 413", "Seminar in Accounting", 2),
            ("BUS 401", "Analysis for Business Decision", 3),
            ("BUS 403", "Business Policy and Strategic Management", 3),
        ],
    },
    "BUS": {
        "100": [
            ("GST 111", "Communication in English & Uses of Library", 2),
            ("AMS 101", "Principles of Management", 2),
            ("AMS 103", "Introduction to Computing", 2),
            ("BUA 101", "Introduction to Business Management", 3),
            ("PCU-ACC 101", "Introduction to Accounting", 3),
            ("PCU-ECO 101", "Principle of Economics", 2),
            ("PCU-BUA 103", "Introduction to Business Finance", 2),
            ("PCU-HDS 101", "Principles & Parameter of Life", 1),
            ("PCU-SMC 103", "Introduction to Psychology", 2),
            ("GNS 101", "Communication in English", 2),
            ("GNS 103", "Nigeria Peoples & Culture", 2),
        ],
        "200": [
            ("ENT 211", "Entrepreneurship and Innovation", 2),
            ("BUA 201", "Principles of Business Administration I", 3),
            ("BUA 203", "Business Statistics", 3),
            ("BUA 205", "Leadership and Governance", 3),
            ("PCU-BUA 201", "Principles of Marketing", 2),
            ("PCU-BUA 205", "Introduction to Microeconomics", 2),
            ("PCU-ACC 201", "Financial Accounting and Reporting", 2),
            ("PCU-GNS 203", "Peace Studies and Conflict Resolution", 2),
            ("HDS 201", "Leadership Development", 1),
        ],
        "300": [
            ("BUA 303", "Management Theory", 3),
            ("BUA 305", "Financial Management", 3),
            ("BUA 313", "Innovation Management", 3),
            ("BUA 319", "E-Commerce", 3),
            ("BUA 321", "Business Start-up", 2),
            ("BUA 323", "Supply Chain Management", 3),
            ("PCU-BUA 327", "Business Law", 2),
            ("PCU-BUA 303", "Business Ethics", 1),
        ],
        "400": [
            ("BUS 401", "Analysis for Business Decision", 3),
            ("BUS 403", "Business Policy and Strategic Management", 3),
            ("BUS 405", "Seminar in Business Administration", 1),
            ("BUS 407", "Human and Organizational Behaviour I", 2),
            ("BUS 409", "Advance Management Theory", 3),
            ("GST 403", "Quick Book", 1),
            ("MKT 401", "Marketing Management", 3),
            ("MKT 403", "Logistics and Supply Chain Management", 3),
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # FPAS — MCB  (from First Semester Microbiology & Biochemistry PDF)
    # ═══════════════════════════════════════════════════════════════════════
    "MCB": {
        "100": [
            ("BIO 101", "General Biology I", 3),
            ("BIO 103", "General Biology Laboratory I", 1),
            ("BTG 101", "Introduction to Biotechnology", 1),
            ("MTH 101", "General Mathematics I", 3),
            ("PHY 101", "General Physics I", 3),
            ("PHY 107", "General Physics Laboratory I", 1),
            ("CHM 101", "General Chemistry I", 3),
            ("CHM 103", "General Chemistry Laboratory I", 1),
            ("HDS 101", "Principles and Parameters of Life", 1),
            ("GNS 101", "Communication in English", 2),
            ("GNS 103", "Nigerian People's and Culture", 2),
        ],
        "200": [
            ("MCB 201", "General Microbiology", 3),
            ("BCH 201", "General Biochemistry I", 3),
            ("CHM 201", "Inorganic Chemistry I", 3),
            ("CHM 203", "Organic Chemistry I", 3),
            ("CHM 205", "Physical Chemistry I", 3),
            ("STA 201", "Statistics for Biological Sciences", 4),
            ("GNS 201", "Entrepreneurship", 2),
            ("GNS 203", "Peace Studies and Conflict Resolution", 2),
            ("HDS 201", "Leadership Development", 1),
            ("GST 205", "Office Productivity", 1),
        ],
        "300": [
            ("MCB 301", "Immunology", 3),
            ("MCB 303", "Food Microbiology", 3),
            ("MCB 305", "Biodeterioration", 2),
            ("MCB 307", "Mycology", 3),
            ("ZOO 301", "Biology of Tropical Parasites", 3),
            ("STA 315", "Scientific Writing and Presentation", 2),
            ("CSC 301", "Computer Appreciation", 3),
            ("HDS 301", "Managing Relationships", 1),
            ("GST 301", "Python Programming (Introduction)", 1),
            ("BCH 301", "Amino Acids & Protein: Chemistry & Metabolism", 2),
            ("BCH 303", "Carbohydrates: Chemistry & Metabolism", 2),
        ],
        "400": [
            ("MCB 401", "Seminar", 3),
            ("MCB 403", "Virology & Tissue Culture", 3),
            ("MCB 405", "Advanced Food Microbiology", 3),
            ("MCB 407", "Petroleum Microbiology", 3),
            ("MCB 409", "Pathogenic Microbiology", 3),
            ("MCB 411", "Microbiological Quality Control & Assurance", 2),
            ("MCB 413", "Bacteria Diversity", 3),
            ("ZOO 405", "Principles of Parasitology", 4),
            ("GST 405", "Project Management I", 1),
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # FPAS — BCH  (from First Semester Microbiology & Biochemistry PDF)
    # ═══════════════════════════════════════════════════════════════════════
    "BCH": {
        "100": [
            ("BIO 101", "General Biology I", 3),
            ("BIO 103", "General Biology Laboratory I", 1),
            ("BTG 101", "Introduction to Biotechnology", 1),
            ("MTH 101", "General Mathematics I", 3),
            ("PHY 101", "General Physics I", 3),
            ("PHY 107", "General Physics Laboratory I", 1),
            ("CHM 101", "General Chemistry I", 3),
            ("CHM 103", "General Chemistry Laboratory I", 1),
            ("HDS 101", "Principles and Parameters of Life", 1),
            ("GNS 101", "Communication in English", 2),
            ("GNS 103", "Nigerian People's and Culture", 2),
        ],
        "200": [
            ("BCH 201", "General Biochemistry I", 3),
            ("CHM 201", "Inorganic Chemistry I", 3),
            ("CHM 203", "Organic Chemistry I", 3),
            ("CHM 205", "Physical Chemistry I", 3),
            ("STA 201", "Statistics for Biological Sciences", 4),
            ("MCB 201", "General Microbiology", 3),
            ("GNS 201", "Entrepreneurship", 2),
            ("GNS 203", "Peace Studies and Conflict Resolution", 2),
            ("HDS 201", "Leadership Development", 1),
            ("GST 205", "Office Productivity", 1),
        ],
        "300": [
            ("BCH 301", "Amino Acids and Proteins: Chemistry and Metabolism", 2),
            ("BCH 303", "Carbohydrates: Chemistry and Metabolism", 2),
            ("BCH 305", "Lipids: Chemistry and Metabolism", 2),
            ("BCH 307", "Nucleic Acids: Genome Organization and Metabolism", 2),
            ("BCH 309", "Enzymology", 3),
            ("BCH 311", "Food and Nutritional Biochemistry", 2),
            ("CHM 303", "Organic Chemistry II", 3),
            ("CSC 301", "Computer Appreciation", 3),
            ("STA 315", "Scientific Writing and Presentation", 2),
            ("HDS 301", "Managing Relationships", 1),
            ("GST 305", "CRMI", 1),
        ],
        "400": [
            ("BCH 401", "Advanced Enzymology", 2),
            ("BCH 403", "Xenobiochemistry", 1),
            ("BCH 405", "Tissue Biochemistry", 1),
            ("BCH 407", "Biosynthesis of Macromolecules", 1),
            ("BCH 409", "Pharmacological Biochemistry", 2),
            ("BCH 411", "Instrumentation and Analytical Methods in Biochemistry", 3),
            ("BCH 413", "Seminar", 2),
            ("BCH 415", "Genetic Engineering", 3),
            ("BCH 417", "Neurobiochemistry", 2),
            ("BCH 419", "Forensic Biochemistry", 2),
            ("MCB 301", "Immunology", 3),
            ("GST 405", "Project Management I", 1),
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # FPAS — PHY  (from Department of Physical Sciences exam list PDF)
    # ═══════════════════════════════════════════════════════════════════════
    "PHY": {
        "100": [
            ("MTH 101", "Elementary Mathematics I", 2),
            ("PHY 101", "General Physics I", 2),
            ("PCU-STA 101", "Descriptive Statistics", 2),
            ("PCU-CHM 101", "General Chemistry I", 2),
        ],
        "200": [
            ("PCU-MTH 201", "Mathematical Methods I", 2),
            ("MTH 203", "Sets, Logic and Algebra", 2),
            ("MTH 205", "Linear Algebra", 2),
            ("STA 201", "Statistics for Biological Sciences", 2),
        ],
        "300": [
            ("PHY 325", "Measurement and Instrumentation", 2),
            ("PHY 305", "Quantum Physics", 3),
            ("PHY 306", "Statistical and Thermal Physics", 2),
            ("PHY 316", "Circuit Theory", 2),
            ("PHY 315", "Electronics", 2),
            ("PHY 312", "Analogue Electronics", 2),
            ("STA 315", "Scientific Writing and Presentation", 2),
        ],
        "400": [
            ("PHY 401", "Solid State Physics", 3),
            ("PHY 403", "Computational Physics", 3),
            ("PHY 405", "Quantum Mechanics I", 3),
            ("PHY 407", "Mathematical Methods in Physics 1", 3),
            ("PHY 413", "Electromagnetic Waves and Optics", 3),
        ],
    },
}

# ── All departments now use real data ────────────────────────────────────


def seed_users(db: Session) -> None:
    if db.query(User).count() > 0:
        return
    users = [
               User(username="admin", full_name="System Administrator",
             hashed_password=hash_password("admin123"), role="admin"),
        User(username="client", full_name="Student User",
             hashed_password=hash_password("client123"), role="client"),
        User(username="ireoluwa", full_name="Ireoluwa",
             hashed_password=hash_password("ireoluwa123"), role="admin"),
        User(username="damilola", full_name="Damilola",
             hashed_password=hash_password("damilola123"), role="admin"),
        User(username="biola", full_name="Biola",
             hashed_password=hash_password("biola123"), role="admin"),
        User(username="diamond", full_name="Diamond",
             hashed_password=hash_password("diamond123"), role="admin"),
        User(username="great", full_name="Great",
             hashed_password=hash_password("great123"), role="admin"),
        User(username="emmanuel", full_name="Emmanuel",
             hashed_password=hash_password("emmanuel123"), role="admin"),
    ]
    db.add_all(users)
    db.commit()


def _make_real_course(code: str, title: str, units: int, dept: str, level: str,
                      lecturer: str) -> CourseItem:
    """Create a CourseItem from real course data with proper time range.

    Unit handling:
      - 3-unit: session A (2hr block) + session B (1hr, different day)
      - 2-unit: 2hr block on one day
      - 1-unit: 1hr slot
      - 1-unit: 1 hour/week → one 1-hour slot
    """
    if units == 3:
        session = "A"
        start, _ = random.choice(TIME_SLOTS)
        start_hr = int(start.split(":")[0])
        if start_hr >= 16:
            start = "15:00"
            start_hr = 15
        end = f"{start_hr + 2:02d}:00"
    elif units == 2:
        session = "A"
        start, _ = random.choice(TIME_SLOTS)
        start_hr = int(start.split(":")[0])
        if start_hr >= 16:
            start = "15:00"
            start_hr = 15
        end = f"{start_hr + 2:02d}:00"
    else:
        session = "A"
        start, end = random.choice(TIME_SLOTS)

    return CourseItem(
        department=dept,
        academic_level=level,
        name=title,
        description=random.choice(VENUES),
        course_code=code,
        lecturer_name=lecturer,
        day_of_the_week=random.choice(DAYS),
        time_start=start,
        time_end=end,
        units=min(units, 3),  # cap at 3 for scheduler
        session=session,
    )


def seed_courses(db: Session) -> None:
    random.seed(42)
    existing_depts = {row[0] for row in db.query(CourseItem.department).distinct().all()}

    items: list[CourseItem] = []

    # ── Real data departments (all departments) ───────────────────────────
    for dept in REAL_COURSES:
        if dept in existing_depts:
            continue
        pool = DEPARTMENT_POOLS[dept]
        courses_by_level = REAL_COURSES[dept]

        # Round-robin lecturer assignment to reduce lecturer conflicts.
        # General courses (HDS, GNS) use the first lecturer so they never
        # share a lecturer with non-general courses.
        lecturers = pool["lecturers"]
        gen_lecturer = lecturers[0]   # dedicated general-course lecturer
        normal_lecturers = lecturers[1:]
        lec_idx = 0

        for level in LEVELS:
            level_courses = courses_by_level.get(level, [])

            for code, title, units in level_courses:
                is_gen = code.startswith("HDS ") or code.startswith("GNS ") or \
                         code.startswith("PCU-HDS ") or code.startswith("PCU-GNS ")
                if is_gen:
                    lecturer = gen_lecturer
                else:
                    lecturer = normal_lecturers[lec_idx % len(normal_lecturers)]
                    lec_idx += 1

                if units == 3:
                    course_a = _make_real_course(code, title, 3, dept, level, lecturer)
                    course_a.session = "A"

                    course_b = _make_real_course(code, title, 3, dept, level, lecturer)
                    course_b.session = "B"
                    other_days = [d for d in DAYS if d != course_a.day_of_the_week]
                    course_b.day_of_the_week = random.choice(other_days) if other_days else course_a.day_of_the_week
                    start, end = random.choice(TIME_SLOTS)
                    course_b.time_start = start
                    course_b.time_end = end

                    items.append(course_a)
                    items.append(course_b)
                else:
                    course = _make_real_course(code, title, units, dept, level, lecturer)
                    items.append(course)

    if items:
        db.add_all(items)
        db.commit()


def seed_all(db: Session) -> None:
    seed_users(db)
    seed_courses(db)