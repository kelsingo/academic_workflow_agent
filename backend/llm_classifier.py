"""
llm_classifier.py — Use Claude to classify advisor/registrar email replies
---------------------------------------------------------------------------
Install:  pip install anthropic
Set in .env:  ANTHROPIC_API_KEY=sk-ant-...

The classifier reads the raw email reply body and returns:
  ("approved", reason_or_none)  or  ("rejected", reason_string)
"""

import os
import re
import anthropic


_client = None

def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
        _client = anthropic.AsyncAnthropic(api_key=api_key)
    return _client


async def classify_advisor_reply(raw_email_body: str) -> tuple[str, str | None]:
    """
    Given raw email text from an advisor or registrar, return:
      ("approved", None)           — if they approved
      ("rejected", "reason text")  — if they rejected, with extracted reason

    Falls back to simple keyword matching if LLM call fails.
    """
    client = _get_client()

    prompt = f"""You are classifying an academic advisor's email reply about a student's 
Maximum Course Load request. Read the email and determine if they APPROVED or REJECTED it.

Email body:
---
{raw_email_body}
---

Respond in this exact format:
DECISION: approved
REASON: none

OR:
DECISION: rejected  
REASON: <brief reason extracted from the email>

Only output those two lines. Nothing else."""

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )

        text = message.content[0].text.strip()
        lines = text.split("\n")

        decision = "rejected"
        reason = "No reason provided"

        for line in lines:
            if line.upper().startswith("DECISION:"):
                val = line.split(":", 1)[1].strip().lower()
                if "approv" in val:
                    decision = "approved"
                else:
                    decision = "rejected"
            elif line.upper().startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
                if reason.lower() in ("none", "n/a", ""):
                    reason = None

        print(f"[LLM] Classified reply: {decision} — {reason}")
        return decision, reason

    except Exception as e:
        print(f"[LLM ERROR] Falling back to keyword match: {e}")
        return _keyword_fallback(raw_email_body)


def _keyword_fallback(text: str) -> tuple[str, str | None]:
    """Simple keyword-based fallback if LLM is unavailable."""
    lower = text.lower()

    approve_words = ["approve", "approved", "yes", "accepted", "grant", "ok", "okay", "agree"]
    reject_words  = ["deny", "denied", "reject", "rejected", "decline", "no", "not approved", "cannot"]

    for word in approve_words:
        if word in lower:
            return "approved", None

    for word in reject_words:
        if word in lower:
            # Try to extract reason after common phrases
            reason_match = re.search(
                r'(?:reason|because|due to|since)[:\s]+(.{10,120})',
                lower
            )
            reason = reason_match.group(1).strip() if reason_match else "See advisor email for details."
            return "rejected", reason

    # Ambiguous — treat as rejected and flag for human review
    return "rejected", "Reply was ambiguous — please contact advisor directly."
