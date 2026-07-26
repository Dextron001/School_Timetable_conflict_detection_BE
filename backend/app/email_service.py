"""Email notification service for complaints.

By default, email is DISABLED. To enable it, set these in your .env:
  SMTP_ENABLED=true
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your_email@gmail.com
  SMTP_PASSWORD=your_app_password
  ADMIN_EMAIL=admin@yourdomain.com

When disabled, complaints are only stored in the database and shown
on the Admin dashboard. When enabled, an email is sent to ADMIN_EMAIL
each time a client submits a complaint.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SMTP_ENABLED = os.environ.get("SMTP_ENABLED", "false").lower() == "true"
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")


def send_complaint_notification(complaint, submitter, db):
    """Send an email to the admin about a new complaint (if SMTP is enabled)."""
    if not SMTP_ENABLED:
        print("[Email] SMTP is disabled. Skipping email notification.")
        return

    if not SMTP_USER or not SMTP_PASSWORD or not ADMIN_EMAIL:
        print("[Email] SMTP credentials not configured. Skipping email.")
        print("[Email] Set SMTP_USER, SMTP_PASSWORD, and ADMIN_EMAIL in .env to enable.")
        return

    subject_line = f"[ResolvIt] New Complaint: {complaint.subject}"

    body = f"""
A new timetable complaint has been submitted:

From: {submitter.full_name} ({submitter.username})
Faculty: {complaint.faculty}
Course: {complaint.course_code or 'N/A'}
Subject: {complaint.subject}

Message:
{complaint.message}

---
Submitted at: {complaint.created_at.strftime('%Y-%m-%d %H:%M UTC')}

View and resolve this complaint on the ResolvIt Admin Dashboard.
"""

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = ADMIN_EMAIL
    msg["Subject"] = subject_line
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, ADMIN_EMAIL, msg.as_string())
        server.quit()
        print(f"[Email] ✓ Notification sent to {ADMIN_EMAIL}")
    except Exception as e:
        print(f"[Email] ✗ Failed to send email: {e}")