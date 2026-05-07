// =============================================================
// Keeps the active request in localStorage so students can close
// the browser and return to see the same status.
//
// Only CLEARS final requests:
// - Approved by registrar
// - Rejected by registrar
// =============================================================


// Only clears if status is truly FINAL (approved or registrar rejected)
function storageSaveRequest(data) {
  // Only clear truly final statuses
  const isFinalApproval = data.status === 'approved';
  const isRegistrarRejection = data.status === 'rejected' && data.registrar_decision === 'rejected';
  
  if (isFinalApproval || isRegistrarRejection) {
    // These are truly final - don't save
    storageClearRequest();
  } else {
    // Keep: pending_advisor, pending_registrar, or advisor rejection
    localStorage.setItem(CONFIG.LS_KEY, JSON.stringify(data));
    STATE.pendingRequest = data;
  }
}

// Load request from localStorage on page load
// Returns parsed object or null if nothing saved
function storageLoadRequest() {
  try {
    const data = JSON.parse(localStorage.getItem(CONFIG.LS_KEY));
    if (!data) return null;
    
    // Clear only truly final requests
    const isFinalApproval = data.status === 'approved';
    const isRegistrarRejection = data.status === 'rejected' && data.registrar_decision === 'rejected';
    
    if (isFinalApproval || isRegistrarRejection) {
      storageClearRequest();
      return null;
    }
    
    return data;
  } catch {
    return null;
  }
}

// Clear request after it is fully resolved (approved or rejected)
function storageClearRequest() {
  localStorage.removeItem(CONFIG.LS_KEY);
  STATE.pendingRequest = null;
}
