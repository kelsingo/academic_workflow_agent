// =============================================================
// chat.js — Chat flow logic
//
//   Step 2 (connect UI ↔ backend)
//   Step 3 (student submit)
//   Step 3a (extract + check LLM)
//   Step 4 (create request in DB)
//   Step 5 (send email)       
//   Step 6 (advisor reply)
//
// Flow steps:
//   idle → collecting → checking → advisor_wait → registrar_wait → done
// =============================================================


// ── INPUT HANDLERS ────────────────────────────────────────────
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendUserMessage(); }
}

function sendUserMessage() {
  const inp  = document.getElementById('chat-input');
  const text = inp.value.trim();
  if (!text || STATE.typing) return;
  inp.value = ''; inp.style.height = 'auto';
  document.getElementById('quick-replies-bar').innerHTML = '';
  addMessage('user', text);
  routeMessage(text);
}


// ── MAIN ROUTER ───────────────────────────────────────────────
// Dispatches to the correct handler based on STATE.step
async function routeMessage(text) {
  STATE.typing = true;
  document.getElementById('send-btn').disabled = true;

  const lower = text.toLowerCase();

  if      (STATE.step === 'idle')            await handleIdle(text, lower);
  else if (STATE.step === 'collecting')      await handleCollecting(text, lower);
  else if (STATE.step === 'checking')        { /* checking is automated, no user input */ }
  else if (STATE.step === 'advisor_wait')    await handleAdvisorWait(text, lower);
  else if (STATE.step === 'registrar_wait')  await handleRegistrarWait(text, lower);
  else                                       await handleDone(text, lower);

  STATE.typing = false;
  document.getElementById('send-btn').disabled = false;
}


// ── STEP: IDLE ────────────────────────────────────────────────
async function handleIdle(text, lower) {
  if (lower.includes('maximum') || lower.includes('course load') || lower.includes('submit request') || lower.includes('overload')) {
    STATE.step = 'collecting';
    await agentReply(
      `Sure! I can help you submit a <strong>Maximum Course Load Request</strong>.<br><br>` +
      `Please provide the following in your next message:<br>` +
      `• <strong>Course IDs</strong> (e.g. CS101, CS204, CORE101, IS101, IS202)<br>` +
      `• <strong>Reason</strong> for the extra load<br>` +
      `• <strong>Plan</strong> to manage your workload<br><br>` +
      `<em>Format: "Course IDs: CS101, CS204 | Reason: ... | Plan: ..."</em>`, 900
    );
  }

  else if (lower.includes('hello') || lower.includes('hi') || lower.includes('xin')) {
    await agentReply(`Hello! 👋 How can I help you today? I can assist with course load requests, academic policies, registration, and more.`);
    addChips(['Submit course load request', 'Check my courses', 'Academic calendar']);
  }

  else if (lower.includes('check') || lower.includes('status')) {
    // ── STEP 8: Student returns and checks status ─────────────
    const req = storageLoadRequest();
    if (req) {
      await agentReply(
        `Here's the current status of your request <strong>#${req.request_id}</strong>:` +
        buildTracker(req.status, req.advisor_decision, req.registrar_decision, req.deadline), 600
      );
      // Restore correct step
      STATE.step = req.status === 'pending_registrar' ? 'registrar_wait' : 'advisor_wait';
      if (req.request_id.startsWith('MOCK')) {
        addChips(['Simulate: Advisor Approves', 'Simulate: Advisor Denies', 'Check status']);
      }
    } else {
      await agentReply(`You don't have an active request. Would you like to submit one?`);
      addChips(['Submit course load request']);
    }
  }

  else {
    await agentReply(`I can help with that! For course load requests, try <em>"Submit maximum course load request"</em>. For other inquiries, I'm happy to assist.`);
    addChips(['Submit course load request', 'Browse knowledge', 'Check my courses']);
  }
}


