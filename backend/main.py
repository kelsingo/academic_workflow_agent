"""
Fulbright Maximum Course Load Agent — FastAPI Backend
------------------------------------------------------
Endpoints:
  POST /api/submit        — Student submits course load request
  GET  /api/status/{id}   — Poll request status (used by frontend)
  POST /api/advisor-reply — Webhook: advisor email reply comes in here
  GET  /api/requests      — (dev) list all mock requests

Run with:
  pip install fastapi uvicorn anthropic exchangelib python-dotenv
  uvicorn main:app --reload --port 8000
"""

import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from email_service import send_advisor_email, send_student_email, send_registrar_email
from llm_classifier import classify_advisor_reply

load_dotenv()

app = FastAPI(title="Fulbright Course Load Agent")

# Allow frontend (any origin for dev; lock down in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory mock store (replace with DB later) ───────────────────────────
# Structure:
# requests[request_id] = {
#   "request_id": str,
#   "student": {...},
#   "courses": [...],
#   "reason": str,
#   "plan": str,
#   "status": "pending_advisor" | "pending_registrar" | "approved" | "rejected",
#   "advisor_decision": None | "approved" | "rejected",
#   "advisor_reason": str,
#   "registrar_decision": None | "approved" | "rejected",
#   "registrar_reason": str,
#   "submitted_at": ISO str,
#   "deadline": ISO str,
#   "last_updated": ISO str,
#   "notify_push": bool,   # whether to push browser notification
# }
requests: dict = {}


# ─── Models ─────────────────────────────────────────────────────────────────

class StudentInfo(BaseModel):
    student_name: str
    student_id: str
    email_address: str

class SubmitRequest(BaseModel):
    student: StudentInfo
    courses: list[str]
    reason: str
    plan: str
    advisor_email: str = os.getenv("ADVISOR_EMAIL", "advisor@fulbright.edu.vn")

class AdvisorReplyWebhook(BaseModel):
    request_id: str
    raw_email_body: str          # Full reply text — LLM will classify this
    advisor_email: Optional[str] = None


# ─── Helper ─────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def deadline_iso(hours: int = 48) -> str:
    return (datetime.utcnow() + timedelta(hours=hours)).isoformat() + "Z"


# ─── Routes ─────────────────────────────────────────────────────────────────

@app.post("/api/submit")
async def submit_request(body: SubmitRequest, background_tasks: BackgroundTasks):
    """
    1. Save request with status=pending_advisor
    2. Send Outlook email to advisor (background task)
    3. Return request_id to frontend for polling
    """
    request_id = str(uuid.uuid4())[:8].upper()

    requests[request_id] = {
        "request_id": request_id,
        "student": body.student.dict(),
        "courses": body.courses,
        "reason": body.reason,
        "plan": body.plan,
        "advisor_email": body.advisor_email,
        "status": "pending_advisor",
        "advisor_decision": None,
        "advisor_reason": None,
        "registrar_decision": None,
        "registrar_reason": None,
        "submitted_at": now_iso(),
        "deadline": deadline_iso(48),
        "last_updated": now_iso(),
        "notify_push": False,
    }

    # Send advisor email in background (non-blocking)
    background_tasks.add_task(
        send_advisor_email,
        request_id=request_id,
        student=body.student.dict(),
        courses=body.courses,
        reason=body.reason,
        plan=body.plan,
        advisor_email=body.advisor_email,
        deadline_hours=48,
    )

    print(f"[{now_iso()}] New request {request_id} from {body.student.student_name}")
    return {"request_id": request_id, "status": "pending_advisor", "deadline": requests[request_id]["deadline"]}


@app.get("/api/status/{request_id}")
async def get_status(request_id: str):
    """
    Frontend polls this every 30s.
    Returns current status + a push flag if a new decision just arrived.
    """
    req = requests.get(request_id.upper())
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    response = {
        "request_id": req["request_id"],
        "status": req["status"],
        "advisor_decision": req["advisor_decision"],
        "advisor_reason": req["advisor_reason"],
        "registrar_decision": req["registrar_decision"],
        "registrar_reason": req["registrar_reason"],
        "submitted_at": req["submitted_at"],
        "deadline": req["deadline"],
        "last_updated": req["last_updated"],
        "notify_push": req["notify_push"],
    }

    # Consume the push flag once read
    if req["notify_push"]:
        requests[request_id.upper()]["notify_push"] = False

    return response


@app.post("/api/advisor-reply")
async def advisor_reply(body: AdvisorReplyWebhook, background_tasks: BackgroundTasks):
    """
    Called when advisor email reply is received (via Outlook webhook or polling).
    LLM classifies the raw email body → approve / reject.
    """
    req = requests.get(body.request_id.upper())
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req["status"] != "pending_advisor":
        raise HTTPException(status_code=400, detail=f"Request is already '{req['status']}'")

    # Use LLM to classify
    decision, reason = await classify_advisor_reply(body.raw_email_body)
    print(f"[{now_iso()}] Advisor reply for {body.request_id}: {decision} — {reason}")

    req["advisor_decision"] = decision
    req["advisor_reason"] = reason
    req["last_updated"] = now_iso()
    req["notify_push"] = True   # triggers browser notification on next poll

    if decision == "approved":
        req["status"] = "pending_registrar"
        # Forward to registrar in background
        background_tasks.add_task(
            send_registrar_email,
            request_id=body.request_id,
            student=req["student"],
            courses=req["courses"],
            reason=req["reason"],
            advisor_decision="approved",
            registrar_email=os.getenv("REGISTRAR_EMAIL", "registrar@fulbright.edu.vn"),
        )
    else:
        req["status"] = "rejected"
        # Notify student of rejection
        background_tasks.add_task(
            send_student_email,
            student=req["student"],
            status="rejected",
            reason=f"Advisor: {reason}",
        )

    return {"ok": True, "decision": decision, "new_status": req["status"]}


@app.post("/api/registrar-reply")
async def registrar_reply(body: AdvisorReplyWebhook, background_tasks: BackgroundTasks):
    """
    Called when Registrar email reply is received.
    Same LLM classification flow.
    """
    req = requests.get(body.request_id.upper())
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req["status"] != "pending_registrar":
        raise HTTPException(status_code=400, detail=f"Request is '{req['status']}', not pending_registrar")

    decision, reason = await classify_advisor_reply(body.raw_email_body)
    print(f"[{now_iso()}] Registrar reply for {body.request_id}: {decision} — {reason}")

    req["registrar_decision"] = decision
    req["registrar_reason"] = reason
    req["last_updated"] = now_iso()
    req["notify_push"] = True
    req["status"] = "approved" if decision == "approved" else "rejected"

    # Notify student either way
    background_tasks.add_task(
        send_student_email,
        student=req["student"],
        status=req["status"],
        reason=reason if decision != "approved" else None,
    )

    return {"ok": True, "decision": decision, "new_status": req["status"]}


@app.get("/api/requests")
async def list_requests():
    """Dev endpoint — see all mock requests"""
    return list(requests.values())


@app.get("/")
async def root():
    return {"message": "Fulbright Course Load Agent API is running"}
