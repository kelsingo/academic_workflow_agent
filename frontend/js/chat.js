// =============================================================
// Chat flow logic
// =============================================================


// INPUT HANDLERS 
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


// Dispatches to the correct handler based on STATE.step
async function routeMessage(text) {
  STATE.typing = true;
  document.getElementById('send-btn').disabled = true;

  const lower = text.toLowerCase();

  if      (STATE.step === 'idle')              await handleIdle(text, lower);
  else if (STATE.step === 'collecting')        await handleCollecting(text, lower);
  else if (STATE.step === 'checking')          { /* automated */ }
  else if (STATE.step === 'confirm_submission') await handleConfirmSubmission(text, lower);
  else if (STATE.step === 'advisor_wait')      await handleAdvisorWait(text, lower);
  else if (STATE.step === 'rejected_advisor')  await handleRejectedAdvisor(text, lower);
  else if (STATE.step === 'suggestion_review') await handleSuggestionReview(text, lower);
  else if (STATE.step === 'registrar_wait')    await handleRegistrarWait(text, lower);
  else                                         await handleDone(text, lower);

  STATE.typing = false;
  document.getElementById('send-btn').disabled = false;
}


// IDLE
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

  else {
    await agentReply(`I cannot help with that right now. Please submit a course load request.`);
    addChips(['Submit course load request']);
  }
}


// COLLECTING student input 
async function handleCollecting(text, lower) {
  STATE.step = 'checking';

  // Validate that the input is specifically about submitting maximum course load requests
  const submitKeywords = ['submit', 'maximum', 'course load', 'overload', 'request courses'];
  const hasSubmitKeyword = submitKeywords.some(kw => lower.includes(kw));
  
  // Also check for course IDs in the text (e.g., CS101, IS202)
  const courseIdPattern = /[A-Z]{2,4}\d{3}/i;
  const hasCourseIds = courseIdPattern.test(text);
  
  if (!hasSubmitKeyword && !hasCourseIds) {
    STATE.step = 'collecting';
    await agentReply(`I cannot handle that. Please provide a valid course load request with course IDs, reason, and plan.<br><br><em>Format: "Course IDs: CS101, CS204 | Reason: ... | Plan: ..."</em>`, 500);
    return;
  }

  // Call LLM extraction endpoint 
  let extracted;
  try {
    const resp = await fetch(`${CONFIG.API_BASE}/api/extract`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        text,
        student_id: STATE.student.student_id,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    extracted = await resp.json();
  } catch (e) {
    console.warn('[Extract] API call failed:', e.message);
    // Fallback to regex if backend is offline (demo mode)
    extracted = _regexFallback(text);
  }

  // Handle validation errors from backend 
  // Errors include: missing fields, course not in DB, too many courses
  if (!extracted.is_valid) {
    STATE.step = 'collecting';
    const errorMsg = extracted.errors?.[0] || 'Please check your input and try again.';
    await agentReply(`${errorMsg}<br><br>Please revise and re-enter your request.`, 500);
    return;
  }

  // All good: store and proceed to confirmation
  STATE._collected = {
    courses: extracted.courses,
    reason:  extracted.reason  || 'Not specified',
    plan:    extracted.plan    || 'Not specified',
  };

  // Show confirmation message
  STATE.step = 'confirm_submission';
  await agentReply(
    `<strong>Please confirm your request:</strong><br><br>` +
    `<strong>Courses:</strong> ${extracted.courses.join(', ')}<br>` +
    `<strong>Reason:</strong> ${extracted.reason}<br>` +
    `<strong>Plan:</strong> ${extracted.plan}<br><br>` +
    `Do you want to submit this request?`,
    700
  );
  addChips(['Yes, submit', 'No, cancel']);
}

// Regex fallback used when backend is offline (demo mode only)
function _regexFallback(text) {
  const courseMatch = text.match(/(?:course[_ ]?ids?:?\s*)([A-Z0-9,\s]+?)(?:\||reason|plan|$)/i);
  const reasonMatch = text.match(/reason:?\s*([^|]+?)(?:\||plan|$)/i);
  const planMatch   = text.match(/plan:?\s*([^|]+?)$/i);
  const courses     = courseMatch ? courseMatch[1].trim().split(/[\s,]+/).filter(c => c.length > 2) : [];
  if (courses.length < 1) return { is_valid: false, courses: [], errors: ['Could not detect course IDs. Please use the format: "Course IDs: CS101, CS204 | Reason: ... | Plan: ..."'] };
  return { is_valid: true, courses, reason: reasonMatch?.[1]?.trim() || 'Not specified', plan: planMatch?.[1]?.trim() || 'Not specified', errors: [] };
}


// Submit request to backend
async function submitToBackend(courses, reason, plan) {
  STATE.step = 'advisor_wait';

  try {
    const data = await apiSubmitRequest(
      STATE.student.student_id,   // backend looks up full student info from DB
      courses, reason, plan
    );

    const saved = { ...data, student: STATE.student };
    storageSaveRequest(saved);
    updateBanner(saved);
    startPolling(data.request_id);

    await agentReply(
      `<strong>Request submitted!</strong> Your advisor has been notified via email with a 48-hour deadline.<br><br>` +
      `<span class="deadline-pill">Advisor deadline: 48 hours</span>` +
      buildTracker('pending_advisor', null, null, data.deadline),
      700
    );

    await requestNotifPermission();
    await agentReply(
      `You'll receive a <strong>push notification</strong> and an <strong>email</strong> when your advisor responds — even if you close this page.`,
      600
    );

  } catch (e) {
    // Check if this is an eligibility failure (HTTP 400)
    if (e.message && e.message.includes('400')) {
      STATE.step = 'collecting';
      // Try to get the error detail from the response
      await agentReply(
        `<strong>Your request could not be submitted.</strong><br><br>` +
        `This may be due to insufficient available credits or a registration deadline issue.<br>` +
        `Please contact your academic advisor for clarification.`,
        600
      );
      return;
    }

    // Demo/offline fallback 
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
      `<span class="deadline-pill">Advisor deadline: 48 hours</span>` +
      buildTracker('pending_advisor', null, null, mockDeadline),
      700
    );
    addChips(['Simulate: Advisor Approves', 'Simulate: Advisor Denies', 'Check status']);
  }
}


