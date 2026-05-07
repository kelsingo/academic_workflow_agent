// =============================================================
// All HTTP calls to the FastAPI backend
//
// Each function maps 1-to-1 with a backend endpoint.
// If the backend is offline, functions throw an error —
// the caller (chat.js) catches it and falls back to demo mode.
// =============================================================


// Student submits request 
async function apiSubmitRequest(student_id, courses, reason, plan) {
  const resp = await fetch(`${CONFIG.API_BASE}/api/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student_id, courses, reason, plan }),
  });
  if (!resp.ok) throw new Error(`Submit failed: ${resp.status}`);
  return resp.json();
}


// Poll request status 
async function apiGetStatus(requestId) {
  const resp = await fetch(`${CONFIG.API_BASE}/api/status/${requestId}`);
  if (!resp.ok) throw new Error(`Status fetch failed: ${resp.status}`);
  return resp.json();
}


// list all requests 
async function apiListRequests() {
  const resp = await fetch(`${CONFIG.API_BASE}/api/requests`);
  if (!resp.ok) throw new Error('List failed');
  return resp.json();
}