// ── STEP 3: COLLECTING student input ─────────────────────────
//
// TODO:
//   Replace the regex parsing here with a call to your LLM extraction endpoint:
//   POST /api/extract  →  { courses, reason, plan, is_valid, errors }
//   If is_valid=false, show errors[0] as the error message below.
async function handleCollecting(text, lower) {
  // ── Parse student input (currently regex — swap for LLM API call) ──
  const courseMatch = text.match(/(?:course[_ ]?ids?:?\s*)([A-Z0-9,\s]+?)(?:\||reason|plan|$)/i);
  const reasonMatch = text.match(/reason:?\s*([^|]+?)(?:\||plan|$)/i);
  const planMatch   = text.match(/plan:?\s*([^|]+?)$/i);
  const courses     = courseMatch ? courseMatch[1].trim().split(/[\s,]+/).filter(c => c.length > 2) : [];

  if (courses.length < 1) {
    // ── STEP 3b: course not found in database → ask to re-enter ──
    await agentReply(
      `I couldn't detect your course IDs. Please use the format:<br>` +
      `<em>"Course IDs: CS101, CS204 | Reason: ... | Plan: ..."</em>`
    );
    return;
  }

  const reason = reasonMatch ? reasonMatch[1].trim() : 'Not specified';
  const plan   = planMatch   ? planMatch[1].trim()   : 'Not specified';

  // Store parsed data for use in next step
  STATE._collected = { courses, reason, plan };

  STATE.step = 'checking';
  await agentReply(`Got it! Running eligibility checks for <strong>${courses.length}</strong> courses…`, 500);

  // ── STEP 3 UI: Animated eligibility display ──────────────────
  // Note: Real eligibility check is done on the backend.
  // This animation is UI-only. If backend returns an error (Step 3c),
  // call agentReply() with the error and reset STATE.step = 'collecting'.
  await runEligibilityAnimation();
  await new Promise(r => setTimeout(r, 400));
  await agentReply(`<span class="sbadge ok">✅ Eligible</span> All checks passed! Submitting your request…`, 600);

  // ── STEP 3 → STEP 4: Submit to backend ───────────────────────
  await submitToBackend(courses, reason, plan);
}


// ── STEP 4: Submit request to backend + start tracking ────────
//
// Calls POST /api/submit.
// On success: saves to localStorage, starts polling, shows tracker.
// On failure: falls back to demo mode with a MOCK request ID.
async function submitToBackend(courses, reason, plan) {
  STATE.step = 'advisor_wait';

  try {
    const data = await apiSubmitRequest(STATE.student, courses, reason, plan);

    // ── STEP 4: Save request to localStorage ──────────────────
    const saved = { ...data, student: STATE.student };
    storageSaveRequest(saved);
    updateBanner(saved);

    // ── STEP 8: Start polling for status changes ───────────────
    startPolling(data.request_id);

    // ── STEP 5: Email has been sent (backend confirms) ─────────
    await agentReply(
      `<strong>Request submitted!</strong> Your advisor has been notified via email with a 48-hour deadline.<br><br>` +
      `<span class="deadline-pill">⏰ Advisor deadline: 48 hours</span>` +
      buildTracker('pending_advisor', null, null, data.deadline),
      700
    );

    // Request browser notification permission (Step 8)
    await requestNotifPermission();
    await agentReply(
      `🔔 You'll receive a <strong>push notification</strong> and an <strong>email</strong> when your advisor responds — even if you close this page.`,
      600
    );

  } catch (e) {
    // ── DEMO MODE: backend offline ────────────────────────────
    console.warn('[Submit] Backend offline, using mock:', e.message);
    const mockId       = 'MOCK' + Math.random().toString(36).slice(2, 6).toUpperCase();
    const mockDeadline = new Date(Date.now() + 48 * 3600 * 1000).toISOString();
    const saved = {
      request_id: mockId, status: 'pending_advisor',
      deadline: mockDeadline, advisor_decision: null,
      registrar_decision: null, student: STATE.student,
    };
    storageSaveRequest(saved);
    updateBanner(saved);

    await agentReply(
      `<strong>Request submitted (demo mode)</strong><br>` +
      `<small style="color:var(--light)">Backend offline — mock ID: ${mockId}</small><br><br>` +
      `<span class="deadline-pill">⏰ Advisor deadline: 48 hours</span>` +
      buildTracker('pending_advisor', null, null, mockDeadline),
      700
    );
    await agentReply(
      `In production, your advisor receives an Outlook email and the system polls for their reply automatically.`,
      800
    );
    addChips(['Simulate: Advisor Approves', 'Simulate: Advisor Denies', 'Check status']);
  }
}


