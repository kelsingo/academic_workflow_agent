// =============================================================
// ui.js — UI helpers
//
// These functions are used by chat.js and polling.js.
// If you change the HTML structure, update these functions.
// No API calls or state changes here — just rendering.
// =============================================================


// ── CHAT WIDGET TOGGLE ────────────────────────────────────────
function toggleChat() {
  STATE.chatOpen = !STATE.chatOpen;
  document.getElementById('chat-body').classList.toggle('collapsed', !STATE.chatOpen);
  document.getElementById('chevron').classList.toggle('open', STATE.chatOpen);
}


// ── TEXTAREA AUTO-RESIZE ──────────────────────────────────────
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 80) + 'px';
}


// ── CURRENT TIME STRING ───────────────────────────────────────
function nowStr() {
  return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}


// ── ADD A CHAT MESSAGE ────────────────────────────────────────
// role: 'agent' | 'user'
// html: innerHTML string (may contain tags)
function addMessage(role, html) {
  const wrap = document.getElementById('chat-messages');
  const row  = document.createElement('div'); row.className = `msg-row ${role}`;
  const av   = document.createElement('div'); av.className = `msg-avatar ${role}`; av.textContent = role === 'agent' ? 'OS' : 'ND';
  const col  = document.createElement('div');
  const bub  = document.createElement('div'); bub.className = 'msg-bubble'; bub.innerHTML = html;
  const meta = document.createElement('div'); meta.className = 'msg-meta';
  meta.textContent = (role === 'agent' ? 'One Stop Portal Virtual Agent • ' : '') + nowStr();
  col.appendChild(bub); col.appendChild(meta);
  row.appendChild(av); row.appendChild(col);
  wrap.appendChild(row);
  wrap.scrollTop = wrap.scrollHeight;
}


// ── TYPING INDICATOR ──────────────────────────────────────────
function showTyping() {
  const wrap = document.getElementById('chat-messages');
  const row  = document.createElement('div'); row.className = 'msg-row agent'; row.id = 'typing-row';
  const av   = document.createElement('div'); av.className = 'msg-avatar agent'; av.textContent = 'OS';
  const bub  = document.createElement('div'); bub.className = 'msg-bubble';
  bub.innerHTML = '<div class="typing-indicator"><div class="t-dot-anim"></div><div class="t-dot-anim"></div><div class="t-dot-anim"></div></div>';
  row.appendChild(av); row.appendChild(bub);
  wrap.appendChild(row);
  wrap.scrollTop = wrap.scrollHeight;
}
function hideTyping() { document.getElementById('typing-row')?.remove(); }


// ── AGENT REPLY (with typing delay) ──────────────────────────
// Returns a Promise — use `await agentReply(...)` to sequence messages
function agentReply(html, delay = 800) {
  return new Promise(resolve => {
    showTyping();
    setTimeout(() => { hideTyping(); addMessage('agent', html); resolve(); }, delay);
  });
}


// ── QUICK REPLY CHIPS ─────────────────────────────────────────
// labels: string[]
// onClick: each chip calls addMessage('user', label) + routeMessage(label)
function addChips(labels) {
  const bar = document.getElementById('quick-replies-bar');
  bar.innerHTML = '';
  labels.forEach(label => {
    const btn = document.createElement('button');
    btn.className = 'qr-chip'; btn.textContent = label;
    btn.onclick = () => { bar.innerHTML = ''; addMessage('user', label); routeMessage(label); };
    bar.appendChild(btn);
  });
}


// ── STATUS TRACKER HTML ───────────────────────────────────────
// Builds the multi-step progress tracker shown in the chat.
// Used by chat.js and polling.js.
// STEPS 4-8 — each step corresponds to a request lifecycle phase.
function buildTracker(status, advisorDec, registrarDec, deadline) {
  const steps = [
    { label: 'Request Submitted',  sub: '' },
    { label: 'Eligibility Verified', sub: '' },
    { label: 'Advisor Review',     sub: deadline ? `Deadline: ${fmtDeadline(deadline)}` : '' },
    { label: 'Registrar Review',   sub: '' },
    { label: 'Final Decision',     sub: '' },
  ];

  const activeMap = {
    pending_advisor:   2,
    pending_registrar: 3,
    approved:          4,
    rejected:          4,
  };
  const activeIdx = activeMap[status] ?? 2;

  const rows = steps.map((step, i) => {
    let dotClass, dotContent;
    if (i < activeIdx)        { dotClass = 'done';   dotContent = '✓'; }
    else if (i === activeIdx) {
      if (status === 'approved') { dotClass = 'done'; dotContent = '✓'; }
      else if (status === 'rejected') { dotClass = 'fail'; dotContent = '✕'; }
      else                       { dotClass = 'active'; dotContent = '●'; }
    } else                    { dotClass = 'wait';   dotContent = '○'; }

    return `<div class="t-step">
      <div class="t-dot ${dotClass}">${dotContent}</div>
      <div class="t-label">${step.label}${step.sub ? `<small>${step.sub}</small>` : ''}</div>
    </div>`;
  }).join('');

  return `<div class="tracker" style="margin-top:8px">
    <h4>📋 Request Status</h4>
    <div class="tracker-steps">${rows}</div>
  </div>`;
}

