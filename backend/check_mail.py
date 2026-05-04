"""
Check Gmail inbox for advisor/registrar replies (run in a second terminal)

How it works:
  1. Every 30s, connects to Gmail via IMAP and checks for UNREAD email whose subject contains a known Request ID
  2. Determines if the sender is an advisor or registrar
  3. Calls the local FastAPI: POST /api/advisor-reply   or   POST /api/registrar-reply
  4. Marks the email as READ so it won't be processed again
"""

import imaplib
import email
import email.header
import time
import re
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ────────────────────────────────────────────────────────
GMAIL_SENDER       = os.environ.get("SENDER_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("SENDER_PASSWORD")
BACKEND_URL        = 'http://localhost:8000'
REGISTRAR_EMAIL    = os.environ.get("REGISTRAR_EMAIL")
POLL_INTERVAL_SEC  = 30
IMAP_HOST          = "imap.gmail.com"

# Regex to find Request ID anywhere in subject or body
REQUEST_ID_PATTERN = re.compile(r'\b(REQ[A-Z0-9]{4,8})\b')


# ── IMAP CONNECTION ───────────────────────────────────────────────
def connect_imap() -> imaplib.IMAP4_SSL:
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
    mail.select("inbox")
    return mail


# ── DECODE EMAIL HEADER ───────────────────────────────────────────
def decode_header(raw: str) -> str:
    parts = email.header.decode_header(raw or "")
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded)


# ── EXTRACT PLAIN TEXT BODY ───────────────────────────────────────
def extract_body(msg: email.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp  = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp:
                charset = part.get_content_charset() or "utf-8"
                body += part.get_payload(decode=True).decode(charset, errors="replace")
    else:
        charset = msg.get_content_charset() or "utf-8"
        body = msg.get_payload(decode=True).decode(charset, errors="replace")
    return body.strip()


# ── FIND REQUEST ID ───────────────────────────────────────────────
def find_request_id(subject: str, body: str) -> str | None:
    for text in (subject, body):
        match = REQUEST_ID_PATTERN.search(text)
        if match:
            return match.group(1)
    return None


# ── DETERMINE SENDER ROLE ─────────────────────────────────────────
def get_sender_role(sender_email: str) -> str | None:
    """
    Returns 'registrar' if sender is the registrar email.
    Returns 'advisor' for anyone else (advisors can have various emails).
    Returns None if sender is our own system (ignore loop emails).
    """
    sender_lower = sender_email.lower().strip()

    # Ignore our own system emails to avoid infinite loops
    if sender_lower == GMAIL_SENDER.lower():
        return None

    if sender_lower == REGISTRAR_EMAIL:
        return "registrar"

    # Everyone else who replies is treated as an advisor
    return "advisor"


# ── CALL BACKEND WEBHOOK ──────────────────────────────────────────
def notify_backend(role: str, request_id: str, body: str) -> bool:
    endpoint = f"{BACKEND_URL}/api/{role}-reply"
    try:
        resp = requests.post(
            endpoint,
            json={"request_id": request_id, "raw_email_body": body},
            timeout=10,
        )
        if resp.ok:
            print(f"[Poller] ✅ Notified backend: {role} reply for {request_id}")
            return True
        else:
            print(f"[Poller] ❌ Backend returned {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[Poller] ❌ Could not reach backend: {e}")
        return False


# ── MARK EMAIL AS READ ────────────────────────────────────────────
def mark_as_read(mail: imaplib.IMAP4_SSL, uid: str):
    mail.uid("store", uid, "+FLAGS", "\\Seen")


# ── SINGLE POLL CYCLE ─────────────────────────────────────────────
def poll_once():
    try:
        mail = connect_imap()
    except Exception as e:
        print(f"[Poller] IMAP login failed: {e}")
        return

    # Search for UNREAD emails only
    status, data = mail.uid("search", None, "UNSEEN")
    if status != "OK" or not data[0]:
        mail.logout()
        return

    uids = data[0].split()
    print(f"[Poller] {datetime.now().strftime('%H:%M:%S')} — Found {len(uids)} unread email(s)")

    for uid in uids:
        try:
            status, msg_data = mail.uid("fetch", uid, "(RFC822)")
            if status != "OK":
                continue

            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject = decode_header(msg.get("Subject", ""))
            sender  = email.utils.parseaddr(msg.get("From", ""))[1]
            body    = extract_body(msg)

            print(f"[Poller]   From: {sender} | Subject: {subject[:60]}")

            # ── Determine who sent this ───────────────────────────
            role = get_sender_role(sender)
            if role is None:
                print(f"[Poller]   Skipping — sender is our own system")
                mark_as_read(mail, uid)
                continue

            # ── Find Request ID in subject or body ────────────────
            request_id = find_request_id(subject, body)
            if not request_id:
                print(f"[Poller]   No Request ID found — skipping")
                # Don't mark as read — might be a non-system email
                continue

            print(f"[Poller]   Role: {role} | Request ID: {request_id}")

            # ── Notify backend ────────────────────────────────────
            success = notify_backend(role, request_id, body)
            if success:
                mark_as_read(mail, uid)

        except Exception as e:
            print(f"[Poller]   Error processing email uid={uid}: {e}")

    mail.logout()


# ── MAIN LOOP ─────────────────────────────────────────────────────
def main():
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        print("GMAIL_SENDER and GMAIL_APP_PASSWORD must be set in .env")
        return

    print(f"[Poller] Starting Gmail inbox poller")
    print(f"[Poller] Inbox: {GMAIL_SENDER}")
    print(f"[Poller] Backend: {BACKEND_URL}")
    print(f"[Poller] Registrar email: {REGISTRAR_EMAIL}")
    print(f"[Poller] Polling every {POLL_INTERVAL_SEC}s — press Ctrl+C to stop\n")

    while True:
        poll_once()
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