// ══════════════════════════════════════════════════════════════════
// CONFIRM SUBMISSION
// User confirms or cancels the request before submitting
// ══════════════════════════════════════════════════════════════════
async function handleConfirmSubmission(text, lower) {
  
  // User confirms submission
  if (lower.includes('yes') || lower.includes('submit') || lower.includes('confirm')) {
    if (!STATE._collected) {
      STATE.step = 'collecting';
      await agentReply(`Let me start over. Please provide your course IDs, reason, and plan.`);
      return;
    }

    STATE.step = 'checking';
    
    // UI: Animated eligibility display
    await runEligibilityAnimation();
    await new Promise(r => setTimeout(r, 400));
    await agentReply(`<span class="sbadge ok">✅ Eligible</span> All checks passed! Submitting your request…`, 600);

    // Submit to backend 
    await submitToBackend(STATE._collected.courses, STATE._collected.reason, STATE._collected.plan);
    return;
  }

  // User cancels
  if (lower.includes('no') || lower.includes('cancel')) {
    STATE.step = 'collecting';
    STATE._collected = null;
    await agentReply(`No problem. Please revise your request and re-enter it.<br><br><em>Format: "Course IDs: CS101, CS204 | Reason: ... | Plan: ..."</em>`, 600);
    return;
  }

  // Unclear response
  await agentReply(`Please confirm: do you want to submit this request?`);
  addChips(['Yes, submit', 'No, cancel']);
}


