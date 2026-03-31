"""
email_service.py — Outlook email via exchangelib (Microsoft Exchange / O365)
-----------------------------------------------------------------------------
Install:  pip install exchangelib

Set these in your .env:
  OUTLOOK_EMAIL=your_agent_email@fulbright.edu.vn
  OUTLOOK_PASSWORD=your_password
  OUTLOOK_SERVER=outlook.office365.com     # or your Exchange server
  ADVISOR_EMAIL=advisor@fulbright.edu.vn
  REGISTRAR_EMAIL=registrar@fulbright.edu.vn

NOTE: For Office 365, you may need to use OAuth2 instead of basic auth.
      See: https://ecederstrand.github.io/exchangelib/#oauth2
      For a demo, basic auth with an app password works fine.
"""

import os
from datetime import datetime
from exchangelib import (
    Credentials, Account, Message, Mailbox,
    HTMLBody, Configuration, DELEGATE
)
from exchangelib.protocol import BaseProtocol, NoVerifyHTTPAdapter

# Optional: disable SSL verify for corp proxies (dev only)
# BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter


def _get_account() -> Account:
    """Build and return an authenticated Exchange account."""
    email    = os.getenv("OUTLOOK_EMAIL")
    password = os.getenv("OUTLOOK_PASSWORD")
    server   = os.getenv("OUTLOOK_SERVER", "outlook.office365.com")

    if not email or not password:
        raise RuntimeError(
            "OUTLOOK_EMAIL and OUTLOOK_PASSWORD must be set in .env"
        )

    credentials = Credentials(username=email, password=password)
    config = Configuration(server=server, credentials=credentials)
    return Account(
        primary_smtp_address=email,
        config=config,
        autodiscover=False,
        access_type=DELEGATE,
    )


# ─── Advisor Email ────────────────────────────────────────────────────────────

def send_advisor_email(
    request_id: str,
    student: dict,
    courses: list,
    reason: str,
    plan: str,
    advisor_email: str,
    deadline_hours: int = 48,
):
    """Send course load approval request to academic advisor."""
    deadline_str = (
        datetime.utcnow()
        .__class__
        .now()
        .strftime("%B %d, %Y at %I:%M %p")
    )

    course_rows = "".join(
        f"<tr><td style='padding:4px 8px;border:1px solid #ddd'>{c}</td></tr>"
        for c in courses
    )

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; color: #222;">
      <div style="background:#003865;padding:20px 24px;">
        <h2 style="color:#fff;margin:0;font-size:1.1rem">
          Fulbright Academic Automated System
        </h2>
        <p style="color:rgba(255,255,255,.75);margin:4px 0 0;font-size:.85rem">
          Maximum Course Load Request — Action Required
        </p>
      </div>

      <div style="padding:24px;background:#fff;border:1px solid #e0e0e0;">
        <p>Dear Academic Advisor,</p>
        <p>
          This is an automated notification regarding a
          <strong>Request for Maximum Course Load</strong>.
          A student under your advisement has submitted a request to register
          for a workload of <strong>{len(courses) * 4} credit hours</strong>
          for the 2026 Academic Year, Fall Term.
        </p>
        <p>Pursuant to university policy, this request requires your formal
        review and approval before it can be processed by the Office of the Registrar.</p>

        <h3 style="color:#003865;border-bottom:2px solid #C8972B;padding-bottom:6px">
          Request Details
        </h3>
        <table style="width:100%;border-collapse:collapse;font-size:.9rem">
          <tr><td style="padding:6px;color:#666;width:140px">Student Name</td>
              <td style="padding:6px"><strong>{student['student_name']}</strong></td></tr>
          <tr style="background:#f9f9f9">
              <td style="padding:6px;color:#666">Student ID</td>
              <td style="padding:6px">{student['student_id']}</td></tr>
          <tr><td style="padding:6px;color:#666">Email</td>
              <td style="padding:6px">{student['email_address']}</td></tr>
          <tr style="background:#f9f9f9">
              <td style="padding:6px;color:#666">Term</td>
              <td style="padding:6px">Fall 2026</td></tr>
          <tr><td style="padding:6px;color:#666">Credit Hours</td>
              <td style="padding:6px"><strong>{len(courses) * 4}</strong></td></tr>
        </table>

        <h3 style="color:#003865;margin-top:20px">Requested Courses</h3>
        <table style="border-collapse:collapse;font-size:.9rem">
          {course_rows}
        </table>

        <h3 style="color:#003865;margin-top:20px">Student's Reason</h3>
        <p style="background:#f5f5f5;padding:10px;border-left:3px solid #C8972B">
          {reason}
        </p>

        <h3 style="color:#003865;margin-top:20px">Student's Workload Plan</h3>
        <p style="background:#f5f5f5;padding:10px;border-left:3px solid #C8972B">
          {plan}
        </p>

        <div style="background:#fff8e1;border:1px solid #ffe082;border-radius:6px;
                    padding:14px;margin-top:20px">
          <strong>⏰ Response Deadline: {deadline_hours} hours from receipt</strong><br>
          <small style="color:#666">Request ID: {request_id}</small>
        </div>

        <h3 style="color:#003865;margin-top:20px">Action Required</h3>
        <p>Please reply to this email with one of the following:</p>
        <ul>
          <li><strong>Approve</strong> — to approve the request</li>
          <li><strong>Deny: [reason]</strong> — to deny with a specific reason</li>
        </ul>
        <p style="color:#666;font-size:.85rem">
          Your reply will be automatically processed by the system.
          The student and Registrar's Office will be notified accordingly.
        </p>
      </div>

      <div style="padding:12px 24px;background:#f5f5f5;
                  font-size:.75rem;color:#888;text-align:center">
        This is an automated message from the Fulbright Academic System.
        Do not forward this email. Request ID: {request_id}
      </div>
    </div>
    """

    try:
        account = _get_account()
        msg = Message(
            account=account,
            subject=f"[Action Required] Course Load Request — {student['student_name']} (ID: {request_id})",
            body=HTMLBody(html_body),
            to_recipients=[Mailbox(email_address=advisor_email)],
        )
        msg.send()
        print(f"[EMAIL] Advisor email sent to {advisor_email} for request {request_id}")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send advisor email: {e}")
        # In demo mode, just log — don't crash the app
        raise


# ─── Student Notification Email ───────────────────────────────────────────────

def send_student_email(student: dict, status: str, reason: str = None):
    """Notify student of final approved/rejected outcome."""

    if status == "approved":
        subject = "✅ Your Course Load Request Has Been Approved"
        body_content = f"""
        <p>Dear <strong>{student['student_name']}</strong>,</p>
        <p>We are pleased to inform you that your
           <strong>Request for Maximum Course Load</strong> for the 2026 Academic Year
           has been officially approved.</p>
        <p style="background:#e8f5e9;padding:12px;border-radius:6px;color:#2e7d32">
          <strong>✅ You are now authorized to register for up to 20 credit hours
          for this term.</strong>
        </p>
        <p>Please proceed with course registration through the student portal.</p>
        """
    else:
        subject = "❌ Your Course Load Request — Not Approved"
        body_content = f"""
        <p>Dear <strong>{student['student_name']}</strong>,</p>
        <p>We regret to inform you that your
           <strong>Request for Maximum Course Load</strong> for the 2026 Academic Year
           has not been approved following review.</p>
        <div style="background:#ffebee;padding:12px;border-radius:6px;color:#c62828;margin:12px 0">
          <strong>Status: Not Approved</strong><br>
          <strong>Reason:</strong> {reason or 'Please contact your advisor for details.'}
        </div>
        <p>You may resubmit your request after addressing the concerns raised,
           or contact the Registrar's Office for further guidance.</p>
        """

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;color:#222">
      <div style="background:#003865;padding:20px 24px">
        <h2 style="color:#fff;margin:0;font-size:1.1rem">
          Fulbright Academic Automated System
        </h2>
      </div>
      <div style="padding:24px;background:#fff;border:1px solid #e0e0e0">
        {body_content}
        <p style="margin-top:24px">Best regards,<br>
           <strong>Fulbright Academic Automated System</strong></p>
      </div>
      <div style="padding:12px 24px;background:#f5f5f5;
                  font-size:.75rem;color:#888;text-align:center">
        This is an automated message. Please do not reply to this email.
      </div>
    </div>
    """

    try:
        account = _get_account()
        msg = Message(
            account=account,
            subject=subject,
            body=HTMLBody(html_body),
            to_recipients=[Mailbox(email_address=student["email_address"])],
        )
        msg.send()
        print(f"[EMAIL] Student notification sent to {student['email_address']} — {status}")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send student email: {e}")
        raise


