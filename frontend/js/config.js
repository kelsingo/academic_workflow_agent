// =============================================================
// Central configuration
// =============================================================

const CONFIG = {
  // Connect UI - Backend 
  API_BASE: 'http://localhost:8000',

  // How often the frontend polls the backend for status updates (ms)
  POLL_INTERVAL_MS: 30000,   // 30 seconds

  // localStorage key to persist request across browser sessions
  LS_KEY: 'fulbright_course_request',

  // Mock student data — replace with real login session (Step 1)
  // TODO: pull this from auth session instead
  MOCK_STUDENT: {
    student_name:  'Duong Hoang Ngan',
    student_id:    25418,     
    email_address: 'ngan.duong.220221@student.fulbright.edu.vn',
  },
};