// ══════════════════════════════════════════════════════════════════
// ADVISOR WAIT
// This handler manages:
//   - "Check status" user queries
//   - The full rejection flow (suggest fix -> resubmit)
//   - Demo simulation chips for testing without real email
// ══════════════════════════════════════════════════════════════════
async function handleAdvisorWait(text, lower) {

  // Check status 
  if (lower.includes('check') || lower.includes('status')) {
    const req = storageLoadRequest();
    await agentReply(
      `Your request is <strong>awaiting your advisor's decision</strong>. ` +
      `You'll be notified automatically when they respond.<br>` +
      buildTracker('pending_advisor', null, null, req?.deadline)
    );
    addChips(['Simulate: Advisor Approves', 'Simulate: Advisor Denies']);
    return;
  }

  // DEMO: Simulate advisor approval
  if (lower.includes('simulate') && lower.includes('approv')) {
    STATE.step = 'registrar_wait';
    const req = storageLoadRequest();
    if (req) {
      req.status = 'pending_registrar';
      req.advisor_decision = 'approved';
      storageSaveRequest(req);
      updateBanner(req);
    }
    notifyToast('✅', 'Advisor Approved', 'Your request is forwarding to Registrar…');
    await agentReply(
      `<strong>Your advisor approved your request!</strong><br>` +
      `The system is forwarding it to the <strong>Registrar's Office</strong> for final review.<br><br>` +
      buildTracker('pending_registrar', 'approved', null, req?.deadline), 800
    );
    addChips(['Simulate: Registrar Approves', 'Simulate: Registrar Rejects']);
    return;
  }

  // DEMO: Simulate advisor rejection 
  if (lower.includes('simulate') && (lower.includes('den') || lower.includes('reject'))) {
    const req = storageLoadRequest();
    const mockReason = 'GPA does not meet the minimum requirement for maximum course load this semester.';
    if (req) {
      req.status = 'rejected';
      req.advisor_decision = 'rejected';
      req.advisor_reason = mockReason;
      storageSaveRequest(req);
      updateBanner(req);
    }
    // Trigger the same rejection UI as a real rejection from polling
    await _showRejectionFlow(mockReason);
    return;
  }

  await agentReply(`Your request is with your advisor. You'll be notified automatically when they respond.`);
  addChips(['Check status', 'Simulate: Advisor Approves', 'Simulate: Advisor Denies']);
}


// Rejection flow (used by both real polling + demo) 
async function _showRejectionFlow(reason) {
  STATE.step = 'rejected_advisor';
  notifyToast('❌', 'Advisor Decision', 'Your request was not approved by your advisor.');

  await agentReply(
    `<strong>Your advisor has not approved your request.</strong><br><br>` +
    `<strong>Reason:</strong> ${reason || 'No specific reason provided.'}<br><br>` +
    `Would you like the AI to suggest how to improve your reason and plan so you can resubmit?`,
    800
  );
  addChips(['Yes, suggest improvements ✨', 'No, I\'ll revise myself', 'Cancel']);
}


// Student responses after rejection 
async function handleRejectedAdvisor(text, lower) {

  // Student wants AI suggestions 
  if (lower.includes('yes') && lower.includes('suggest')) {
    const req = storageLoadRequest();
    if (!req?.request_id) {
      await agentReply(`Sorry, I couldn't find your request. Please resubmit from scratch.`);
      STATE.step = 'idle';
      addChips(['Submit course load request']);
      return;
    }

    await agentReply(`Let me generate improved suggestions based on your advisor's feedback…`, 500);

    let suggestions;
    try {
      const resp = await fetch(`${CONFIG.API_BASE}/api/suggest-fix`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ request_id: req.request_id }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      suggestions = await resp.json();
    } catch (e) {
      console.warn('[SuggestFix] API failed, using generic:', e.message);
      // Offline fallback
      suggestions = {
        suggested_reason: 'I need to complete these courses to remain on track for graduation. I have reviewed the advisor\'s concerns and am committed to maintaining academic performance.',
        suggested_plan:   'I will attend all office hours weekly, reduce extracurricular commitments, form a study group, and send weekly progress updates to each instructor.',
        courses: req.courses || [],
      };
    }

    // Store suggestions in STATE for use when student confirms
    STATE._suggestions = {
      courses:        suggestions.courses || req.courses || [],
      reason:         suggestions.suggested_reason,
      plan:           suggestions.suggested_plan,
      rejection_reason: suggestions.rejection_reason,
    };

    await agentReply(
      `✨ <strong>Here are the AI-suggested improvements:</strong><br><br>` +
      `<strong>Improved Reason:</strong><br>` +
      `<div style="background:#f0f7ff;padding:8px 10px;border-radius:6px;margin:4px 0 10px;font-size:.82rem">` +
      `${suggestions.suggested_reason}</div>` +
      `<strong>Improved Plan:</strong><br>` +
      `<div style="background:#f0f7ff;padding:8px 10px;border-radius:6px;margin:4px 0">` +
      `${suggestions.suggested_plan}</div><br>` +
      `Would you like to resubmit with these suggestions, or edit them first?`,
      900
    );
    addChips(['Resubmit with these suggestions', 'Let me edit first', 'Cancel']);
    STATE.step = 'suggestion_review';
    return;
  }

  // Student will revise on their own 
  if (lower.includes('no') || lower.includes('myself')) {
    STATE.step = 'collecting';
    storageClearRequest();
    await agentReply(
      `No problem! Please re-enter your request with an updated reason and plan.<br><br>` +
      `<em>Format: "Course IDs: CS101, CS204, CORE101 | Reason: ... | Plan: ..."</em>`,
      600
    );
    return;
  }

  // Cancel 
  if (lower.includes('cancel')) {
    STATE.step = 'idle';
    storageClearRequest();
    await agentReply(`Understood. Your request has been closed. Feel free to start a new one anytime.`);
    addChips(['Submit course load request']);
    return;
  }

  await agentReply(`Would you like AI suggestions, or would you prefer to revise your request yourself?`);
  addChips(['Yes, suggest improvements ✨', 'No, I\'ll revise myself', 'Cancel']);
}


