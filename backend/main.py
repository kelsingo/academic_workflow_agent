import os
import json
import uuid
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from backend.validate_info import build_n_validate        
from backend.check_eligibility import eligible_check          
from backend.data_adapter import load_student_data, load_credits_required, load_course_availability
from backend.send_mail import send_advisor_email, send_registrar_email, send_student_email
from backend.classify_llm import classify_advisor_reply, suggest_fix

# Database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.abspath(os.path.join(BASE_DIR, '..', 'datasets', 'fuv_data.db'))

ADVISOR_DEADLINE_HOURS   = 48
REGISTRAR_DEADLINE_HOURS = 48


# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS course_load_requests (
            request_id          TEXT PRIMARY KEY,
            student_id          INTEGER NOT NULL,
            student_name        TEXT NOT NULL,
            student_email       TEXT NOT NULL,
            advisor_name        TEXT,
            advisor_email       TEXT,
            courses             TEXT NOT NULL,
            reason              TEXT,
            plan                TEXT,
            credit_required     INTEGER,
            status              TEXT NOT NULL DEFAULT 'pending_advisor',
            advisor_decision    TEXT,
            advisor_reason      TEXT,
            registrar_decision  TEXT,
            registrar_reason    TEXT,
            submitted_at        TEXT NOT NULL,
            advisor_deadline    TEXT,
            last_updated        TEXT NOT NULL,
            notify_push         INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    print(f"[Init] DB ready: {DB_PATH}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    pass


# App
app = FastAPI(title="Fulbright Academic Workflow Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # restrict to your frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _deadline_iso(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()

def _gen_request_id() -> str:
    return "REQ" + str(uuid.uuid4())[:6].upper()


# Look up advisor email from the advisors table
def _get_advisor_email(advisor_name: str) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT email FROM advisors WHERE advisor_name = ?", (advisor_name,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def db_create_request(student_id: int, courses: list, reason: str, plan: str) -> dict:

    # Load student info from DB
    student = load_student_data(student_id)
    if not student:
        raise HTTPException(status_code=400, detail=f"Student ID {student_id} not found in database.")

    # Get advisor email
    advisor_email = _get_advisor_email(student["advisor_name"])
    if not advisor_email:
        print(f"[Warning] No email found for advisor '{student['advisor_name']}'")

    # Run eligibility check
    check_data = {
        "student_id": student_id,
        "course_ids": courses,
        "reason":     reason,
        "plan":       plan,
    }
    result = eligible_check(check_data)

    if result is True:
        pass  # eligible, continue
    elif result is False:
        raise HTTPException(
            status_code=400,
            detail="You do not have enough available credits for this course load."
        )
    else:
        # eligible_check returned an error string
        raise HTTPException(status_code=400, detail=str(result))

    # Calculate total credits
    credit_required = load_credits_required(courses) or 0

    # Save to DB
    request_id = _gen_request_id()
    now        = _now()
    deadline   = _deadline_iso(ADVISOR_DEADLINE_HOURS)

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO course_load_requests (
            request_id, student_id, student_name, student_email,
            advisor_name, advisor_email, courses, reason, plan,
            credit_required, status, submitted_at, advisor_deadline, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_advisor', ?, ?, ?)
    """, (
        request_id,
        student_id,
        student["student_name"],
        student["email"],
        student["advisor_name"],
        advisor_email,
        json.dumps(courses),
        reason,
        plan,
        credit_required,
        now,
        deadline,
        now,
    ))
    conn.commit()
    conn.close()
    print(f"[DB] Created {request_id} for student {student_id} ({student['student_name']})")

    # Return the full dict for send_mail.py 
    return {
        "request_id":      request_id,
        "status":          "pending_advisor",
        "deadline":        deadline,
        "advisor_email":   advisor_email,
        "credit_required": credit_required,
        "courses":         courses,
        "reason":          reason,
        "plan":            plan,
        "student": {
            "student_name":  student["student_name"],
            "student_id":    student_id,
            "email_address": student["email"],
            "advisor_name":  student["advisor_name"],
        },
    }


def db_get_request(request_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()
    cur.execute("SELECT * FROM course_load_requests WHERE request_id = ?", (request_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["courses"]     = json.loads(d["courses"])
    d["notify_push"] = bool(d["notify_push"])
    return d


def db_update_status(
    request_id: str,
    status: str,
    advisor_decision: str    = None,
    advisor_reason: str      = None,
    registrar_decision: str  = None,
    registrar_reason: str    = None,
    notify_push: bool        = True,
):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        UPDATE course_load_requests SET
            status             = ?,
            advisor_decision   = COALESCE(?, advisor_decision),
            advisor_reason     = COALESCE(?, advisor_reason),
            registrar_decision = COALESCE(?, registrar_decision),
            registrar_reason   = COALESCE(?, registrar_reason),
            notify_push        = ?,
            last_updated       = ?
        WHERE request_id = ?
    """, (
        status,
        advisor_decision, advisor_reason,
        registrar_decision, registrar_reason,
        1 if notify_push else 0,
        _now(),
        request_id,
    ))
    conn.commit()
    conn.close()
    print(f"[DB] {request_id} status -> {status}")

# Reset notify_push to 0 after frontend has read
def db_clear_push(request_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute(
        "UPDATE course_load_requests SET notify_push = 0 WHERE request_id = ?",
        (request_id,)
    )
    conn.commit()
    conn.close()


def db_list_all() -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()
    cur.execute("SELECT * FROM course_load_requests ORDER BY submitted_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["courses"]     = json.loads(r["courses"])
        r["notify_push"] = bool(r["notify_push"])
    return rows

# Send email
def _ensure_student_dict(req: dict) -> dict:
    """
    Ensure req has proper nested student dict.
    Handles both formats:
    - Flat dict from db_get_request(): {student_name, student_id, student_email, ...}
    - Nested dict from db_create_request(): {student: {student_name, student_id, email_address, ...}, ...}
    """
    # If already has nested student dict, return as-is
    if "student" in req and isinstance(req["student"], dict):
        if "student_name" in req["student"]:
            return req
    
    # Otherwise, reconstruct from flat keys
    req_for_email = {
        **req,
        "student": {
            "student_name": req.get("student_name"),
            "student_id": req.get("student_id"),
            "email_address": req.get("student_email"),
            "advisor_name": req.get("advisor_name"),
        },
    }
    return req_for_email

def _send_advisor_safe(req: dict):
    try:
        req_for_email = _ensure_student_dict(req)
        send_advisor_email(req_for_email)
        print(f"[Email] Advisor email sent for {req['request_id']}")
    except Exception as e:
        print(f"[Email Error] Advisor email for {req['request_id']}: {e}")

def _send_registrar_safe(req: dict):
    try:
        req_for_email = _ensure_student_dict(req)
        send_registrar_email(req_for_email)
        print(f"[Email] Registrar email sent for {req['request_id']}")
    except Exception as e:
        print(f"[Email Error] Registrar email for {req['request_id']}: {e}")

def _send_student_safe(req: dict, status: str, reason: str = None):
    try:
        req_for_email = _ensure_student_dict(req)
        send_student_email(req_for_email, status, reason)
        print(f"[Email] Student email sent for {req['request_id']}")
    except Exception as e:
        print(f"[Email Error] Student email for {req['request_id']}: {e}")


# ══════════════════════════════════════════════════════════════════
# Extract + validate student message
# ══════════════════════════════════════════════════════════════════

class ExtractBody(BaseModel):
    text:       str
    student_id: Optional[int] = None

@app.post("/api/extract")
async def api_extract(body: ExtractBody):

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set on server.")

    result = build_n_validate(api_key, body.text)

    if not result.get("valid"):
        errors = result.get("errors", []) + result.get("missing_fields", [])
        extracted = result.get("data", {})
        
        # Check for null reason/plan specifically
        has_null_reason = extracted.get("reason") is None
        has_null_plan = extracted.get("plan") is None
        
        return {
            "is_valid": False,
            "courses":  extracted.get("course_ids", []) or [],
            "reason":   extracted.get("reason"),
            "plan":     extracted.get("plan"),
            "has_null_reason": has_null_reason,
            "has_null_plan": has_null_plan,
            "errors":   errors or ["Please check your input and try again."],
        }

    extracted  = result.get("data", {})
    course_ids = extracted.get("course_ids") or []

    # Check each course exists in the DB
    unavailable = load_course_availability(course_ids)
    if unavailable:
        for c in unavailable:
            print(f"[Extract] Course not in DB: {c}")
        return {
            "is_valid": False,
            "courses":  [],
            "reason":   extracted.get("reason"),
            "plan":     extracted.get("plan"),
            "errors":   [
                f"The following course(s) are not available this semester: "
                f"<strong>{', '.join(unavailable)}</strong>. Please check and try again."
            ],
        }

    return {
        "is_valid": True,
        "courses":  course_ids,
        "reason":   extracted.get("reason"),
        "plan":     extracted.get("plan"),
        "errors":   [],
    }


# ══════════════════════════════════════════════════════════════════
# Submit request
# ══════════════════════════════════════════════════════════════════

class SubmitBody(BaseModel):
    student_id: int
    courses:    list[str]
    reason:     str
    plan:       str

@app.post("/api/submit")
async def api_submit(body: SubmitBody, background_tasks: BackgroundTasks):
    """
    1. Eligibility check (check_eligibility.py)
    2. Save request to course_load_requests table
    3. Send advisor email in background (send_mail.py)
    """
    req = db_create_request(
        student_id=body.student_id,
        courses=body.courses,
        reason=body.reason,
        plan=body.plan,
    )

    # Send advisor email in background (send_mail.py)
    background_tasks.add_task(_send_advisor_safe, req)

    return {
        "request_id": req["request_id"],
        "status":     req["status"],
        "deadline":   req["deadline"],
    }


# ══════════════════════════════════════════════════════════════════
# Poll request status
# ══════════════════════════════════════════════════════════════════

@app.get("/api/status/{request_id}")
async def api_status(request_id: str):
    # Detect when advisor/registrar has replied
    # notify_push = False after the email was read

    req = db_get_request(request_id.upper())
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")

    response = {
        "request_id":         req["request_id"],
        "status":             req["status"],
        "advisor_decision":   req["advisor_decision"],
        "advisor_reason":     req["advisor_reason"],
        "registrar_decision": req["registrar_decision"],
        "registrar_reason":   req["registrar_reason"],
        "submitted_at":       req["submitted_at"],
        "deadline":           req["advisor_deadline"],
        "last_updated":       req["last_updated"],
        "notify_push":        req["notify_push"],
        "courses":            req["courses"],
        "reason":             req["reason"],
        "plan":               req["plan"],
    }

    # Consume push flag — next poll returns False
    if req["notify_push"]:
        db_clear_push(request_id.upper())

    return response


# ══════════════════════════════════════════════════════════════════
# Advisor reply
# ══════════════════════════════════════════════════════════════════

class ReplyBody(BaseModel):
    request_id:     str
    raw_email_body: str

@app.post("/api/advisor-reply")
async def api_advisor_reply(body: ReplyBody, background_tasks: BackgroundTasks):

    req = db_get_request(body.request_id.upper())
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
    if req["status"] != "pending_advisor":
        raise HTTPException(
            status_code=400,
            detail=f"Request is '{req['status']}', not 'pending_advisor'."
        )
    
    # Classify the email as approve or reject
    decision, reason = classify_advisor_reply(body.raw_email_body)

    if decision == "approved":
        db_update_status(
            req["request_id"],
            status="pending_registrar",
            advisor_decision="approved",
            advisor_reason=reason,
            notify_push=True,
        )
        # Fetch fresh request from DB before sending email
        req_fresh = db_get_request(req["request_id"])
        background_tasks.add_task(_send_registrar_safe, req_fresh)
        print(f"[Step 6] {req['request_id']} approved -> forwarded to registrar")

    else:
        db_update_status(
            req["request_id"],
            status="rejected",
            advisor_decision="rejected",
            advisor_reason=reason,
            notify_push=True,
        )
        # Fetch fresh request from DB before sending email
        req_fresh = db_get_request(req["request_id"])
        background_tasks.add_task(_send_student_safe, req_fresh, "rejected", reason)
        print(f"[Step 6] {req['request_id']} rejected. Reason: {reason}")

    return {"ok": True, "decision": decision, "reason": reason}


# ══════════════════════════════════════════════════════════════════
# Suggest fix after advisor rejection
# ══════════════════════════════════════════════════════════════════

class SuggestFixBody(BaseModel):
    request_id: str

@app.post("/api/suggest-fix")
async def api_suggest_fix(body: SuggestFixBody):

    req = db_get_request(body.request_id.upper())
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
    if req["advisor_decision"] != "rejected":
        raise HTTPException(status_code=400, detail="Request was not rejected by the advisor.")

    # Generate improved reason and plan addressing the advisor's rejection reason
    suggestions = suggest_fix(
        rejection_reason=req["advisor_reason"] or "No specific reason provided.",
        original_reason=req["reason"]          or "",
        original_plan=req["plan"]              or "",
        courses=req["courses"]                 or [],
    )

    return {
        "suggested_reason": suggestions["suggested_reason"],
        "suggested_plan":   suggestions["suggested_plan"],
        "courses":          req["courses"],
        "rejection_reason": req["advisor_reason"],
    }


# ══════════════════════════════════════════════════════════════════
# Registrar reply
# ══════════════════════════════════════════════════════════════════

@app.post("/api/registrar-reply")
async def api_registrar_reply(body: ReplyBody, background_tasks: BackgroundTasks):

    req = db_get_request(body.request_id.upper())
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
    if req["status"] != "pending_registrar":
        raise HTTPException(
            status_code=400,
            detail=f"Request is '{req['status']}', not 'pending_registrar'."
        )

    decision, reason = classify_advisor_reply(body.raw_email_body)
    final_status = "approved" if decision == "approved" else "rejected"

    db_update_status(
        req["request_id"],
        status=final_status,
        registrar_decision=decision,
        registrar_reason=reason,
        notify_push=True,
    )

    # Fetch fresh request from DB before sending email
    req_fresh = db_get_request(req["request_id"])
    background_tasks.add_task(_send_student_safe, req_fresh, final_status, reason)
    print(f"[Step 7] {req['request_id']} registrar: {final_status}")

    return {"ok": True, "decision": decision, "reason": reason}


# ══════════════════════════════════════════════════════════════════
# DEV — list all requests
# ══════════════════════════════════════════════════════════════════

@app.get("/api/requests")
async def api_list_requests():
    """Dev endpoint — shows all requests currently in the database."""
    return db_list_all()


@app.get("/")
async def root():
    return {
        "status":  "Fulbright Academic Workflow Agent is running",
        "api_docs": "http://localhost:8000/docs",
    }


# ══════════════════════════════════════════════════════════════════
# DIRECT RUN (alternative to uvicorn command)
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)