/* UG Exam Atlas — shared runtime. Pages are pre-rendered; this file adds live dates, search,
   filters, saved list, compare and the tools. Data comes from data.js (window.ATLAS). */
(function(){
"use strict";
const A = window.ATLAS; if(!A) return;
const BODY = document.getElementById("atlas") || document.body, ROOT = BODY.dataset.root || "", IDX = BODY.dataset.idx || "";
const exams = A.exams, byId = Object.fromEntries(exams.map(e=>[e.id,e]));
const cols = A.colleges;
const examUrl = id => ROOT + id + "/" + IDX;
const colUrl = s => ROOT + "colleges/" + s + "/" + IDX;
const $ = (s,r=document) => r.querySelector(s), $$ = (s,r=document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

/* ---------- per-viewer storage ---------- */
const store = {
  get(k,d){ try{ const v = localStorage.getItem("ugatlas:"+k); return v ? JSON.parse(v) : d }catch(e){ return d } },
  set(k,v){ try{ localStorage.setItem("ugatlas:"+k, JSON.stringify(v)) }catch(e){} }
};
let LIST = new Set(store.get("list", []).filter(id => byId[id]));
let CMP = store.get("cmp", []).filter(id => byId[id]).slice(0,3);
const saveList = () => store.set("list", [...LIST]);
const saveCmp = () => store.set("cmp", CMP);

/* ---------- dates & status ---------- */
const TODAY = (()=>{ const d = new Date(); d.setHours(0,0,0,0); return d })();
const DAY = 864e5;
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const pd = s => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s||""); return m ? new Date(+m[1], m[2]-1, +m[3]) : null };
const fd = d => d ? `${d.getDate()} ${MON[d.getMonth()]} ${d.getFullYear()}` : "";
const fds = d => d ? `${d.getDate()} ${MON[d.getMonth()]}` : "";
const days = d => Math.round((d - TODAY) / DAY);
const CYCLE = TODAY.getMonth() >= 7 ? TODAY.getFullYear() + 1 : TODAY.getFullYear();

function status(e){
  const n = e.nc || {};
  const open = pd(n.apply_open), close = pd(n.apply_close);
  const exD = (n.exam_dates || []).map(pd).filter(Boolean).sort((a,b) => a-b);
  const rounds = (n.rounds || []).map(r => ({label:r.label, c:pd(r.apply_close), x:pd(r.exam_date)}));
  rounds.forEach(r => { if(r.x && !exD.some(d => +d === +r.x)) exD.push(r.x) }); exD.sort((a,b) => a-b);
  const nextExam = exD.find(d => d >= TODAY) || null;
  const nextRound = rounds.find(r => r.c && r.c >= TODAY) || null;
  const nextClose = nextRound ? nextRound.c : (close && close >= TODAY ? close : null);
  let key = "na", label = "Dates not out", deadline = null;
  if(open && open > TODAY){ key = "soon"; label = "Opens " + fds(open) }
  else if(nextClose && (!open || open <= TODAY)){ key = "open"; label = "Open now"; deadline = nextClose }
  else if(n.status === "open" && !(close && close < TODAY)){ key = "open"; label = "Open now" }
  else if(nextExam){ key = "exam"; label = "Exam " + fds(nextExam) }
  else if((close && close < TODAY) || n.status === "closed"){ key = "closed"; label = "Closed" }
  else if(n.status === "upcoming"){ key = "soon"; label = "Coming up" }
  if(key === "open" && deadline && days(deadline) <= 10) label = days(deadline) <= 0 ? "Closes today" : `Closes in ${days(deadline)} day${days(deadline)===1?"":"s"}`;
  return {key, label, open, close, deadline, nextExam, nextRound, rounds, n,
    urgent: key === "open" && deadline && days(deadline) <= 10,
    sortKey: deadline ? +deadline : (key === "soon" && open) ? +open : nextExam ? +nextExam : key === "open" ? 8e15 : key === "soon" ? 8.2e15 : 8.5e15};
}
function usual(e){
  const m = (e.months && e.months.apply) || [];
  if(m.length){ const f = m[0]; return "Usually opens " + MON[f-1] }
  return "Dates not out yet";
}
function nextText(e, s){
  s = s || status(e);
  if(s.key === "open" && s.deadline) return (s.nextRound ? s.nextRound.label + ": apply by " : "Apply by ") + fds(s.deadline);
  if(s.key === "open") return "Applications open";
  if(s.key === "soon" && s.open) return "Opens " + fd(s.open);
  if(s.key === "exam") return "Exam on " + fd(s.nextExam);
  if(s.key === "closed") return "Closed for " + CYCLE;
  return usual(e);
}
const pill = s => `<span class="pill ${s.urgent ? "urgent" : s.key}">${esc(s.label)}</span>`;
function cdHtml(e, s){
  s = s || status(e);
  if(s.key === "open" && s.deadline){ const d = Math.max(0, days(s.deadline)); return `<b>${d}</b><span>day${d===1?"":"s"} left<br>to apply</span>` }
  if(s.key === "soon" && s.open){ const d = days(s.open); return `<b>${d}</b><span>day${d===1?"":"s"} until<br>it opens</span>` }
  if(s.key === "exam"){ const d = days(s.nextExam); return `<b>${d}</b><span>day${d===1?"":"s"} to<br>the exam</span>` }
  if(s.key === "open") return `<b>Open</b><span>rolling<br>admissions</span>`;
  if(s.key === "closed") return `<b>Closed</b><span>for ${CYCLE}</span>`;
  const m = (e.months && e.months.apply) || [];
  return m.length ? `<b>${MON[m[0]-1]}</b><span>applications<br>usually open</span>` : `<b>TBA</b><span>dates not<br>out yet</span>`;
}
function detail(e, s){
  s = s || status(e);
  if(s.key === "open" && s.deadline) return "Apply by " + fd(s.deadline) + ((s.nextRound && s.nextRound.x) ? " · test on " + fd(s.nextRound.x) : s.nextExam ? " · exam on " + fd(s.nextExam) : "") + ".";
  if(s.key === "open") return "Applications are open now.";
  if(s.key === "soon" && s.open) return "Applications open on " + fd(s.open) + ".";
  if(s.key === "exam") return "Applications have closed. Exam on " + fd(s.nextExam) + ".";
  const x = ((e.nc && e.nc.expected) || "").split("(")[0].trim().replace(/[;,.\s]+$/,"");
  return x ? x + "." : "Official dates are not out yet.";
}

/* ---------- toast ---------- */
let toastT;
function toast(msg){
  let t = $("#toast");
  if(!t){ t = document.createElement("div"); t.id = "toast"; t.className = "toast"; t.setAttribute("role","status"); document.body.appendChild(t) }
  t.textContent = msg; t.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => t.hidden = true, 2200);
}

