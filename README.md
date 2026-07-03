# 🗓️ Timetable Conflict Detection & Resolution System

A full-stack web app that lets a school administrator **generate** class timetables,
automatically **detect and resolve scheduling conflicts**, and lets students
**view and download** their timetable.

| Layer | Technology |
|-------|------------|
| Frontend | **React 18 + Vite + Tailwind CSS** (JavaScript) |
| Backend | **Python + FastAPI** |
| Database | **SQLite** (via SQLAlchemy) |
| Auth | **JWT tokens + bcrypt password hashing** |
| PDF export | **ReportLab** |

---

## ✨ Features

- **Two roles, two dashboards**
  - **Admin** — generate timetables, auto-resolve conflicts, edit any course, export PDF.
  - **Client (Student)** — view the published timetable and download it as PDF. (Cannot modify anything — enforced on the server, not just hidden in the UI.)
- **Real authentication** — passwords are hashed with bcrypt; sessions use signed JWTs.
- **Conflict detection** — overlapping lectures on the same day are highlighted in red.
- **Automatic resolution** — clashing courses are moved to free time slots until no overlaps remain.
- **PDF export** — a clean, printable timetable grouped by weekday.
- **Customizable theme** — colors are driven by CSS variables, plus a light/dark toggle.

---

## 🚀 Running the project

You need **Python 3.10+** and **Node 18+**.

### 1. Backend (terminal 1)
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
- API runs at **http://127.0.0.1:8000**
- Interactive docs at **http://127.0.0.1:8000/docs**
- On first run it auto-creates `timetable.db` and seeds demo data.

### 2. Frontend (terminal 2)
```bash
cd frontend
npm install
npm run dev
```
- App runs at **http://127.0.0.1:5173**

> Tip: the script `./run.sh` starts both at once (Linux/macOS).

---

## 🔑 Demo accounts

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Client | `client` | `client123` |

(There are quick-fill buttons on the login screen.)

---

## 🎨 Customizing the look

Open `frontend/src/index.css`. At the top you'll find a `:root` block of CSS
variables (colors are `R G B`). Change `--brand` to instantly rebrand every
button, badge and accent. A `.dark` block defines the dark theme. The
**🌙 / ☀️ toggle** in the header switches between them.

Tailwind utility classes are used everywhere, so you can also tweak spacing,
rounding and typography directly in the JSX components under
`frontend/src/components/` and `frontend/src/pages/`.

---

## 📁 Project structure

```
timetable-app/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI routes (auth + courses + export)
│   │   ├── auth.py        # JWT + bcrypt + role guards
│   │   ├── models.py      # SQLAlchemy tables (User, CourseItem)
│   │   ├── schemas.py     # Pydantic request/response models
│   │   ├── timetable.py   # conflict detection + generate + resolve logic
│   │   ├── pdf_export.py  # ReportLab PDF builder
│   │   ├── seed.py        # demo users + courses
│   │   └── database.py    # engine / session
│   └── requirements.txt
└── frontend/
    └── src/
        ├── api.js                  # fetch wrapper (attaches JWT)
        ├── App.jsx                 # routes
        ├── context/                # Auth + Toast providers
        ├── components/             # reusable UI
        └── pages/                  # Login, AdminDashboard, ClientDashboard
```

---

## 🛡️ How the conflict logic works (for your defence)

1. Each course has a `day_of_the_week` and 24-hour `time_start` / `time_end`.
2. Two courses **conflict** when they share a day and their time ranges overlap:
   `start_A < end_B AND end_A > start_B`.
3. `find_conflicts()` returns the ids of every course involved in a clash —
   the UI paints those rows red.
4. **Resolve** repeatedly finds a clashing course and relocates it to the first
   free `(day, slot)` pair, re-checking after each move, until no conflicts remain.

> Note: times are stored in **24-hour format** (`13:00`, not `1:00`). The
> original prototype stored afternoons as `1:00`/`2:30`, which were parsed as
> 1 a.m. and silently broke overlap detection — that bug is fixed here.
