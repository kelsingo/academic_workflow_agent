// =============================================================
// api.js — All HTTP calls to the FastAPI backend
//
// Each function maps 1-to-1 with a backend endpoint.
// If the backend is offline, functions throw an error —
// the caller (chat.js) catches it and falls back to demo mode.
// =============================================================


// ── STEP 3: Student submits request ──────────────────────────
// Called by: chat.js → after eligibility animation passes
// Backend endpoint: POST /api/submit
// Returns: { request_id, status, deadline }
async function apiSubmitRequest(student, courses, reason, plan) {
  const resp = await fetch(`${CONFIG.API_BASE}/api/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student, courses, reason, plan }),
  });
  if (!resp.ok) throw new Error(`Submit failed: ${resp.status}`);
  return resp.json();
}


// ── STEP 8: Poll request status ──────────────────────────────
// Called by: polling.js every POLL_INTERVAL_MS
// Backend endpoint: GET /api/status/{request_id}
// Returns: { request_id, status, advisor_decision, advisor_reason,
//            registrar_decision, registrar_reason, deadline,
//            last_updated, notify_push }
async function apiGetStatus(requestId) {
  const resp = await fetch(`${CONFIG.API_BASE}/api/status/${requestId}`);
  if (!resp.ok) throw new Error(`Status fetch failed: ${resp.status}`);
  return resp.json();
}


// ── DEV ONLY: list all requests (backend debug endpoint) ─────
// Backend endpoint: GET /api/requests
async function apiListRequests() {
  const resp = await fetch(`${CONFIG.API_BASE}/api/requests`);
  if (!resp.ok) throw new Error('List failed');
  return resp.json();
}


// ── NOTE: The following are backend-only — no frontend call needed ──
//
// POST /api/advisor-reply   (Step 6 — triggered by email webhook, not UI)
// POST /api/registrar-reply (Step 7 — triggered by email webhook, not UI)
//
// The frontend just polls /api/status to learn about those decisions.
