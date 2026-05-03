// =============================================================
// state.js — Global application state
// Single source of truth shared across all JS modules.
// Do not import browser APIs here — just plain data.
// =============================================================

const STATE = {
  // Chat widget open/collapsed
  chatOpen: true,

  // Current step in the course load request flow:
  //   idle | collecting | checking | advisor_wait | registrar_wait | done
  step: 'idle',

  // Whether the agent is currently typing (blocks user input)
  typing: false,

  // Interval handle for polling (Step 8)
  pollTimer: null,

  // Student info from login (Step 1) or mock (config.js)
  // TODO (Login step): set this after auth
  student: { ...CONFIG.MOCK_STUDENT },

  // Active request persisted from localStorage (Steps 4-8)
  // Structure mirrors the backend /api/status response:
  // { request_id, status, advisor_decision, advisor_reason,
  //   registrar_decision, registrar_reason, deadline, last_updated }
  pendingRequest: null,
};
