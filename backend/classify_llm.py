"""
Classify advisor reply + Suggest fixes
"""

import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# ── GEMINI CALL ────────────────────────────────────────────
def _call_gemini(prompt: str) -> str:
    """Send prompt to Gemini, return raw text response."""
    
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set in .env")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }
    body = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    resp = requests.post(GEMINI_URL, headers=headers, json=body, timeout=15)
    resp.raise_for_status()
    result = resp.json()

    if "candidates" not in result:
        raise RuntimeError(f"Gemini error: {result.get('error', 'unknown')}")

    return result["candidates"][0]["content"]["parts"][0]["text"].strip()


def _parse_json(blob: str) -> dict:
    blob = blob.strip()
    blob = re.sub(r"^```json\s*", "", blob)
    blob = re.sub(r"^```\s*",     "", blob)
    blob = re.sub(r"\s*```$",     "", blob)
    try:
        return json.loads(blob)
    except Exception:
        return {}


# ── CLASSIFY EMAIL REPLY ───────────────────────────────
CLASSIFY_PROMPT = """
You are processing an academic advisor's or registrar's email reply about a 
student's Maximum Course Load request at Fulbright University Vietnam.

Read the email and determine:
1. Whether they APPROVED or REJECTED the request
2. If rejected, extract the specific reason

Email body:
---
{email_body}
---

Respond in EXACTLY this format (two lines only, no extra text):
DECISION: approved
REASON: none

OR:
DECISION: rejected
REASON: <brief reason extracted from the email, max 2 sentences>
""".strip()


def classify_advisor_reply(raw_email_body: str) -> tuple[str, str | None]:
    """
    Classify a raw email reply as approved or rejected.
    Returns: ("approved", None) or ("rejected", "reason string")
    """
    prompt = CLASSIFY_PROMPT.format(email_body=raw_email_body[:2000])  # cap length

    try:
        text = _call_gemini(prompt)
        decision = "rejected"
        reason   = None

        for line in text.strip().split("\n"):
            line = line.strip()
            if line.upper().startswith("DECISION:"):
                val = line.split(":", 1)[1].strip().lower()
                decision = "approved" if "approv" in val else "rejected"
            elif line.upper().startswith("REASON:"):
                r = line.split(":", 1)[1].strip()
                reason = None if r.lower() in ("none", "n/a", "") else r

        print(f"[Classifier] Result: {decision} — {reason}")
        return decision, reason

    except Exception as e:
        print(f"[Classifier] Gemini failed, using keyword fallback: {e}")
        return _keyword_fallback(raw_email_body)


def _keyword_fallback(text: str) -> tuple[str, str | None]:
    lower = text.lower()
    for word in ["approve", "approved", "yes", "accepted", "grant", "okay", "agree"]:
        if word in lower:
            return "approved", None
    reason_match = re.search(
        r'(?:reason|because|due to|since|unfortunately)[:\s]+(.{10,150})',
        lower
    )
    reason = reason_match.group(1).strip() if reason_match else "See advisor email for details."
    return "rejected", reason


# ── SUGGEST FIX WHEN ADVISOR DENIES ─────────────────────
SUGGEST_FIX_PROMPT = """
You are an academic advisor assistant at Fulbright University Vietnam.

A student's Maximum Course Load request was REJECTED by their advisor.
Your job is to suggest improved versions of their reason and plan so they 
can resubmit a stronger application.

Rejection reason from advisor:
{rejection_reason}

Student's original reason:
{original_reason}

Student's original plan:
{original_plan}

Requested courses:
{courses}

Write improved versions that directly address the advisor's concern.
Be specific, practical, and encouraging. Keep each under 3 sentences.

Return ONLY a JSON object like:
{{
  "suggested_reason": "...",
  "suggested_plan": "..."
}}
""".strip()


def suggest_fix(
    rejection_reason: str,
    original_reason:  str,
    original_plan:    str,
    courses:          list,
) -> dict:
    """
    Use Gemini to suggest improved reason and plan after a rejection.
    Returns: { "suggested_reason": "...", "suggested_plan": "..." }
    """
    prompt = SUGGEST_FIX_PROMPT.format(
        rejection_reason=rejection_reason or "No specific reason given",
        original_reason=original_reason   or "Not specified",
        original_plan=original_plan       or "Not specified",
        courses=", ".join(courses)        if courses else "Not specified",
    )

    try:
        raw  = _call_gemini(prompt)
        data = _parse_json(raw)
        if "suggested_reason" in data and "suggested_plan" in data:
            print(f"[SuggestFix] Generated suggestions successfully")
            return data
        else:
            raise ValueError("Missing keys in Gemini response")
    except Exception as e:
        print(f"[SuggestFix] Gemini failed: {e}")
        # Generic fallback suggestions
        return {
            "suggested_reason": (
                f"I need to complete these courses ({', '.join(courses)}) to stay on track "
                f"for graduation. I have carefully reviewed the advisor's concerns and believe "
                f"I can handle this load with proper support."
            ),
            "suggested_plan": (
                "I will attend all office hours, form a weekly study group, "
                "and proactively communicate with each instructor about my progress. "
                "I will also reduce extracurricular commitments this semester."
            ),
        }


# ── QUICK TEST ────────────────────────────────────────────────────
if __name__ == "__main__":
    test_email = """
    Hi, thanks for reaching out.
    After reviewing the student's academic record, I'm denying this request.
    The student has a GPA below the required threshold and I don't think 
    taking 5 courses simultaneously is advisable at this time.
    Best regards,
    Dr. Smith
    """
    decision, reason = classify_advisor_reply(test_email)
    print(f"Decision: {decision}, Reason: {reason}")

    if decision == "rejected":
        fix = suggest_fix(
            rejection_reason=reason,
            original_reason="I need to graduate on time",
            original_plan="Study hard",
            courses=["CS101", "CS204", "CORE101"],
        )
        print("Suggested fix:", fix)