// ── STEP 6: ADVISOR WAIT ──────────────────────────────────────
//
// In production: polling.js handles real advisor replies automatically.
// The chips below are for demo/simulation only.
async function handleAdvisorWait(text, lower) {
  if (lower.includes('simulate') && lower.includes('approv')) {
    // Simulate advisor approval
    STATE.step = 'registrar_wait';
    const req = storageLoadRequest();
    if (req) { req.status = 'pending_registrar'; req.advisor_decision = 'approved'; storageSaveRequest(req); updateBanner(req); }
    await agentReply(
      `✅ <strong>Advisor approved!</strong> Forwarding to Registrar's Office…<br>` +
      buildTracker('pending_registrar', 'approved', null, req?.deadline), 800
    );
    addChips(['Simulate: Registrar Approves', 'Simulate: Registrar Rejects']);
  }

  else if (lower.includes('simulate') && (lower.includes('den') || lower.includes('reject'))) {
    // ── STEP 6b: Advisor denied ───────────────────────────────
    // TODO: When backend sends rejection with reason:
    //   1. Extract reason from email (done in backend llm_classifier.py)
    //   2. Show popup: "Do you want to fix and resubmit?"
    //   3. If yes: LLM suggests edits → reset STATE.step = 'collecting'
    STATE.step = 'done';
    const req = storageLoadRequest();
    if (req) { req.status = 'rejected'; req.advisor_decision = 'rejected'; storageSaveRequest(req); updateBanner(req); }
    storageClearRequest();
    await agentReply(
      `❌ <strong>Advisor denied the request.</strong><br><br>` +
      `Reason: Student's current academic standing does not meet the requirement for maximum course load.<br><br>` +
      `Would you like the AI to suggest how to improve your application?`, 800
    );
    addChips(['Yes, suggest improvements', 'No, I will contact my advisor', 'Submit new request']);
    STATE.step = 'idle';
  }

  else if (lower.includes('suggest improvement')) {
    // ── STEP 6b: LLM suggests fixes ──────────────────────────
    // TODO: Call LLM with the rejection reason
    // and student's original reason/plan to suggest improvements.
    await agentReply(
      `💡 Based on the advisor's feedback, here are some suggestions:<br><br>` +
      `• Strengthen your <strong>workload plan</strong> — add specific weekly schedules<br>` +
      `• Show evidence of prior success with heavy loads<br>` +
      `• Get written support from at least one instructor<br><br>` +
      `Would you like to revise and resubmit your request?`, 900
    );
    addChips(['Yes, let me revise', 'No thanks']);
    STATE.step = 'idle';
  }

  else if (lower.includes('yes, let me revise')) {
    STATE.step = 'collecting';
    await agentReply(`Sure! Please re-enter your course IDs, updated reason, and revised plan.`, 600);
  }

  else if (lower.includes('status') || lower.includes('check')) {
    const req = storageLoadRequest();
    await agentReply(
      `Your request is currently <strong>awaiting your advisor's decision</strong>.<br>` +
      buildTracker('pending_advisor', null, null, req?.deadline)
    );
    addChips(['Simulate: Advisor Approves', 'Simulate: Advisor Denies']);
  }

  else {
    await agentReply(`Your request is with your advisor. You'll be notified automatically when they respond.`);
    addChips(['Simulate: Advisor Approves', 'Simulate: Advisor Denies', 'Check status']);
  }
}


// ── STEP 7: REGISTRAR WAIT ────────────────────────────────────
// In production: polling.js handles real registrar replies.
async function handleRegistrarWait(text, lower) {
  if (lower.includes('simulate') && lower.includes('approv')) {
    STATE.step = 'done';
    const req  = storageLoadRequest();
    const name = STATE.student?.student_name || 'Student';
    if (req) { req.status = 'approved'; req.registrar_decision = 'approved'; storageSaveRequest(req); updateBanner(req); }
    notifyToast('🎓', 'Request Approved!', 'Your Maximum Course Load has been approved.');
    notifyPush('Request Approved!', 'You are authorized to register for up to 20 credit hours.');
    await agentReply(
      `<span class="sbadge ok">🎓 FULLY APPROVED</span><br><br>` +
      `Dear <strong>${name}</strong>,<br><br>` +
      `Your <strong>Maximum Course Load Request</strong> has been officially approved by the Registrar's Office.<br><br>` +
      `You are now authorized to register for up to <strong>20 credit hours</strong> this term.<br><br>` +
      `A confirmation email has been sent to your Fulbright email address.<br><br>` +
      `<em>Best regards,<br>Fulbright Academic Automated System</em>`, 900
    );
    storageClearRequest();
    addChips(['Submit another request', 'Done ✓']);
    STATE.step = 'idle';
  }

  else if (lower.includes('simulate') && lower.includes('reject')) {
    STATE.step = 'done';
    const req = storageLoadRequest();
    if (req) { req.status = 'rejected'; req.registrar_decision = 'rejected'; storageSaveRequest(req); updateBanner(req); }
    notifyToast('❌', 'Request Rejected', 'The Registrar did not approve your request.');
    await agentReply(
      `<span class="sbadge err">❌ NOT APPROVED</span><br><br>` +
      `The Registrar's Office has rejected your request.<br><br>` +
      `<strong>Reason:</strong> Academic standing requirements not met for this term.<br><br>` +
      `A notification email has been sent. Please visit the Registrar's Office for further guidance.`, 900
    );
    storageClearRequest();
    addChips(['Submit new request', 'Contact registrar']);
    STATE.step = 'idle';
  }

  else {
    await agentReply(`Your request is with the Registrar's Office for final review.`);
    addChips(['Simulate: Registrar Approves', 'Simulate: Registrar Rejects']);
  }
}


// ── DONE ──────────────────────────────────────────────────────
async function handleDone(text, lower) {
  STATE.step = 'idle';
  await agentReply(`Is there anything else I can help you with?`);
  addChips(['Submit course load request', 'Check my courses', 'Browse knowledge']);
}
