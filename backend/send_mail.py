import os
import smtplib
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GMAIL_SENDER       = os.getenv("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("SENDER_PASSWORD")
REGISTRAR_EMAIL    = os.getenv("REGISTRAR_EMAIL")
GMAIL_SMTP_HOST    = "smtp.gmail.com"
GMAIL_SMTP_PORT    = 587


# ── SHARED SEND HELPER ───────────────────────────────────────────
def _send(to_email: str, subject: str, html_body: str):
    """
    Low-level send over Gmail SMTP with TLS.
    Raises on failure — callers should wrap in try/except.
    """
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "GMAIL_SENDER and GMAIL_APP_PASSWORD must be set in .env\n"
            "See setup instructions at the top of send_email.py"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Fulbright Academic System <{GMAIL_SENDER}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_SENDER, to_email, msg.as_string())

    print(f"[Email] ✅ Sent to {to_email} — {subject[:60]}")


# ── SHARED HTML WRAPPER ───────────────────────────────────────────
def _html_wrap(inner: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #222; margin: 0; padding: 0; }}
  .header {{ background: #003865; padding: 20px 24px; }}
  .header h2 {{ color: #fff; margin: 0; font-size: 1.05rem; }}
  .header p  {{ color: rgba(255,255,255,.7); margin: 4px 0 0; font-size: .85rem; }}
  .body  {{ padding: 24px; background: #fff; border: 1px solid #e0e0e0; max-width: 600px; }}
  .footer {{ padding: 12px 24px; background: #f5f5f5; font-size: .75rem; color: #888; text-align: center; }}
  table  {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
  td     {{ padding: 7px 8px; }}
  tr.alt {{ background: #f9f9f9; }}
  .box   {{ background: #f5f5f5; padding: 10px 12px; border-left: 3px solid #C8972B; margin: 8px 0; }}
  .deadline {{ background: #fff8e1; border: 1px solid #ffe082; border-radius: 6px; padding: 12px 14px; margin-top: 16px; }}
  .action   {{ background: #e3f2fd; border: 1px solid #90caf9; border-radius: 6px; padding: 12px 14px; margin-top: 12px; }}
  .ok  {{ background: #e8f5e9; color: #2e7d32; padding: 10px 14px; border-radius: 6px; }}
  .err {{ background: #ffebee; color: #c62828; padding: 10px 14px; border-radius: 6px; }}
</style>
</head>
<body>
<div style="max-width:620px;margin:0 auto">
  <div class="header">
    <h2>Fulbright Academic Automated System</h2>
    <p>Maximum Course Load Request</p>
  </div>
  <div class="body">{inner}</div>
  <div class="footer">
    This is an automated message from Fulbright University Vietnam Academic System.<br>
    Please do not reply directly to this email unless instructed.
  </div>
</div>
</body>
</html>"""


# ── STEP 5: EMAIL TO ADVISOR ─────────────────────────────────────
def send_advisor_email(request: dict):
    """
    Send approval request email to the student's academic advisor.

    `request` is the dict returned by request_db.create_request(), e.g.:
    {
        "request_id":   "REQABC123",
        "student":      { "student_name": ..., "student_id": ..., "email_address": ..., "advisor_name": ... },
        "courses":      ["CS101", "ARTS102"],
        "reason":       "...",
        "plan":         "...",
        "advisor_email": "...",
        "deadline":     "2026-05-05T...",
        "credit_required": 8,
    }
    """
    student       = request["student"]
    courses       = request["courses"]
    advisor_email = request.get("advisor_email", "")
    request_id    = request["request_id"]
    deadline_str  = _fmt_deadline(request.get("deadline"))
    course_rows   = "\n".join(
        f"<tr{'class=\"alt\"' if i%2 else ''}><td>{c}</td></tr>"
        for i, c in enumerate(courses)
    )

    inner = f"""
<p>Dear <strong>{student.get('advisor_name', 'Academic Advisor')}</strong>,</p>
<p>
  This is an automated notification regarding a
  <strong>Request for Maximum Course Load</strong>.
  A student under your advisement has submitted a request to register for
  <strong>{request.get('credit_required', len(courses)*4)} credit hours</strong>
  for the 2025–2026 Academic Year.
</p>
<p>Per university policy, your approval is required before the request can be
processed by the Registrar's Office.</p>

<h3 style="color:#003865;border-bottom:2px solid #C8972B;padding-bottom:6px;margin-top:20px">
  Request Details
</h3>
<table>
  <tr>          <td style="color:#666;width:140px">Student Name</td><td><strong>{student['student_name']}</strong></td></tr>
  <tr class="alt"><td style="color:#666">Student ID</td>  <td>{student['student_id']}</td></tr>
  <tr>          <td style="color:#666">Email</td>         <td>{student['email_address']}</td></tr>
  <tr class="alt"><td style="color:#666">Term</td>        <td>Spring 2026</td></tr>
  <tr>          <td style="color:#666">Credits Requested</td><td><strong>{request.get('credit_required', '—')}</strong></td></tr>
  <tr class="alt"><td style="color:#666">Request ID</td>  <td><code>{request_id}</code></td></tr>
</table>

<h3 style="color:#003865;margin-top:18px">Requested Courses</h3>
<table>{course_rows}</table>

<h3 style="color:#003865;margin-top:18px">Student's Reason</h3>
<div class="box">{request.get('reason', '—')}</div>

<h3 style="color:#003865;margin-top:18px">Student's Workload Plan</h3>
<div class="box">{request.get('plan', '—')}</div>

<div class="deadline">
  <strong>⏰ Response Deadline: {deadline_str}</strong><br>
  <small>Please respond within 48 hours of receiving this email.</small>
</div>

<div class="action">
  <strong>Action Required</strong><br>
  Please reply to this email with one of the following:<br><br>
  • <strong>Approve</strong> — to approve the request<br>
  • <strong>Deny: [your reason]</strong> — to deny with a reason<br><br>
  <small>Your reply will be automatically processed by the system. Request ID: <code>{request_id}</code></small>
</div>
"""

    _send(
        to_email=advisor_email,
        subject=f"[Action Required] Course Load Request — {student['student_name']} (ID: {request_id})",
        html_body=_html_wrap(inner),
    )


# ── STEP 7: EMAIL TO REGISTRAR ───────────────────────────────────
def send_registrar_email(request: dict):
    """
    Forward approved request to Registrar's Office.
    Called after advisor approves.
    """
    student    = request["student"]
    courses    = request["courses"]
    request_id = request["request_id"]
    course_list = ", ".join(courses)
    deadline_str = _fmt_deadline(
        (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    )

    inner = f"""
<p>Dear Registrar's Office,</p>
<p>
  The Academic Advisor has <strong>approved</strong> a
  <strong>Request for Maximum Course Load</strong>.
  Please review and provide your final decision.
</p>

<h3 style="color:#003865;border-bottom:2px solid #C8972B;padding-bottom:6px;margin-top:20px">
  Student &amp; Term Information
</h3>
<table>
  <tr>            <td style="color:#666;width:160px">Student Name</td><td><strong>{student['student_name']}</strong></td></tr>
  <tr class="alt"><td style="color:#666">Student ID</td>   <td>{student['student_id']}</td></tr>
  <tr>            <td style="color:#666">Semester</td>     <td>Spring 2026</td></tr>
  <tr class="alt"><td style="color:#666">Courses</td>      <td>{course_list}</td></tr>
  <tr>            <td style="color:#666">Credits</td>      <td>{request.get('credit_required', '—')}</td></tr>
  <tr class="alt"><td style="color:#666">Advisor Decision</td><td><strong style="color:#2e7d32">✅ Approved</strong></td></tr>
  <tr>            <td style="color:#666">Request ID</td>   <td><code>{request_id}</code></td></tr>
</table>

<h3 style="color:#003865;margin-top:18px">Student's Reason</h3>
<div class="box">{request.get('reason', '—')}</div>

<div class="deadline">
  <strong>Response Deadline: {deadline_str}</strong>
</div>

<div class="action">
  <strong>Action Required</strong><br>
  Please reply to this email with:<br><br>
  • <strong>Approve</strong> — to finalize approval<br>
  • <strong>Reject: [your reason]</strong> — to reject with a reason<br><br>
  <small>Request ID: <code>{request_id}</code></small>
</div>
"""

    _send(
        to_email=REGISTRAR_EMAIL,
        subject=f"[Registrar Action Required] Course Load — {student['student_name']} (ID: {request_id})",
        html_body=_html_wrap(inner),
    )


# ── STEP 8: EMAIL TO STUDENT ─────────────────────────────────────
def send_student_email(request: dict, status: str, reason: str = None):
    """
    Notify the student of the final outcome.
    status: 'approved' | 'rejected'
    """
    student    = request["student"]
    request_id = request["request_id"]

    if status == "approved":
        inner = f"""
<p>Dear <strong>{student['student_name']}</strong>,</p>
<div class="ok">
  <strong>✅ Your Maximum Course Load Request has been approved!</strong>
</div>
<p style="margin-top:16px">
  Your request for the 2025–2026 Academic Year (Spring 2026) has been
  officially approved by both your Academic Advisor and the Registrar's Office.
</p>
<p>You are now authorized to register for up to
   <strong>{request.get('credit_required', '20')} credit hours</strong> this term.</p>
<p>Please proceed with course registration through the student portal.</p>
<p style="margin-top:24px">
  Best regards,<br>
  <strong>Fulbright Academic Automated System</strong>
</p>
<p style="font-size:.8rem;color:#888">Request ID: {request_id}</p>
"""
        subject = f"Course Load Request Approved — {student['student_name']}"

    else:
        inner = f"""
<p>Dear <strong>{student['student_name']}</strong>,</p>
<div class="err">
  <strong>❌ Your Maximum Course Load Request has not been approved.</strong>
</div>
<p style="margin-top:16px">
  After review, your request for the 2025–2026 Academic Year (Spring 2026)
  has been <strong>rejected</strong>.
</p>
<table style="margin-top:12px">
  <tr><td style="color:#666;width:120px">Status</td><td><strong>Not Approved</strong></td></tr>
  <tr class="alt"><td style="color:#666">Reason</td><td>{reason or 'Please contact your advisor for details.'}</td></tr>
  <tr><td style="color:#666">Request ID</td><td><code>{request_id}</code></td></tr>
</table>
<p style="margin-top:16px">
  You may resubmit your request after addressing the concerns raised,
  or visit the Registrar's Office for further guidance.
</p>
<p style="margin-top:24px">
  Best regards,<br>
  <strong>Fulbright Academic Automated System</strong>
</p>
"""
        subject = f"Course Load Request Not Approved — {student['student_name']}"

    _send(
        to_email=student["email_address"],
        subject=subject,
        html_body=_html_wrap(inner),
    )


# ── HELPERS ───────────────────────────────────────────────────────
def _fmt_deadline(iso: str) -> str:
    try:
        # Parse ISO format and display as user-friendly date
        iso_clean = iso.rstrip('Z') if iso.endswith('Z') else iso
        dt = datetime.fromisoformat(iso_clean)
        return f"no later than {dt.strftime('%Y-%m-%d')}"
    except Exception:
        return iso or "48 hours from now"


# ── QUICK TEST ────────────────────────────────────────────────────
if __name__ == "__main__":
    # Test with a mock request
    mock_request = {
        "request_id":    "REQTEST1",
        "student": {
            "student_name":  "Nguyen Van A",
            "student_id":    22000,
            "email_address": "thanhngan2332@gmail.com",   # ← change this
            "advisor_name":  "Le E",
        },
        "courses":         ["CS101", "ARTS102"],
        "reason":          "Need to graduate on time",
        "plan":            "Meet instructors weekly",
        "advisor_email":   "thanhngan2332@gmail.com",        # ← change this
        "deadline":        (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat() + "Z",
        "credit_required": 8,
    }

    print("Testing advisor email…")
    try:
        send_advisor_email(mock_request)
    except Exception as e:
        print(f"{e}")

    print("Testing student approval email…")
    try:
        send_student_email(mock_request, status="approved")
    except Exception as e:
        print(f"{e}")