# ─── Registrar Email ──────────────────────────────────────────────────────────

def send_registrar_email(
    request_id: str,
    student: dict,
    courses: list,
    reason: str,
    advisor_decision: str,
    registrar_email: str,
):
    """Forward approved advisor request to Registrar's Office."""

    course_list = ", ".join(courses)

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;color:#222">
      <div style="background:#003865;padding:20px 24px">
        <h2 style="color:#fff;margin:0;font-size:1.1rem">
          Fulbright Academic Automated System
        </h2>
        <p style="color:rgba(255,255,255,.75);margin:4px 0 0;font-size:.85rem">
          Maximum Course Load — Advisor Approved, Registrar Action Required
        </p>
      </div>
      <div style="padding:24px;background:#fff;border:1px solid #e0e0e0">
        <p>Dear Registrar's Office,</p>
        <p>The Academic Advisor has approved a
           <strong>Request for Maximum Course Load</strong>
           for the following student. Please review and confirm.</p>

        <h3 style="color:#003865;border-bottom:2px solid #C8972B;padding-bottom:6px">
          Student &amp; Term Information
        </h3>
        <table style="width:100%;border-collapse:collapse;font-size:.9rem">
          <tr><td style="padding:6px;color:#666;width:140px">Student Name</td>
              <td><strong>{student['student_name']}</strong></td></tr>
          <tr style="background:#f9f9f9">
              <td style="padding:6px;color:#666">Student ID</td>
              <td>{student['student_id']}</td></tr>
          <tr><td style="padding:6px;color:#666">Semester</td>
              <td>Fall 2026</td></tr>
          <tr style="background:#f9f9f9">
              <td style="padding:6px;color:#666">Courses</td>
              <td>{course_list}</td></tr>
          <tr><td style="padding:6px;color:#666">Student Reason</td>
              <td>{reason}</td></tr>
          <tr style="background:#f9f9f9">
              <td style="padding:6px;color:#666">Advisor Decision</td>
              <td><strong style="color:#2e7d32">✅ Approved</strong></td></tr>
        </table>

        <div style="background:#fff8e1;border:1px solid #ffe082;border-radius:6px;
                    padding:14px;margin-top:20px">
          <strong>Request ID: {request_id}</strong><br>
          Please reply <strong>"Approve"</strong> or <strong>"Reject: [reason]"</strong>
        </div>
      </div>
    </div>
    """

    try:
        account = _get_account()
        msg = Message(
            account=account,
            subject=f"[Registrar Action Required] Course Load — {student['student_name']} (ID: {request_id})",
            body=HTMLBody(html_body),
            to_recipients=[Mailbox(email_address=registrar_email)],
        )
        msg.send()
        print(f"[EMAIL] Registrar email sent to {registrar_email} for {request_id}")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send registrar email: {e}")
        raise
