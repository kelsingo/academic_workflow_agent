# Fulbright Maximum Course Load Agent

## Project Structure
```
fulbright_agent/
├── frontend/
│   └── index.html          ← Open this in browser (or Live Server)
└── backend/
    ├── main.py             ← FastAPI app (API endpoints)
    ├── email_service.py    ← Outlook email via exchangelib
    ├── llm_classifier.py   ← Claude API: classify advisor reply
    ├── requirements.txt
    └── .env.example        ← Copy to .env and fill in credentials
```

---

## Quick Start

### 1. Frontend only (demo mode — no backend needed)
Just open `frontend/index.html` in your browser or with Live Server.
The agent works fully in demo/simulation mode using localStorage.

---

### 2. Full stack (with real Outlook emails + LLM)

#### Step 1 — Set up backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

#### Step 2 — Fill in .env
```
ANTHROPIC_API_KEY=sk-ant-...          # From console.anthropic.com
OUTLOOK_EMAIL=agent@fulbright.edu.vn  # The sending email account
OUTLOOK_PASSWORD=your-app-password    # Use an App Password, not your real password
OUTLOOK_SERVER=outlook.office365.com  # Or your Exchange server
ADVISOR_EMAIL=advisor@fulbright.edu.vn
REGISTRAR_EMAIL=registrar@fulbright.edu.vn
```

#### Step 3 — Run backend
```bash
uvicorn main:app --reload --port 8000
```
API docs available at: http://localhost:8000/docs

#### Step 4 — Open frontend
Open `frontend/index.html` with Live Server (port 5500).
The frontend calls `http://localhost:8000` by default.

---

## How It Works

### Student Flow
1. Student submits course IDs, reason, plan via chat
2. Frontend shows animated eligibility check (UI only)
3. `POST /api/submit` — backend saves request, sends Outlook email to advisor
4. Frontend receives `request_id`, saves to **localStorage**, starts **polling** every 30s
5. Student can close the browser — request persists

### When Advisor Replies
1. Advisor replies to the Outlook email
2. Your email monitoring script (or webhook) calls `POST /api/advisor-reply` with the raw email body
3. Claude (LLM) classifies the reply as **approved** or **rejected** with reason
4. Backend updates status, sets `notify_push: true`
5. Next poll from frontend picks up the change → **browser push notification** + **toast** + chat message

### Email Monitoring (you need to wire this up)
The simplest approach: a cron script that polls the inbox:

```python
# poll_inbox.py — run every 5 minutes via cron or scheduler
import requests
from exchangelib import Account, Credentials, Configuration, DELEGATE, Q

def check_inbox():
    # Connect to Outlook inbox
    account = ...  # same setup as email_service.py
    
    # Look for replies with [request_id] in subject
    for item in account.inbox.filter(is_read=False):
        subject = item.subject or ''
        # Extract request_id from subject line
        import re
        match = re.search(r'\(ID:\s*([A-Z0-9]+)\)', subject)
        if match:
            request_id = match.group(1)
            body = item.text_body or item.body or ''
            # Call backend webhook
            requests.post('http://localhost:8000/api/advisor-reply', json={
                'request_id': request_id,
                'raw_email_body': body,
            })
            item.is_read = True
            item.save()
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/submit` | Submit new course load request |
| GET | `/api/status/{id}` | Poll request status |
| POST | `/api/advisor-reply` | Webhook: advisor email reply |
| POST | `/api/registrar-reply` | Webhook: registrar email reply |
| GET | `/api/requests` | Dev: list all requests |

---

## Notes
- The in-memory store in `main.py` resets on server restart. Replace `requests: dict` with a real DB (SQLite/PostgreSQL) for production.
- For Office 365 with MFA, use an **App Password** (account settings → Security → App passwords).
- CORS is open (`*`) for development — restrict to your frontend domain in production.