/* ---------- hydrate live bits ---------- */
function hydrate(root=document){
  $$("[data-st]", root).forEach(el => { const e = byId[el.dataset.st]; if(e) el.innerHTML = pill(status(e)) });
  $$("[data-next]", root).forEach(el => { const e = byId[el.dataset.next]; if(e) el.textContent = nextText(e) });
  $$("[data-detail]", root).forEach(el => { const e = byId[el.dataset.detail]; if(e) el.textContent = detail(e) });
  $$("[data-cd]", root).forEach(el => { const e = byId[el.dataset.cd]; if(!e) return; const s = status(e); el.innerHTML = cdHtml(e, s);
    const host = el.closest(".dcard,.hl"); if(host) host.classList.toggle("urgent", !!s.urgent);
    const m = host && $(".meter i", host); if(m && s.deadline){ const span = s.open ? Math.max(1,(s.deadline - s.open)/DAY) : 60; m.style.width = Math.min(100, Math.max(4, 100 - days(s.deadline)/span*100)) + "%" } });
  $$(".js-card[data-id]", root).forEach(c => { const e = byId[c.dataset.id]; if(!e) return; const s = status(e); c.dataset.status = s.key; c.dataset.sortdl = s.sortKey });
  $$(".rail", root).forEach(r => {
    const cs = $$(".dcard[data-id]", r);
    cs.forEach(c => { const e = byId[c.dataset.id]; const s = status(e);
      c.hidden = !(s.key === "open" || (s.key === "soon" && s.open && days(s.open) <= 90) || (s.key === "exam" && days(s.nextExam) <= 60));
      c.dataset.k = s.sortKey });
    cs.sort((a,b) => a.dataset.k - b.dataset.k).forEach(c => r.appendChild(c));
    const em = r.parentElement.querySelector(".js-railempty"); if(em) em.hidden = cs.some(c => !c.hidden);
  });
  $$("[data-opencount]", root).forEach(el => { el.textContent = exams.filter(e => status(e).key === "open").length });
  syncStars(root);
  const n = LIST.size; $$("[data-listcount]").forEach(b => { b.hidden = !n; b.textContent = n });
}
function syncStars(root=document){
  $$("[data-star]", root).forEach(b => { const on = LIST.has(b.dataset.star); b.setAttribute("aria-pressed", on); b.setAttribute("aria-label", (on ? "Remove from" : "Save to") + " my list"); b.title = on ? "Saved to my list" : "Save to my list" });
  $$("[data-cmp]", root).forEach(b => { const on = CMP.includes(b.dataset.cmp); if(b.tagName === "INPUT") b.checked = on; else b.innerHTML = on ? "✓ In compare" : "+ Compare" });
  cmpBar();
}

/* ---------- header ---------- */
function initHeader(){
  const burger = $(".burger"), nav = $("#nav");
  if(burger && nav) burger.addEventListener("click", () => { const o = nav.classList.toggle("open"); burger.setAttribute("aria-expanded", o) });
  $$(".dd").forEach(dd => {
    const b = $(".dd-btn", dd), m = $(".dd-menu", dd);
    b.addEventListener("click", ev => { ev.stopPropagation(); const o = m.hidden; m.hidden = !o; b.setAttribute("aria-expanded", o) });
    document.addEventListener("click", ev => { if(!dd.contains(ev.target)){ m.hidden = true; b.setAttribute("aria-expanded", false) } });
    document.addEventListener("keydown", ev => { if(ev.key === "Escape"){ m.hidden = true; b.setAttribute("aria-expanded", false) } });
  });
}