//  Review AI suggestions 
async function handleSuggestionReview(text, lower) {

  // Accept suggestions and resubmit
  if (lower.includes('resubmit') || lower.includes('yes')) {
    if (!STATE._suggestions) {
      STATE.step = 'collecting';
      await agentReply(`Let's start fresh. Please enter your course IDs, reason, and plan.`);
      return;
    }
    // Jump straight to submitToBackend with the AI-suggested values
    STATE.step = 'checking';
    await agentReply(`Resubmitting with the improved reason and plan…`, 500);
    await runEligibilityAnimation();
    await new Promise(r => setTimeout(r, 300));
    await agentReply(`<span class="sbadge ok">✅ Eligible</span> Submitting updated request…`, 500);
    await submitToBackend(
      STATE._suggestions.courses,
      STATE._suggestions.reason,
      STATE._suggestions.plan,
    );
    STATE._suggestions = null;
    return;
  }

  // Student wants to edit suggestions first 
  if (lower.includes('edit') || lower.includes('first')) {
    STATE.step = 'collecting';
    STATE._prefill = STATE._suggestions;   // ui hint for pre-filled input
    storageClearRequest();
    await agentReply(
      `Sure! The AI suggestions have been pre-filled as a starting point.<br><br>` +
      `Please type your updated request in this format:<br>` +
      `<em>"Course IDs: ${(STATE._suggestions?.courses || []).join(', ')} | Reason: [your reason] | Plan: [your plan]"</em>`,
      600
    );
    STATE._suggestions = null;
    return;
  }

  // Cancel 
  if (lower.includes('cancel')) {
    STATE.step = 'idle';
    storageClearRequest();
    STATE._suggestions = null;
    await agentReply(`Understood. Feel free to start a new request anytime.`);
    addChips(['Submit course load request']);
    return;
  }

  addChips(['Resubmit with these suggestions', 'Let me edit first', 'Cancel']);
}


// STEP 7: REGISTRAR WAIT
async function handleRegistrarWait(text, lower) {

  if (lower.includes('check') || lower.includes('status')) {
    const req = storageLoadRequest();
    await agentReply(
      `Your request is <strong>with the Registrar's Office</strong> for final review.<br>` +
      buildTracker('pending_registrar', 'approved', null, req?.deadline)
    );
    addChips(['Simulate: Registrar Approves', 'Simulate: Registrar Rejects']);
    return;
  }

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
      `A confirmation email has also been sent to your Fulbright email address.<br><br>` +
      `<em>Best regards,<br>Fulbright Academic Automated System</em>`, 900
    );
    storageClearRequest();
    addChips(['Submit another request', 'Done ✓']);
    STATE.step = 'idle';
    return;
  }

  if (lower.includes('simulate') && lower.includes('reject')) {
    STATE.step = 'done';
    const req = storageLoadRequest();
    const mockReason = 'Academic standing requirements not met for this term.';
    if (req) { req.status = 'rejected'; req.registrar_decision = 'rejected'; storageSaveRequest(req); updateBanner(req); }
    notifyToast('❌', 'Request Rejected', 'The Registrar did not approve your request.');
    await agentReply(
      `<span class="sbadge err">NOT APPROVED</span><br><br>` +
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
