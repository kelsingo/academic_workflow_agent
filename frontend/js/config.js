// =============================================================
// config.js — Central configuration
// =============================================================

const CONFIG = {
  // ── STEP 2: Connect UI - Backend ─────────────────────────────
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
    student_name:  'Phan Thi Son',
    student_id:    25418,     
    email_address: 'son.phan.25418@student.fulbright.edu.vn',
  },
};
