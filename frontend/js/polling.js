// =============================================================
// How it works:
//   1. After a request is submitted, startPolling(request_id) is called.
//   2. Every POLL_INTERVAL_MS, the frontend calls GET /api/status/{id}.
//   3. If the status has changed, onStatusChanged() fires:
//      - Updates the status tracker in the chat
//      - Shows a browser push notification
//      - Shows an in-page toast
//   4. Polling stops automatically when status is final (approved/rejected).
// =============================================================


// ── START POLLING ─────────────────────────────────────────────
function startPolling(requestId) {
  stopPolling();  // clear any existing timer first
  STATE.pollTimer = setInterval(() => pollOnce(requestId), CONFIG.POLL_INTERVAL_MS);
  console.log(`[Polling] Started for request ${requestId} every ${CONFIG.POLL_INTERVAL_MS / 1000}s`);
}

// ── STOP POLLING ──────────────────────────────────────────────
function stopPolling() {
  if (STATE.pollTimer) {
    clearInterval(STATE.pollTimer);
    STATE.pollTimer = null;
    console.log('[Polling] Stopped');
  }
}

// ── SINGLE POLL ──────────────────────────────────────────────
async function pollOnce(requestId) {
  try {
    const data = await apiGetStatus(requestId);
    handleStatusUpdate(data);
  } catch (e) {
    // Backend unreachable — silently ignore, try again next interval
    console.warn('[Polling] Backend unreachable:', e.message);
  }
}

// ── HANDLE STATUS UPDATE ─────────────────────────────────────
// Called each poll cycle. Only reacts when status actually changes.
function handleStatusUpdate(data) {
  const prevStatus = STATE.pendingRequest?.status;

  // Persist latest state
  storageSaveRequest(data);
  updateBanner(data);

  // No change — do nothing
  if (data.status === prevStatus) return;

  console.log(`[Polling] Status changed: ${prevStatus} → ${data.status}`);
  onStatusChanged(data, prevStatus);

  // Stop polling once the request is resolved
  if (data.status === 'approved' || data.status === 'rejected') {
    stopPolling();
  }
}

// ── REACT TO STATUS CHANGE ───────────────────────────────────
// STEP 6 (advisor) + STEP 7 (registrar) outcomes arrive here
function onStatusChanged(data, prevStatus) {
  const name = STATE.student?.student_name || 'Student';

  // ── STEP 6a: Advisor approved → now pending registrar ──────
  if (data.status === 'pending_registrar') {
    notifyToast('✅', 'Advisor Decision Received', 'Your advisor approved your request. Forwarding to Registrar…');
    notifyPush('Advisor Approved', 'Your course load request has been approved by your advisor.');

    if (STATE.step === 'advisor_wait') {
      agentReply(`🎉 <strong>Your advisor approved your request!</strong><br>The system is forwarding it to the <strong>Registrar's Office</strong> for final review.`);
      STATE.step = 'registrar_wait';
      addMessage('agent', buildTracker(data.status, data.advisor_decision, null, data.deadline));
    }
  }

  // ── STEP 6b / STEP 7b: Final approval ──────────────────────
  else if (data.status === 'approved') {
    notifyToast('🎓', 'Request Approved!', 'Your Maximum Course Load has been fully approved.');
    notifyPush('Course Load Approved!', 'You are now authorized to register for up to 20 credit hours.');

    if (STATE.step === 'advisor_wait' || STATE.step === 'registrar_wait') {
      agentReply(
        `<span class="sbadge ok">🎓 APPROVED</span><br><br>` +
        `Dear <strong>${name}</strong>,<br><br>` +
        `Your <strong>Maximum Course Load Request</strong> has been officially approved by the Registrar.<br><br>` +
        `You are now authorized to register for up to <strong>20 credit hours</strong> this term.<br><br>` +
        `A confirmation email has been sent to your Fulbright email address.<br><br>` +
        `<em>Best regards,<br>Fulbright Academic Automated System</em>`
      );
      STATE.step = 'done';
      addChips(['Submit another request', 'Done ✓']);
      storageClearRequest();
    }
  }

  // ── STEP 6b / STEP 7b: Rejection at any stage ──────────────
  else if (data.status === 'rejected') {
    const reason = data.registrar_reason || data.advisor_reason || 'Please contact your advisor for details.';
    notifyToast('❌', 'Request Not Approved', reason);
    notifyPush('Course Load Request Rejected', reason);

    if (STATE.step === 'advisor_wait' || STATE.step === 'registrar_wait') {
      agentReply(
        `<span class="sbadge err">❌ NOT APPROVED</span><br><br>` +
        `Dear <strong>${name}</strong>,<br><br>` +
        `Your <strong>Maximum Course Load Request</strong> has been rejected.<br><br>` +
        `<strong>Reason:</strong> ${reason}<br><br>` +
        `You may resubmit after addressing the concerns, or visit the Registrar's Office.<br><br>` +
        `<em>Best regards,<br>Fulbright Academic Automated System</em>`
      );
      STATE.step = 'done';
      addChips(['Submit new request', 'Contact registrar']);
      storageClearRequest();
    }
  }
}


// ── BROWSER PUSH NOTIFICATIONS ───────────────────────────────
// STEP 8 — push notification when student is away from the page
async function requestNotifPermission() {
  if (!('Notification' in window)) return;
  if (Notification.permission === 'default') {
    await Notification.requestPermission();
  }
}

function notifyPush(title, body) {
  if (Notification.permission === 'granted') {
    new Notification(title, { body, icon: '/favicon.ico' });
  }
}


// ── IN-PAGE TOAST ─────────────────────────────────────────────
// STEP 8 — visible toast when student is on the page
let _toastTimer;
function notifyToast(icon, title, body) {
  document.getElementById('toast-icon').textContent  = icon;
  document.getElementById('toast-title').textContent = title;
  document.getElementById('toast-body').textContent  = body;
  document.getElementById('toast').classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(hideToast, 6000);
}
function hideToast() {
  document.getElementById('toast').classList.remove('show');
}
