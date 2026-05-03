// =============================================================
// storage.js — localStorage helpers
//
// Keeps the active request in localStorage so students can close
// the browser and return to see the same status.
//
// When you switch to a real database (Step 4), you can keep using
// these functions as a local cache — they don't need to change.
// =============================================================


// Save/overwrite the current active request
function storageSaveRequest(data) {
  localStorage.setItem(CONFIG.LS_KEY, JSON.stringify(data));
  STATE.pendingRequest = data;
}

// Load request from localStorage on page load
// Returns parsed object or null if nothing saved
function storageLoadRequest() {
  try {
    return JSON.parse(localStorage.getItem(CONFIG.LS_KEY));
  } catch {
    return null;
  }
}

// Clear request after it is fully resolved (approved or rejected)
function storageClearRequest() {
  localStorage.removeItem(CONFIG.LS_KEY);
  STATE.pendingRequest = null;
}
