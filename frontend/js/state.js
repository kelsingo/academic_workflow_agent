// =============================================================
// Single file shared across all JS modules.
// =============================================================

const STATE = {
  // Chat widget open/collapsed
  chatOpen: true,

  // Current step in the course load request flow:
  step: 'idle',

  // Whether the agent is currently typing (blocks user input)
  typing: false,

  // Interval handle for polling
  pollTimer: null,

  // Student info from login (Step 1) or mock (config.js)
  // TODO (Login step): set this after auth
  student: { ...CONFIG.MOCK_STUDENT },

  // Active request persisted from localStorage
  pendingRequest: null,
};
