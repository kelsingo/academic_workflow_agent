// =============================================================
// config.js — Central configuration
// Change API_BASE to your deployed backend URL when ready.
// =============================================================

const CONFIG = {
  // ── STEP 2: Connect UI ↔ Backend ─────────────────────────────
  // TODO: Replace with your real FastAPI URL
  API_BASE: 'http://localhost:8000',

  // How often the frontend polls the backend for status updates (ms)
  // STEP 8 — polling is how the UI stays in sync
  POLL_INTERVAL_MS: 30000,   // 30 seconds

  // localStorage key to persist request across browser sessions
  LS_KEY: 'fulbright_course_request',

  // Mock student data — replace with real login session (Step 1)
  // TODO: pull this from auth session instead
  MOCK_STUDENT: {
    student_name:  'Nguyen Van A',
    student_id:    '220110',
    email_address: 'a.nguyen@student.fulbright.edu.vn',
  },
};