function fmtDeadline(iso) {
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}


// ── ELIGIBILITY ANIMATION ─────────────────────────────────────
// STEP 3 — purely visual; real check is done by backend
// Inserts an animated checklist into the chat message stream.
async function runEligibilityAnimation() {
  const checks = [
    { label: 'Loading student record…',       result: '✅ Student record found',            delay: 600 },
    { label: 'Verifying GPA requirement…',    result: '✅ GPA meets minimum (3.4)',          delay: 800 },
    { label: 'Checking course availability…', result: '✅ All courses available this term',  delay: 900 },
    { label: 'Calculating credit hours…',     result: '✅ Credit load within policy limits', delay: 700 },
  ];

  const wrap = document.createElement('div');
  wrap.className = 'elig-check';
  wrap.innerHTML = '<h4>🔍 Eligibility Verification</h4><div id="elig-rows"></div>';
  const rowsEl = wrap.querySelector('#elig-rows');

  // Inject into chat
  const msgWrap = document.getElementById('chat-messages');
  const row  = document.createElement('div'); row.className = 'msg-row agent';
  const av   = document.createElement('div'); av.className = 'msg-avatar agent'; av.textContent = 'OS';
  const col  = document.createElement('div');
  const bub  = document.createElement('div'); bub.className = 'msg-bubble';
  bub.appendChild(wrap); col.appendChild(bub); row.appendChild(av); row.appendChild(col);
  msgWrap.appendChild(row);

  for (const c of checks) {
    await new Promise(r => setTimeout(r, c.delay));
    const r = document.createElement('div'); r.className = 'elig-row';
    r.innerHTML = `<span class="elig-icon">⏳</span><span class="elig-text">${c.label}</span>`;
    rowsEl.appendChild(r); msgWrap.scrollTop = msgWrap.scrollHeight;
    await new Promise(r2 => setTimeout(r2, c.delay));
    r.innerHTML = `<span class="elig-icon">✅</span><span class="elig-text">${c.result}</span>`;
    msgWrap.scrollTop = msgWrap.scrollHeight;
  }
}


// ── PENDING REQUEST BANNER ────────────────────────────────────
// STEP 8 — shown at the top of the page when a request is active
function updateBanner(data) {
  const banner = document.getElementById('pending-banner');
  if (!data) { banner.classList.add('hidden'); return; }

  banner.classList.remove('hidden');
  const badge = document.getElementById('banner-badge');
  const sub   = document.getElementById('banner-sub');

  const labels = {
    pending_advisor:   ['⏳ Awaiting Advisor',   'Awaiting Advisor decision'],
    pending_registrar: ['📬 Awaiting Registrar',  'Advisor approved — Registrar reviewing'],
    approved:          ['✅ Approved',             'Your request has been approved!'],
    rejected:          ['❌ Not Approved',         'Your request was not approved'],
  };
  const [badgeText, subText] = labels[data.status] || ['Pending', 'Click to view'];
  badge.className  = `banner-badge ${data.status}`;
  badge.textContent = badgeText;
  sub.textContent  = `${subText} • Request ID: ${data.request_id}`;

  if (data.status === 'approved' || data.status === 'rejected') {
    setTimeout(() => banner.classList.add('hidden'), 8000);
  }
}

// Clicking the banner opens the chat and shows current status
function openChatToRequest() {
  if (!STATE.chatOpen) toggleChat();
  if (STATE.pendingRequest) {
    agentReply(
      `Here's the current status of your request <strong>#${STATE.pendingRequest.request_id}</strong>:` +
      buildTracker(STATE.pendingRequest.status, STATE.pendingRequest.advisor_decision, STATE.pendingRequest.registrar_decision, STATE.pendingRequest.deadline),
      400
    );
  }
}