/* ---------- search ---------- */
const INDEX = [
  ...exams.map(e => ({k:"exam", t:e.name, s:[e.by, (e.progs||[]).join(", ")].filter(Boolean).join(" · "), x:(e.full+" "+e.by+" "+(e.progs||[]).join(" ")).toLowerCase(), u:examUrl(e.id), m:e.mono, c:e.cc})),
  ...cols.map(c => ({k:"college", t:c.n, s:[c.city, c.state].filter(Boolean).join(", ") + (c.ex.length ? ` · ${c.ex.length} exam${c.ex.length>1?"s":""}` : ""), x:(c.city+" "+c.state+" "+(c.progs||[]).join(" ")).toLowerCase(), u:colUrl(c.s), m:c.mono, c:c.cc}))
];
function searchIdx(q){
  q = q.trim().toLowerCase(); if(!q) return [];
  const toks = q.split(/\s+/);
  const out = [];
  for(const it of INDEX){
    const name = it.t.toLowerCase(), hay = name + " " + it.x;
    if(!toks.every(t => hay.includes(t))) continue;
    let r = name.startsWith(q) ? 0 : new RegExp("(^|[\\s(\\-–—,./])" + q.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")).test(name) ? 1 : name.includes(toks[0]) ? 2 : 3;
    out.push({it, r});
  }
  out.sort((a,b) => a.r - b.r || (a.it.k === b.it.k ? 0 : a.it.k === "exam" ? -1 : 1) || a.it.t.length - b.it.t.length);
  return out.map(o => o.it);
}
function hl(text, q){
  const t = esc(text); const w = q.trim().split(/\s+/)[0]; if(!w) return t;
  const i = text.toLowerCase().indexOf(w.toLowerCase()); if(i < 0) return t;
  return esc(text.slice(0,i)) + "<mark>" + esc(text.slice(i, i+w.length)) + "</mark>" + esc(text.slice(i+w.length));
}
function initSearch(){
  $$(".js-search").forEach(inp => {
    const form = inp.closest("form"); const box = document.createElement("div");
    box.className = "sugg"; box.hidden = true; box.id = inp.id + "-list"; box.setAttribute("role","listbox");
    form.appendChild(box);
    inp.setAttribute("role","combobox"); inp.setAttribute("aria-controls", box.id); inp.setAttribute("aria-expanded","false"); inp.setAttribute("aria-autocomplete","list");
    let sel = -1, items = [];
    const render = () => {
      const q = inp.value; const res = searchIdx(q);
      const ex = res.filter(r => r.k === "exam").slice(0,6), co = res.filter(r => r.k === "college").slice(0,6);
      items = [...ex, ...co]; sel = items.length ? 0 : -1;
      if(!q.trim()){ box.hidden = true; inp.setAttribute("aria-expanded","false"); return }
      const row = (it,i) => `<a href="${esc(it.u)}" role="option" id="${box.id}-${i}" aria-selected="${i===sel}"><span class="mono sm ${it.c}${it.m.length > 5 ? " long" : ""}">${esc(it.m)}</span><span class="t"><b>${hl(it.t,q)}</b><small>${esc(it.s)}</small></span></a>`;
      let h = "", i = 0;
      if(ex.length) h += `<div class="grp">Exams</div>` + ex.map(it => row(it, i++)).join("");
      if(co.length) h += `<div class="grp">Colleges</div>` + co.map(it => row(it, i++)).join("");
      box.innerHTML = h || `<div class="none">No exam or college matches “${esc(q)}”. Try a shorter word, like a city or “BBA”.</div>`;
      box.hidden = false; inp.setAttribute("aria-expanded","true");
    };
    const move = d => { if(!items.length) return; sel = (sel + d + items.length) % items.length; $$("a", box).forEach((a,i) => a.setAttribute("aria-selected", i === sel)); const a = $$("a", box)[sel]; a && a.scrollIntoView({block:"nearest"}); inp.setAttribute("aria-activedescendant", box.id + "-" + sel) };
    inp.addEventListener("input", render);
    inp.addEventListener("focus", () => { if(inp.value.trim()) render() });
    inp.addEventListener("keydown", ev => {
      if(ev.key === "ArrowDown"){ ev.preventDefault(); move(1) }
      else if(ev.key === "ArrowUp"){ ev.preventDefault(); move(-1) }
      else if(ev.key === "Escape"){ box.hidden = true; inp.setAttribute("aria-expanded","false") }
    });
    form.addEventListener("submit", ev => { ev.preventDefault(); if(!items.length) render(); if(items.length) location.href = items[Math.max(0,sel)].u });
    document.addEventListener("click", ev => { if(!form.contains(ev.target)){ box.hidden = true; inp.setAttribute("aria-expanded","false") } });
  });
}

/* ---------- directory filters ---------- */
function initDirectory(){
  const wrap = $(".js-dir"); if(!wrap) return;
  const cards = $$(".js-card", wrap), list = $(".js-results", wrap), countEl = $(".js-count"), emptyEl = $(".js-empty");
  const fl = $(".filters"), q = $(".js-fq"), sort = $(".js-sort");
  function groups(){
    const g = {};
    $$("[data-f]", fl).forEach(i => { if(i.checked && i.value !== ""){ (g[i.dataset.f] = g[i.dataset.f] || []).push(i.value) } });
    $$("select[data-fs]", fl).forEach(s => { if(s.value) g[s.dataset.fs] = [s.value] });
    return g;
  }
  function apply(){
    const g = groups(), text = (q && q.value || "").trim().toLowerCase(); let n = 0;
    cards.forEach(c => {
      let ok = true;
      for(const k in g){ const have = (c.dataset[k] || "").split("|"); if(!g[k].some(v => have.includes(v))){ ok = false; break } }
      if(ok && text) ok = (c.dataset.search || "").includes(text);
      c.hidden = !ok; if(ok) n++;
    });
    if(countEl) countEl.textContent = n;
    if(emptyEl) emptyEl.hidden = n > 0;
    const active = Object.values(g).reduce((s,v) => s + v.length, 0) + (text ? 1 : 0);
    $$(".js-fcount").forEach(b => { b.textContent = active ? `(${active})` : "" });
  }
  function doSort(){
    if(!sort) return; const k = sort.value;
    const v = c => k === "dl" ? +c.dataset.sortdl : k === "cols" ? -(+c.dataset.cols) : k === "va" ? -(+c.dataset.va || -1) : k === "exams" ? -(+c.dataset.nex) : (c.dataset.name || "");
    const arr = [...cards].sort((a,b) => { const x = v(a), y = v(b); return typeof x === "number" ? x - y || (a.dataset.name > b.dataset.name ? 1 : -1) : String(x).localeCompare(String(y)) });
    arr.forEach(c => list.appendChild(c));
  }
  fl.addEventListener("change", apply);
  if(q) q.addEventListener("input", apply);
  if(sort) sort.addEventListener("change", doSort);
  const clear = $(".js-clear"); if(clear) clear.addEventListener("click", () => { $$("[data-f]", fl).forEach(i => i.checked = i.value === "" ); $$("select[data-fs]", fl).forEach(s => s.value = ""); if(q) q.value = ""; apply() });
  // phone sheet
  let scrim;
  const close = () => { fl.classList.remove("open"); scrim && scrim.remove(); scrim = null };
  $$(".flt-btn").forEach(b => b.addEventListener("click", () => { fl.classList.add("open"); scrim = document.createElement("div"); scrim.className = "scrim"; scrim.addEventListener("click", close); document.body.appendChild(scrim) }));
  $$(".js-apply").forEach(b => b.addEventListener("click", close));
  // preset from #token
  const h = decodeURIComponent((location.hash || "").slice(1)).toLowerCase();
  if(h){ const i = $(`[data-hash="${CSS.escape(h)}"]`, fl); if(i){ if(i.tagName === "OPTION"){ i.parentElement.value = i.value } else i.checked = true } }
  doSort(); apply();
}

/* ---------- compare bar ---------- */
function cmpBar(){
  let bar = $("#cmpbar");
  const show = CMP.length && !$("#tool[data-tool=compare]");
  if(!show){ if(bar) bar.remove(); return }
  if(!bar){ bar = document.createElement("div"); bar.id = "cmpbar"; bar.className = "cmpbar"; document.body.appendChild(bar) }
  bar.innerHTML = `<span>${CMP.length} of 3 to compare: ${esc(CMP.map(id => byId[id].name).join(", "))}</span><a class="btn gold sm" href="${esc(ROOT + "tools/compare/" + IDX)}">Compare</a><button class="btn sm ghost" style="color:inherit;border-color:transparent" data-cmpclear aria-label="Clear compare">✕</button>`;
}

/* ---------- global clicks ---------- */
document.addEventListener("click", ev => {
  const t = ev.target.closest("[data-star],[data-cmp],[data-cmpclear],[data-copy],[data-showall]"); if(!t) return;
  if(t.dataset.star){ ev.preventDefault(); const id = t.dataset.star; if(LIST.has(id)){ LIST.delete(id); toast("Removed from your list") } else { LIST.add(id); toast("Saved to your list") } saveList(); hydrate(); if($("#tool[data-tool=mylist]")) renderTool(); return }
  if(t.dataset.cmp && t.tagName !== "INPUT"){ ev.preventDefault(); toggleCmp(t.dataset.cmp); return }
  if(t.hasAttribute("data-cmpclear")){ CMP = []; saveCmp(); syncStars(); return }
  if(t.hasAttribute("data-copy")){ const url = location.href.split("#")[0]; const done = () => toast("Link copied");
    if(navigator.clipboard) navigator.clipboard.writeText(url).then(done).catch(() => toast(url)); else toast(url); return }
  if(t.hasAttribute("data-showall")){ $$(".ccard.more").forEach(c => c.classList.remove("more")); t.remove(); return }
});
document.addEventListener("change", ev => { const t = ev.target; if(t.matches("input[data-cmp]")) toggleCmp(t.dataset.cmp) });
function toggleCmp(id){
  if(CMP.includes(id)){ CMP = CMP.filter(x => x !== id) } else { if(CMP.length >= 3){ toast("You can compare up to 3. Remove one first."); syncStars(); return } CMP.push(id); toast("Added to compare") }
  saveCmp(); syncStars(); if($("#tool[data-tool=compare]")) renderTool();
}

/* ---------- exam page ---------- */
function initProfile(){
  const cq = $(".js-colq");
  if(cq) cq.addEventListener("input", () => {
    const v = cq.value.trim().toLowerCase(); const cards = $$("#colleges .ccard"); let n = 0;
    cards.forEach(c => { const ok = !v || (c.dataset.search || "").includes(v); c.hidden = !ok; if(ok) n++; if(v) c.classList.remove("more") });
    const sa = $("[data-showall]"); if(sa && v) sa.remove();
    const e = $(".js-colempty"); if(e) e.hidden = n > 0;
  });
  const links = $$(".secnav a[href^='#']"); if(!links.length || !("IntersectionObserver" in window)) return;
  const map = new Map(links.map(a => [a.getAttribute("href").slice(1), a]));
  const io = new IntersectionObserver(ents => {
    ents.forEach(en => { if(en.isIntersecting){ links.forEach(a => a.classList.remove("on")); const a = map.get(en.target.id); if(a){ a.classList.add("on"); a.scrollIntoView({block:"nearest", inline:"nearest"}) } } });
  }, {rootMargin:"-30% 0px -60% 0px"});
  map.forEach((a,id) => { const s = document.getElementById(id); if(s) io.observe(s) });
}

/* ---------- rail arrows ---------- */
function initRail(){
  $$(".rail-wrap").forEach(w => { const r = $(".rail", w);
    $$("[data-rail]", w.parentElement).forEach(b => b.addEventListener("click", () => r.scrollBy({left:(b.dataset.rail === "next" ? 1 : -1) * r.clientWidth * .9, behavior:"smooth"}))) });
}

/* ============================== TOOLS ============================== */
const mono = (e, sz="sm") => `<span class="mono ${sz} ${e.cc}${e.mono.length > 5 ? " long" : ""}">${esc(e.mono)}</span>`;
const starBtn = (id, sm=true) => `<button class="star${sm?" sm":""}" data-star="${id}" aria-pressed="${LIST.has(id)}" aria-label="Save to my list"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.3l2 4.2 4.6.6-3.3 3.2.8 4.6L8 11.7 3.9 13.9l.8-4.6L1.4 6.1 6 5.5z" fill="currentColor"/></svg></button>`;
let ME = store.get("me", {p12:82, p10:85, stream:"Commerce", maths:"yes", dob:"2008-08-15", example:true});

function ageOn(dob, ref){ if(!dob) return null; let a = ref.getFullYear() - dob.getFullYear(); const m = ref.getMonth() - dob.getMonth(); if(m < 0 || (m === 0 && ref.getDate() < dob.getDate())) a--; return a }
function checkElig(e, me){
  const g = e.elig || {}; const fails = [], checks = [];
  if(!e.elig) checks.push("Rules not captured in detail; read the eligibility on the exam page");
  if(g.min_12_pct != null && me.p12 < g.min_12_pct) fails.push(`Needs ${g.min_12_pct}% in Class XII`);
  if(g.min_10_pct != null && me.p10 < g.min_10_pct) fails.push(`Needs ${g.min_10_pct}% in Class X`);
  const st = g.streams || ["Any"]; if(!st.includes("Any") && !st.includes(me.stream)) fails.push(`Open to ${st.join(" / ")} stream only`);
  if(g.maths_required === true && me.maths === "no") fails.push("Needs Maths in Class XII");
  if(g.maths_required == null && e.elig && me.maths === "no") checks.push("Check whether Maths is required");
  if(g.max_age != null){ const a = ageOn(pd(me.dob), new Date(CYCLE, 6, 31));
    if(a != null && a > g.max_age) fails.push(`Age limit ${g.max_age}${g.age_note ? " (" + g.age_note + ")" : ""}`);
    else if(a != null && a === g.max_age) checks.push(`You're at the age limit; check the cut-off date${g.age_note ? " (" + g.age_note + ")" : ""}`) }
  const state = fails.length ? "no" : checks.length ? "chk" : "ok";
  return {state, fails, checks};
}
function toolEligibility(el){
  const me = ME; const res = exams.map(e => ({e, r:checkElig(e, me)}));
  const ok = res.filter(x => x.r.state === "ok"), chk = res.filter(x => x.r.state === "chk"), no = res.filter(x => x.r.state === "no");
  const row = ({e,r}) => `<div class="rrow ${r.state}">${mono(e)}<div class="t"><a href="${esc(examUrl(e.id))}">${esc(e.name)}</a><p>${esc((r.state === "no" ? r.fails : r.checks).join(" · ") || (e.progs||[]).join(", "))}</p></div>${starBtn(e.id)}</div>`;
  const seg = (name, opts, val) => `<div class="seg" role="group" aria-label="${name}">${opts.map(o => `<button type="button" data-me="${name}" data-v="${o}" aria-pressed="${val === o}">${o === "yes" ? "Yes" : o === "no" ? "No" : o}</button>`).join("")}</div>`;
  el.innerHTML = `<div class="elig">
    <form class="form" onsubmit="return false" aria-label="Your details">
      ${me.example ? `<p class="exnote">Example values are filled in. Change them to yours.</p>` : ""}
      <div class="field"><label for="p12">Class XII % (expected is fine)</label><div class="rng"><input type="range" id="p12" min="40" max="100" step="1" value="${me.p12}"><output id="p12o" class="num">${me.p12}%</output></div></div>
      <div class="field"><label for="p10">Class X %</label><div class="rng"><input type="range" id="p10" min="40" max="100" step="1" value="${me.p10}"><output id="p10o" class="num">${me.p10}%</output></div></div>
      <div class="field"><span class="lab">Stream in Class XII</span>${seg("stream", ["Commerce","Science","Arts"], me.stream)}</div>
      <div class="field"><span class="lab">Maths in Class XII?</span>${seg("maths", ["yes","no"], me.maths)}</div>
      <div class="field"><label for="dob">Date of birth</label><input type="date" id="dob" value="${esc(me.dob)}"><span class="hint">Used only for age limits. Stays on this device.</span></div>
    </form>
    <div>
      <div class="vtop"><div class="vbox ok"><b>${ok.length}</b><span>You can apply</span></div><div class="vbox chk"><b>${chk.length}</b><span>Check the details</span></div><div class="vbox no"><b>${no.length}</b><span>Not eligible</span></div></div>
      ${ok.length ? `<div class="rlist">${ok.map(row).join("")}</div>` : ""}
      ${chk.length ? `<h2 style="font:600 22px var(--display);margin:28px 0 12px">Check the details</h2><div class="rlist">${chk.map(row).join("")}</div>` : ""}
      ${no.length ? `<details class="more2" style="margin-top:20px"><summary>Not eligible (${no.length}): see why</summary><div class="rlist">${no.map(row).join("")}</div></details>` : ""}
      <p class="note">This checks each exam's general-category rules. Reserved categories usually get relaxations. Always confirm on the official page before you apply.</p>
    </div></div>`;
}
function toolCalendar(el){
  const start = new Date(TODAY.getFullYear(), TODAY.getMonth(), 1);
  const months = [...Array(12)].map((_,i) => new Date(start.getFullYear(), start.getMonth()+i, 1));
  const idx = d => d ? (d.getFullYear() - start.getFullYear())*12 + d.getMonth() - start.getMonth() : -1;
  const mi = m => { for(let i=0;i<12;i++) if(months[i].getMonth()+1 === m) return i; return -1 };
  const rows = exams.map(e => {
    const n = e.nc || {}; const cells = months.map(() => ({app:false, ex:false, est:false, lab:""}));
    const o = pd(n.apply_open), c = pd(n.apply_close); let any = false;
    const exD = (n.exam_dates || []).map(pd).filter(Boolean); (n.rounds || []).forEach(r => { const x = pd(r.exam_date); if(x && !exD.some(d => +d === +x)) exD.push(x) });
    if(o || c){ const a = Math.max(0, idx(o || c)), b = Math.min(11, idx(c || o)); for(let i=a;i<=b;i++){ cells[i].app = true; any = true } }
    exD.forEach(d => { const i = idx(d); if(i >= 0 && i < 12){ cells[i].ex = true; cells[i].lab = cells[i].lab ? cells[i].lab + "+" : String(d.getDate()); any = true } });
    if(!any && e.months){ (e.months.apply || []).forEach(m => { const i = mi(m); if(i >= 0){ cells[i].app = true; cells[i].est = true; any = true } }); (e.months.exam || []).forEach(m => { const i = mi(m); if(i >= 0){ cells[i].ex = true; cells[i].est = true; any = true } }) }
    const fe = cells.findIndex(x => x.ex), first = fe >= 0 ? fe : cells.findIndex(x => x.app);
    return {e, cells, any, first};
  }).filter(r => r.any).sort((a,b) => a.first - b.first);
  const prog = el.dataset.prog || "";
  el.innerHTML = `<div class="legend"><span><i style="background:var(--c1s);border:1px solid var(--c1)"></i>Applications open</span><span><i style="background:var(--gold)"></i>Exam (date shown)</span><span><i style="border:1.5px dashed var(--gold-text)"></i>Estimated from last year</span></div>
  <div class="tbl"><div class="cal"><div class="calrow head"><span></span>${months.map((m,i) => `<span class="${i===0?"now":""}">${MON[m.getMonth()]}${(m.getMonth()===0||i===0) ? " ’" + String(m.getFullYear()).slice(2) : ""}</span>`).join("")}</div>
  ${rows.map(r => `<div class="calrow"><a class="lab" href="${esc(examUrl(r.e.id))}" title="${esc(r.e.name)}">${LIST.has(r.e.id) ? "★ " : ""}${esc(r.e.name)}</a>${r.cells.map((c,i) => `<div class="cell${i===0?" now":""}">${c.ex ? `<div class="mk ex${c.est?" est":""}">${esc(c.lab)}</div>` : c.app ? `<div class="mk app${c.est?" est":""}"></div>` : ""}</div>`).join("")}</div>`).join("")}</div></div>`;
}
function toolCompare(el){
  const opts = exams.filter(e => !CMP.includes(e.id)).map(e => `<option value="${e.id}">${esc(e.name)}</option>`).join("");
  const col = e => { const s = status(e); return `<div class="cmpcol"><div class="hd">${mono(e)}<h3><a href="${esc(examUrl(e.id))}">${esc(e.name)}</a></h3><button class="star sm" data-cmp="${e.id}" aria-label="Remove ${esc(e.name)}">✕</button></div>${pill(s)}<dl>
    <div><dt>Coming cycle</dt><dd>${esc(nextText(e, s))}</dd></div>
    <div><dt>Programmes</dt><dd>${esc((e.progs||[]).join(", ") || "—")}</dd></div>
    <div><dt>Duration · questions</dt><dd>${esc(e.dur ? e.dur + " min" : "—")} · ${esc(e.q ? e.q + " questions" : "—")}</dd></div>
    <div><dt>Sections</dt><dd>${esc((e.secs||[]).map(x => x[0] + (x[1] ? ` (${x[1]})` : "")).join(", ") || "—")}</dd></div>
    <div><dt>Marking</dt><dd>${esc(e.mark || "—")}</dd></div>
    <div><dt>English share</dt><dd>${e.va != null ? Math.round(e.va*100) + "% · " : ""}${esc(e.vtxt || "—")}</dd></div>
    <div><dt>Who can apply</dt><dd>${esc(e.etxt || "—")}</dd></div>
    <div><dt>Selection</dt><dd>${esc(e.sel || "—")}</dd></div>
    <div><dt>Application fee</dt><dd>${esc(e.fee || "—")}</dd></div>
    <div><dt>Colleges listed</dt><dd>${e.ncol}</dd></div></dl></div>` };
  const slots = CMP.map(id => byId[id]).map(col);
  while(slots.length < 3) slots.push(`<div class="cmpslot"><b>Add an exam</b><div class="field"><label for="pick${slots.length}" class="sr">Choose an exam</label><select id="pick${slots.length}" data-pick><option value="">Choose an exam…</option>${opts}</select></div><span style="font-size:13.5px;color:var(--muted)">Or tick “Compare” on any exam card.</span></div>`);
  el.innerHTML = `<div class="cmp">${slots.join("")}</div>`;
}
function toolEnglish(el){
  const list = exams.filter(e => e.va != null).sort((a,b) => b.va - a.va);
  const w = list.filter(e => e.va > 0); const avg = w.length ? Math.round(w.reduce((s,e) => s + e.va, 0) / w.length * 100) : 0;
  el.innerHTML = `<div class="callout"><b class="num">${avg}%</b><p>is the average English share across the ${w.length} exams that test it. One strong verbal preparation carries across almost every exam here.</p></div>
  <div class="bars">${list.map(e => `<div class="bar"><a href="${esc(examUrl(e.id))}" title="${esc(e.name)}">${esc(e.name)}</a><div class="track" role="img" aria-label="${Math.round(e.va*100)}%"><div class="fill" style="width:${Math.round(e.va*100)}%"></div></div><span class="v num">${Math.round(e.va*100)}%</span></div>`).join("")}</div>
  <p class="note">Share of questions from verbal ability, reading comprehension, grammar, vocabulary and critical reasoning, from published section counts. The dashed line marks half the paper. For CUET it shows the language paper's share of a typical four-paper combination. Exams without a fixed published split are left out.</p>`;
}
function toolMyList(el){
  const items = [...LIST].map(id => byId[id]).map(e => ({e, s:status(e)})).sort((a,b) => a.s.sortKey - b.s.sortKey);
  const f = store.get("signup", {});
  el.innerHTML = (items.length ? `<div class="rlist">${items.map(({e,s}) => `<div class="mrow">${mono(e)}<div style="min-width:0"><h3><a href="${esc(examUrl(e.id))}">${esc(e.name)}</a></h3>${pill(s)}</div>
      <div class="hs"><div class="k">Next step</div><div class="v">${esc(nextText(e, s))}${s.deadline ? ` <span style="color:var(--muted)">(${days(s.deadline)} days)</span>` : ""}</div></div>
      <div class="hs"><div class="k">Exam</div><div class="v">${s.nextRound && s.nextRound.x ? fd(s.nextRound.x) : s.nextExam ? fd(s.nextExam) : "—"}</div></div>${starBtn(e.id)}</div>`).join("")}</div>`
    : `<div class="empty"><p style="margin:0 0 14px">Your list is empty. Tap the ★ on any exam to save it here.</p><a class="btn gold" href="${esc(ROOT + "tools/eligibility/" + IDX)}">Find exams I can take</a></div>`)
  + `<section class="signup" aria-labelledby="su-h"><div><h2 id="su-h">Get deadline alerts</h2><p>We'll message you before each exam on your list opens and closes. One message per deadline. No spam.</p></div>
    <form id="signup" novalidate>
      <div class="field"><label for="su-name">Name</label><input id="su-name" type="text" autocomplete="name" value="${esc(f.name || "")}"></div>
      <div class="field"><label for="su-class">I am</label><select id="su-class"><option>In Class 12</option><option>In Class 11</option><option>Taking a gap year</option><option>A parent</option></select></div>
      <div class="field"><label for="su-wa">WhatsApp number</label><input id="su-wa" type="tel" inputmode="tel" autocomplete="tel" placeholder="10-digit mobile" value="${esc(f.wa || "")}"></div>
      <div class="field"><label for="su-email">Email</label><input id="su-email" type="email" autocomplete="email" value="${esc(f.email || "")}"></div>
      <div class="full" style="display:flex;flex-wrap:wrap;gap:14px;align-items:center"><button class="btn gold" type="submit">Send me alerts</button><p class="fmsg" id="suMsg" role="status"></p></div>
      <p class="full fmsg" style="font-size:12.5px">We use these details only to send you exam alerts. We never share or sell them. Reply "stop" to any message to opt out.</p>
    </form></section>`;
  const sel = $("#su-class"); if(sel && f.klass) sel.value = f.klass;
}
async function submitSignup(){
  const msg = $("#suMsg"); const d = {name:$("#su-name").value.trim(), klass:$("#su-class").value, wa:$("#su-wa").value.trim(), email:$("#su-email").value.trim()};
  const err = t => { msg.className = "fmsg err"; msg.textContent = t };
  if(!d.name){ err("Add your name."); $("#su-name").focus(); return }
  if(!d.wa && !d.email){ err("Add a WhatsApp number or an email so we can reach you."); return }
  if(d.wa && !/^[+0-9\s-]{10,15}$/.test(d.wa)){ err("Check the WhatsApp number: 10 digits, or with +91."); return }
  if(d.email && !/^\S+@\S+\.\S+$/.test(d.email)){ err("Check the email address."); return }
  store.set("signup", d);
  const examsTxt = [...LIST].map(id => byId[id].name).join(", ");
  const cfg = A.cfg || {};
  if(!cfg.formspree){
    if(cfg.live && cfg.email){
      const body = `Please send me deadline alerts.\n\nName: ${d.name}\nI am: ${d.klass}\nWhatsApp: ${d.wa || "-"}\nEmail: ${d.email || "-"}\nExams: ${examsTxt || "-"}`;
      location.href = `mailto:${cfg.email}?subject=${encodeURIComponent("Deadline alerts: " + d.name)}&body=${encodeURIComponent(body)}`;
      msg.className = "fmsg"; msg.innerHTML = `Your email app should open with the message ready. Press send. If it didn't open, write to <b>${esc(cfg.email)}</b>.`; return }
    msg.className = "fmsg"; msg.textContent = "Alerts aren't switched on in this preview. Your details are saved on this device only."; return }
  msg.className = "fmsg"; msg.textContent = "Sending…";
  try{ const r = await fetch("https://formspree.io/f/" + cfg.formspree, {method:"POST", headers:{"Accept":"application/json","Content-Type":"application/json"}, body:JSON.stringify({...d, exams:examsTxt, source:"UG Exam Atlas"})});
    if(!r.ok) throw 0; msg.className = "fmsg ok"; msg.textContent = "Done. You'll get alerts for the exams on your list." }
  catch(e){ err("That didn't go through. Check your connection and try again.") }
}
const TOOLS = {eligibility:toolEligibility, calendar:toolCalendar, compare:toolCompare, english:toolEnglish, mylist:toolMyList};
function renderTool(keep){
  const el = $("#tool"); if(!el) return;
  const a = document.activeElement, id = a && a.id;
  TOOLS[el.dataset.tool](el);
  if(keep && id){ const n = document.getElementById(id); if(n) n.focus() }
  syncStars();
}
function initTools(){
  const el = $("#tool"); if(!el) return;
  renderTool();
  let t;
  el.addEventListener("input", ev => { const x = ev.target;
    if(x.id === "p12" || x.id === "p10"){ ME = {...ME, [x.id]:+x.value, example:false}; store.set("me", ME); $("#" + x.id + "o").textContent = x.value + "%"; clearTimeout(t); t = setTimeout(() => renderTool(true), 140) } });
  el.addEventListener("change", ev => { const x = ev.target;
    if(x.id === "dob"){ ME = {...ME, dob:x.value, example:false}; store.set("me", ME); renderTool(true) }
    if(x.matches("[data-pick]") && x.value){ CMP.push(x.value); CMP = CMP.slice(0,3); saveCmp(); renderTool() } });
  el.addEventListener("click", ev => { const b = ev.target.closest("[data-me]"); if(!b) return; ME = {...ME, [b.dataset.me]:b.dataset.v, example:false}; store.set("me", ME); renderTool() });
  el.addEventListener("submit", ev => { if(ev.target.id === "signup"){ ev.preventDefault(); submitSignup() } });
}

/* ---------- boot ---------- */
initHeader(); initSearch(); hydrate(); initDirectory(); initProfile(); initRail(); initTools();
})();
