# Fulbright Frontend — Developer Guide

## File Structure
```
frontend/
├── web.html          - HTML
├── css/
│   └── styles.css      - CSS
└── js/
    ├── config.js       - API URL, constants            (edit this first)
    ├── state.js        - Global STATE object
    ├── storage.js      - localStorage helpers          (Step 4)
    ├── api.js          - All fetch() calls to backend  (Step 2)
    ├── ui.js           - DOM helpers, tracker, toasts  (Step 8)
    ├── polling.js      - Status polling + push notifs  (Step 8)
    └── chat.js         - Chat flow & routing logic     (Steps 3-7)
```

---

## How to Run

```
# Open with VS Code Live Server:
# Or just double-click index.html
```

---

## Step-by-Step Guide

### Step 2 — Connect UI to Backend (Khue + Ngan)
1. Open `js/config.js`
2. Change `API_BASE` to your FastAPI server URL (e.g. `http://localhost:8000`)
3. Test: open browser console, run `apiListRequests()` — should return `[]`

---

### Step 3 — Student Submit (An)
The entry point is `handleCollecting()` in `chat.js`.

Currently uses **regex** to parse the student's text. When Thai An's backend
LLM extraction endpoint is ready, replace the regex block with:

```javascript
// ── REPLACE THIS BLOCK in handleCollecting() ──────────────────
// OLD (regex):
const courseMatch = text.match(...);
const courses = courseMatch ? ... : [];

// NEW (LLM endpoint — Step 3a):
const extracted = await fetch(`${CONFIG.API_BASE}/api/extract`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text }),
}).then(r => r.json());

// extracted = { courses, reason, plan, is_valid, errors }

if (!extracted.is_valid) {
  await agentReply(`⚠️ ${extracted.errors[0]}`);
  return;
}
const { courses, reason, plan } = extracted;
```

---

### Step 4 — Create Request in Database (Khue)
`submitToBackend()` in `chat.js` already calls `POST /api/submit`.
When your database is ready on the backend, no frontend changes needed —
just make sure the backend saves the request and returns:
```json
{ "request_id": "ABC123", "status": "pending_advisor", "deadline": "2026-04-10T..." }
```

---

### Step 5 — Send Email to Advisor (Ngan)
This is fully handled by (`send_email.py`).

---

### Step 6 — Advisor Reply (Ngan)
When the advisor replies and the backend processes it:
1. Backend updates `status` to `pending_registrar` or `rejected`
2. Backend sets `notify_push: true` in the status response
3. Frontend's `pollOnce()` in `polling.js` picks it up automatically
4. `onStatusChanged()` fires → shows + push notification + chat message

**For the "suggest improvements" popup** (Step 6b):
- The rejection reason comes from `data.advisor_reason` (extracted by LLM)
- The frontend shows it in `handleAdvisorWait()` in `chat.js`
- The "suggest improvements" chip triggers `handleAdvisorWait()` with text `'suggest improvement'`
- **TODO**: swap the hardcoded suggestion text with a real API call to your LLM suggestion endpoint

---

### Step 7 — Registrar Reply
Same pattern as Step 6 — handled by `handleRegistrarWait()` in `chat.js`.
No changes needed beyond what's already there.

---

### Step 8 — Notify Student on UI
Already implemented in `polling.js`:
- `startPolling(request_id)` — starts 30s polling loop
- `notifyToast()` — in-page notification
- `notifyPush()` — browser push notification (requires user permission)
- `updateBanner()` — top-of-page status banner

---

## STATE.step Values

| Value | Meaning |
|-------|---------|
| `idle` | No active flow |
| `collecting` | Waiting for student to enter course IDs/reason/plan |
| `checking` | Eligibility animation running (automated) |
| `advisor_wait` | Request submitted, polling for advisor reply |
| `registrar_wait` | Advisor approved, polling for registrar reply |
| `done` | Final outcome shown |

---

## Script Load Order
Scripts must load in this exact order:
```
config.js → state.js → storage.js → api.js → ui.js → polling.js → chat.js
```
Each file depends on the ones before it.
