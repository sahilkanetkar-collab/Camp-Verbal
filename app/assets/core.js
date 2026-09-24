/* Camp Verbal — shared app core (loaded on every /app page after config.js and supabase) */
(function () {
  'use strict';
  const cfg = window.CV_CONFIG || {};
  const configured = cfg.supabaseUrl && !/PASTE_/.test(cfg.supabaseUrl) && cfg.supabaseAnonKey && !/PASTE_/.test(cfg.supabaseAnonKey);

  const CREST = '<svg viewBox="0 0 200 220" aria-hidden="true"><defs><linearGradient id="cvg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#F0C567"/><stop offset="55%" stop-color="#EBA036"/><stop offset="100%" stop-color="#C77F22"/></linearGradient></defs><path d="M100 6 L188 6 Q194 6 194 12 L194 118 Q194 162 100 214 Q6 162 6 118 L6 12 Q6 6 12 6 Z" fill="url(#cvg)"/><path d="M100 16 L181 16 Q184 16 184 19 L184 115 Q184 154 100 202 Q16 154 16 115 L16 19 Q16 16 19 16 Z" fill="#930047"/><path d="M100 38 L128 76 L113 76 L100 60 L87 76 L72 76 Z" fill="url(#cvg)"/><text x="100" y="148" text-anchor="middle" font-family="Fraunces, Georgia, serif" font-weight="900" font-size="86" fill="url(#cvg)" letter-spacing="-4">CV</text></svg>';

  const sb = configured ? window.supabase.createClient(cfg.supabaseUrl, cfg.supabaseAnonKey, {
    auth: { persistSession: true, autoRefreshToken: true, flowType: 'implicit',
            // Only the login page reads the token that arrives from an email login link.
            detectSessionInUrl: /\/login\.html$/.test(location.pathname) }
  }) : null;

  // ── text helpers ──
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  // Plain text → paragraphs; keeps line breaks. Content is always escaped.
  const para = s => {
    const t = String(s == null ? '' : s).replace(/\r/g, '').trim();
    if (!t) return '';
    return t.split(/\n{2,}/).map(p => '<p>' + esc(p).replace(/\n/g, '<br>') + '</p>').join('');
  };
  const fmtClock = sec => {
    sec = Math.max(0, Math.floor(sec));
    const h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60;
    return (h ? h + ':' + String(m).padStart(2, '0') : String(m).padStart(2, '0')) + ':' + String(s).padStart(2, '0');
  };
  const fmtDur = sec => {
    sec = Math.max(0, Math.round(sec || 0));
    const m = Math.floor(sec / 60), s = sec % 60;
    return m ? m + 'm ' + String(s).padStart(2, '0') + 's' : s + 's';
  };
  const fmtIST = iso => {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }) + ' IST';
    } catch (e) { return iso; }
  };
  const num = v => (v == null ? '–' : (Math.round(Number(v) * 100) / 100).toString());
  const qs = new URLSearchParams(location.search);

  // ── UI helpers ──
  function toast(msg, bad) {
    const t = document.createElement('div');
    t.className = 'toast' + (bad ? ' bad' : '');
    t.setAttribute('role', 'status');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), bad ? 5200 : 3200);
  }
  // In-page confirm (never window.confirm). Resolves true/false.
  function ask(title, bodyHtml, okLabel, opts) {
    opts = opts || {};
    return new Promise(res => {
      const o = document.createElement('div');
      o.className = 'overlay';
      o.innerHTML = '<div class="modal" role="dialog" aria-modal="true" aria-labelledby="mdl-t"><h3 id="mdl-t">' + esc(title) + '</h3><div class="body">' + (bodyHtml || '') +
        '</div><div class="actions">' + (opts.noCancel ? '' : '<button class="btn" data-a="0">' + esc(opts.cancelLabel || 'Cancel') + '</button>') +
        '<button class="btn ' + (opts.danger ? 'btn-danger' : 'btn-gold') + '" data-a="1">' + esc(okLabel || 'OK') + '</button></div></div>';
      const done = v => { o.remove(); document.removeEventListener('keydown', onKey); res(v); };
      const onKey = e => { if (e.key === 'Escape' && !opts.noCancel) done(false); };
      o.addEventListener('click', e => { const a = e.target.getAttribute && e.target.getAttribute('data-a'); if (a != null) done(a === '1'); });
      document.addEventListener('keydown', onKey);
      document.body.appendChild(o);
      o.querySelector('[data-a="1"]').focus();
    });
  }
  function loading(el, msg) { el.innerHTML = '<div class="center-load"><span class="spinner"></span>' + esc(msg || 'Loading…') + '</div>'; }

  // ── data ──
  function friendly(err) {
    const m = (err && (err.message || err.error_description || err.msg)) || String(err || 'Something went wrong.');
    if (/Failed to fetch|NetworkError|Load failed/i.test(m)) return 'Can’t reach the server. Check your connection and try again.';
    if (/JWT|jwt expired|invalid claim/i.test(m)) return 'Your session expired. Please log in again.';
    return m;
  }
  async function rpc(fn, args) {
    if (!sb) throw new Error('The app is not connected to its database yet (see config.js).');
    const { data, error } = await sb.rpc(fn, args || {});
    if (error) { const e = new Error(friendly(error)); e.code = error.code; throw e; }
    return data;
  }
  async function session() {
    if (!sb) return null;
    const { data } = await sb.auth.getSession();
    return data.session || null;
  }
  async function requireUser() {
    const s = await session();
    if (!s) {
      location.replace('login.html?next=' + encodeURIComponent(location.pathname.split('/').pop() + location.search));
      return new Promise(() => {});
    }
    return s.user;
  }
  async function logout() {
    try { await sb.auth.signOut(); } catch (e) { /* ignore */ }
    location.href = 'login.html';
  }

  // ── header ──
  function header(opts) {
    opts = opts || {};
    const h = document.createElement('header');
    h.className = 'hdr no-print';
    h.innerHTML = '<a class="brand" href="index.html" aria-label="Camp Verbal library">' + CREST +
      '<span><b>CAMP VERBAL</b><small>' + esc(opts.label || 'Practice') + '</small></span></a>' +
      '<div class="hdr-right">' + (opts.email ? '<span class="who">' + esc(opts.email) + '</span>' : '') +
      (opts.email && !/progress\.html$/.test(location.pathname) ? '<a class="btn btn-sm" href="progress.html">My progress</a>' : '') +
      (opts.admin ? '<a class="btn btn-sm" href="admin.html">Admin</a>' : '') +
      (opts.email ? '<button class="btn btn-sm" id="cv-logout">Log out</button>' : '') + '</div>';
    document.body.prepend(h);
    const lo = h.querySelector('#cv-logout');
    if (lo) lo.addEventListener('click', logout);
    return h;
  }
  function notConfigured(el) {
    el.innerHTML = '<div class="wrap narrow"><div class="card"><h2>Almost there</h2><p class="sub">This app isn’t connected to its database yet. ' +
      'Paste your Supabase project URL and anon key into <code>app/assets/config.js</code> (see SETUP.md).</p></div></div>';
  }

  window.CV = { sb, configured, cfg, CREST, esc, para, fmtClock, fmtDur, fmtIST, num, qs, toast, ask, loading, rpc, session, requireUser, logout, header, friendly, notConfigured };
})();
