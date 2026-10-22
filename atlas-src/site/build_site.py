"""UG Exam Atlas — multi-page site generator (directory style).

  python3 site/build_site.py            -> dist/live/exams/...   (for campverbal.com/exams/)
                                        -> dist/preview/...       (for the Claude artifact preview)
Uses build.collect() for the merged, patched data.
"""
import json, os, re, html, math, datetime, shutil, sys, hashlib, collections, io, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, PROJ)
import build as B  # noqa: E402

TODAY = datetime.date.today()
CYCLE = TODAY.year + 1 if TODAY.month >= 8 else TODAY.year
CFG = B.CONFIG
SITE = CFG.get("siteUrl", "https://www.campverbal.com").rstrip("/")
BASE = CFG.get("pageBase", "/exams/")
H = lambda s: html.escape(str(s if s is not None else ""), quote=True)
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CATS = [
    ("IIM & integrated management", "iim", "c1", "IIMs & IPM", "IPMAT, JIPMAT and the IIMs' own UG tests"),
    ("Private university", "private", "c2", "Private universities", "NPAT, SET, Christ, KIIT, Manipal and more"),
    ("CUET & central universities", "cuet", "c3", "CUET & central universities", "Delhi University, BHU, Jamia, AMU and others"),
    ("State & other", "state", "c4", "State & college tests", "MAH CET, IPU CET, Xavier's, Gujarat and South India"),
    ("Liberal arts", "liberal", "c5", "Liberal arts", "Ashoka, FLAME, Krea, Jindal, Azim Premji, SAT"),
]
CAT = {c[0]: {"tok": c[1], "cc": c[2], "label": c[3], "desc": c[4]} for c in CATS}
PROGS = [("IPM", "ipm", "Integrated 5-year management programmes at IIMs and others"),
         ("BBA", "bba", "Bachelor of Business Administration"),
         ("BMS", "bms", "Management studies and business economics"),
         ("BCom", "bcom", "Commerce, accounting and business"),
         ("Economics", "economics", "BA / BSc Economics and integrated MA"),
         ("Finance", "finance", "Finance, accounting and investment"),
         ("Liberal Arts", "liberal-arts", "Interdisciplinary BA / BSc programmes")]

# ---------------- icons ----------------
def ic(name, cls=""):
    P = {
        "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>',
        "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
        "left": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
        "chev": '<path d="m6 9 6 6 6-6"/>',
        "ext": '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
        "cal": '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
        "check": '<circle cx="12" cy="12" r="8.5"/><path d="m8.5 12.2 2.4 2.4 4.8-5"/>',
        "cols": '<rect x="3.5" y="4" width="7" height="16" rx="1.5"/><rect x="13.5" y="4" width="7" height="16" rx="1.5"/>',
        "bars": '<path d="M4 20h16"/><rect x="5.5" y="11" width="3" height="7" rx=".8"/><rect x="10.5" y="6" width="3" height="12" rx=".8"/><rect x="15.5" y="9" width="3" height="9" rx=".8"/>',
        "book": '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5"/>',
        "brief": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M3 12.5h18"/>',
        "cap": '<path d="m2.5 9 9.5-5 9.5 5-9.5 5z"/><path d="M6.5 11v5c0 1.4 2.5 3 5.5 3s5.5-1.6 5.5-3v-5M21.5 9v6"/>',
        "coins": '<ellipse cx="9" cy="7" rx="5.5" ry="2.5"/><path d="M3.5 7v4c0 1.4 2.5 2.5 5.5 2.5s5.5-1.1 5.5-2.5V7"/><path d="M9.5 15.4c.9 1 2.8 1.6 5 1.6 3 0 5.5-1.1 5.5-2.5v-4c0-1.2-1.8-2.2-4.3-2.4"/>',
        "ledger": '<rect x="4.5" y="3" width="15" height="18" rx="2"/><path d="M8.5 8h7M8.5 12h7M8.5 16h4"/>',
        "trend": '<path d="M3 17l5.5-5.5 4 4L21 7"/><path d="M15 7h6v6"/>',
        "feather": '<path d="M20 4c-7 0-12 5-12 12v4"/><path d="M8 16c5 0 9-3 10-8M4 20l4-4"/>',
        "pin": '<path d="M12 21s7-6.2 7-11.5a7 7 0 1 0-14 0C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
        "doc": '<path d="M14 3H6.5A1.5 1.5 0 0 0 5 4.5v15A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3v5h5M8.5 13h7M8.5 17h5"/>',
        "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
        "filter": '<path d="M4 6h16M7 12h10M10 18h4"/>',
        "shield": '<path d="M12 3 5 6v5.5c0 4.4 3 7.9 7 9.5 4-1.6 7-5.1 7-9.5V6z"/><path d="m9 12 2.2 2.2L15.5 10"/>',
        "tag": '<path d="M3.5 12.2V4.5a1 1 0 0 1 1-1h7.7l8.3 8.3-8.7 8.7z"/><circle cx="8" cy="8" r="1.4"/>',
        "refresh": '<path d="M20 11a8 8 0 0 0-14.6-4.5M4 4v4h4M4 13a8 8 0 0 0 14.6 4.5M20 20v-4h-4"/>',
        "bldg": '<path d="M3 21h18M5 21V9l7-5 7 5v12M9 21v-6h6v6M9 11h.01M15 11h.01"/>',
        "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
        "lang": '<path d="M4 6h9M8.5 4v2M6 6c.5 3 2.6 5.5 5.5 6.5M11 6c-.6 3.4-3 6.3-6.5 7.5"/><path d="m12.5 20 4-9 4 9M14 17h5"/>',
    }[name]
    return f'<svg class="{cls}" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{P}</svg>'

STAR_SVG = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.3l2 4.2 4.6.6-3.3 3.2.8 4.6L8 11.7 3.9 13.9l.8-4.6L1.4 6.1 6 5.5z" fill="currentColor"/></svg>'
SHIELD = '<svg viewBox="0 0 200 220" aria-hidden="true"><defs><linearGradient id="cvg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f3d488"/><stop offset="1" stop-color="#c9971c"/></linearGradient></defs><path d="M12 10h176v86c0 58-42 100-88 114C54 196 12 154 12 96z" fill="#7c1d33" stroke="url(#cvg)" stroke-width="10"/><path d="M58 150 100 66l42 84" fill="none" stroke="url(#cvg)" stroke-width="14" stroke-linejoin="round"/><path d="M84 150l16-32 16 32" fill="#7c1d33" stroke="url(#cvg)" stroke-width="8" stroke-linejoin="round"/></svg>'

def star(eid, sm=False):
    return f'<button class="star{" sm" if sm else ""}" data-star="{H(eid)}" aria-pressed="false" aria-label="Save to my list">{STAR_SVG}</button>'

# ---------------- text helpers ----------------
def slug(s):
    s = re.sub(r"[’'`.]", "", s.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:64].strip("-")

def fdate(s, year=True):
    try:
        d = datetime.date.fromisoformat(s or "")
        return f"{d.day} {MON[d.month-1]}" + (f" {d.year}" if year else "")
    except Exception:
        return ""

def pdate(s):
    try:
        return datetime.date.fromisoformat(s or "")
    except Exception:
        return None

def short(s, n=36):
    s = re.split(r";|,(?!\d)", s or "")[0]
    s = re.sub(r"\s*\(.*?\)", "", s).strip(" ,")
    return s if len(s) <= n else s[:n-1].rstrip() + "…"

def plural(n, w):
    return f"{n} {w}{'' if n == 1 else 's'}"

def join_and(xs):
    xs = [x for x in xs if x]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1] if xs else ""

ACRO = re.compile(r"^[A-Z][A-Z0-9\-]{1,5}$")
STOP = {"of", "the", "and", "&", "for", "in", "at", "to", "a", "an", "–", "—", "-"}
def mono_exam(name):
    for t in re.split(r"[\s/()\-]+", name):
        if ACRO.match(t):
            return t
    w = [x for x in re.split(r"\s+", name) if x.lower() not in STOP and x[:1].isalpha()]
    return "".join(x[0] for x in w[:2]).upper()

def mono_college(name):
    m = re.search(r"\(([A-Z][A-Za-z]{1,5})\)", name)
    if m and m.group(1).isupper():
        return m.group(1)
    first = re.split(r"[\s,]+", name)[0]
    if ACRO.match(first) and first not in ("ATLAS",):
        nxt = re.split(r"[\s,–—-]+", name)
        return first if first != "IIM" or len(nxt) < 2 else "IIM" + nxt[1][:1].upper()
    w = [x for x in re.split(r"[\s,–—\-]+", re.sub(r"\(.*?\)", "", name)) if x and x.lower() not in STOP and x[:1].isalpha()]
    w2 = [x for x in w if x.lower() not in ("college", "university", "school", "institute", "department", "faculty")]
    w = w2 if len(w2) >= 2 else w
    return "".join(x[0] for x in w[:3]).upper().replace(".", "")

def prog_tags(texts):
    blob = " ".join(texts)
    return [n for n, rx in B.PROG_MAP if re.search(rx, blob, re.I)]

def type_bucket(t, name):
    t = (t or "") + " " + name
    if re.search(r"\bIIM\b|Indian Institute of Management", t): return "IIM"
    if re.search(r"central", t, re.I): return "Central university"
    if re.search(r"govt|government|state univ|public", t, re.I): return "Government"
    if re.search(r"private|deemed", t, re.I): return "Private / deemed"
    if re.search(r"college|autonomous|aided|affiliated", t, re.I): return "College"
    return "Other"

# ---------------- status (server-side fallback; atlas.js recomputes live) ----------------
def status(e, today=TODAY):
    n = e.get("next_cycle") or {}
    op, cl = pdate(n.get("apply_open")), pdate(n.get("apply_close"))
    exd = sorted(d for d in (pdate(x) for x in n.get("exam_dates") or []) if d)
    rounds = [{"label": r.get("label"), "c": pdate(r.get("apply_close")), "x": pdate(r.get("exam_date"))} for r in n.get("rounds") or []]
    for r in rounds:
        if r["x"] and r["x"] not in exd: exd.append(r["x"])
    exd.sort()
    nxt = next((d for d in exd if d >= today), None)
    nr = next((r for r in rounds if r["c"] and r["c"] >= today), None)
    ncl = nr["c"] if nr else (cl if cl and cl >= today else None)
    key, label, dl = "na", "Dates not out", None
    if op and op > today: key, label = "soon", f"Opens {fdate(n.get('apply_open'), False)}"
    elif ncl and (not op or op <= today): key, label, dl = "open", "Open now", ncl
    elif n.get("status") == "open" and not (cl and cl < today): key, label = "open", "Open now"
    elif nxt: key, label = "exam", f"Exam {nxt.day} {MON[nxt.month-1]}"
    elif (cl and cl < today) or n.get("status") == "closed": key, label = "closed", "Closed"
    elif n.get("status") == "upcoming": key, label = "soon", "Coming up"
    return {"key": key, "label": label, "deadline": dl, "next_exam": nxt, "next_round": nr, "open": op}

def next_text(e, s=None):
    s = s or status(e)
    if s["key"] == "open" and s["deadline"]:
        d = s["deadline"]; return (f"{s['next_round']['label']}: apply by " if s["next_round"] else "Apply by ") + f"{d.day} {MON[d.month-1]}"
    if s["key"] == "open": return "Applications open"
    if s["key"] == "soon" and s["open"]: return f"Opens {s['open'].day} {MON[s['open'].month-1]} {s['open'].year}"
    if s["key"] == "exam": return f"Exam on {s['next_exam'].day} {MON[s['next_exam'].month-1]} {s['next_exam'].year}"
    if s["key"] == "closed": return f"Closed for {CYCLE}"
    m = (e.get("months") or {}).get("apply") or []
    return f"Usually opens {MON[m[0]-1]}" if m else "Dates not out yet"

def cd_fallback(e):
    s = status(e)
    m = (e.get("months") or {}).get("apply") or []
    if s["key"] == "closed": return f"<b>Closed</b><span>for {CYCLE}</span>"
    if s["key"] in ("open", "soon", "exam"): return f"<b>—</b><span>{H(next_text(e, s))}</span>"
    return f"<b>{MON[m[0]-1]}</b><span>applications<br>usually open</span>" if m else "<b>TBA</b><span>dates not<br>out yet</span>"

def detail_text(e):
    s = status(e); nc = e.get("next_cycle") or {}
    if s["key"] in ("open", "soon", "exam"): return next_text(e, s) + "."
    x = (nc.get("expected") or "").split("(")[0].strip().rstrip(";,. ")
    return (x + ".") if x else "Official dates are not out yet."

def pill(e):
    s = status(e)
    return f'<span data-st="{H(e["id"])}"><span class="pill {s["key"]}">{H(s["label"])}</span></span>'

# ---------------- data prep ----------------
ALIAS = {
    "Ahmedabad University (Amrut Mody School of Management; School of Arts & Sciences)": "Ahmedabad University",
    "IFMR Graduate School of Business, Krea University": "Krea University",
    "IFMR Graduate School of Business, Krea University — Integrated MBA": "Krea University",
    "Krea University (SIAS & IFMR GSB Integrated MBA)": "Krea University",
    "Krea University — School of Interwoven Arts and Sciences (SIAS)": "Krea University",
    "Institute of Management, Nirma University": "Nirma University – Institute of Management",
    "Nirma University – Institute of Management (Integrated BBA-MBA)": "Nirma University – Institute of Management",
    "Institute of Commerce, Nirma University": "Nirma University – Institute of Commerce",
    "KIIT School of Management": "KIIT University",
    "KIIT School of Management (KSOM)": "KIIT University",
    "KIIT Deemed University (commerce and economics programmes)": "KIIT University",
    "Mahindra University — School of Management": "Mahindra University",
    "O.P. Jindal Global University (JGBS, JSBF, JSGP, JSLH, JSIA and other schools)": "O.P. Jindal Global University",
    "Sai University — School of Arts and Sciences": "Sai University",
    "Shiv Nadar University (Institution of Eminence), Delhi-NCR": "Shiv Nadar University, Delhi-NCR",
    "IIM Jammu – eBBA": "IIM Jammu",
    "IIM Bangalore – BBA DBE (online)": "IIM Bangalore",
    "IIM Bangalore – Dorabji Tata School of Undergraduate Studies": "IIM Bangalore",
    "NMIMS (Deemed University)": "NMIMS (all campuses)",
    "AMU Centres Malappuram and Murshidabad": "Aligarh Muslim University (AMU)",
    "AMU Department of Economics (Faculty of Social Sciences)": "Aligarh Muslim University (AMU)",
    "AMU Faculty of Commerce": "Aligarh Muslim University (AMU)",
    "JMI Department of Commerce & Business Studies": "Jamia Millia Islamia (JMI)",
    "JMI Department of Economics": "Jamia Millia Islamia (JMI)",
    "MAHE Bengaluru — Department of Commerce": "Manipal Academy of Higher Education (MAHE)",
    "MAHE Department of Commerce, Manipal": "Manipal Academy of Higher Education (MAHE)",
    "Unitedworld School of Business, Karnavati University": "Karnavati University",
    "Unitedworld School of Liberal Arts & Mass Communication, Karnavati University": "Karnavati University",
    "Department of Management Studies, NALSAR University of Law": "NALSAR University of Law",
    "School of Liberal Studies, PDEU": "PDEU (Pandit Deendayal Energy University)",
    "Amity University (Noida and other campuses)": "Amity University",
    "IIM Kozhikode (Kochi campus)": "IIM Kozhikode",
    "TAPMI (Manipal and Bengaluru)": "TAPMI",
    "M.S. University of Baroda – Faculty of Commerce / Faculty of Arts (Economics)": "M.S. University of Baroda",
    "Parul University – Parul Institute of Commerce / Business Administration": "Parul University",
    "Navrachana University – School of Business & Law": "Navrachana University",
    "GITAM (Deemed to be) University": "GITAM University",
    "JAIN (Deemed-to-be University)": "Jain University",
    "Mount Carmel College (Autonomous)": "Mount Carmel College",
    "Bhavan's College (autonomous)": "Bhavan's College",
    "IIFT Kakinada (Indian Institute of Foreign Trade)": "IIFT Kakinada",
    "LM Thapar School of Management, Thapar Institute (TIET)": "Thapar Institute (TIET)",
    "St. Xavier's College (Autonomous), Ahmedabad": "St. Xavier's College, Ahmedabad",
    "H.L. College of Commerce (Gujarat University)": "H.L. College of Commerce",
    "SVKM's Narsee Monjee College of Commerce & Economics": "Narsee Monjee College of Commerce & Economics (NM College)",
    "SVKM's Usha Pravin Gandhi College": "Usha Pravin Gandhi College (UPG)",
    "K.C. College (Kishinchand Chellaram)": "K.C. College",
}
NO_PAGE = {"Jagannath Institute of Management Sciences / New Delhi Institute of Management"}
def is_group(name):
    if name in ALIAS: return False
    if name in NO_PAGE: return True
    return bool(re.search(r";|affiliated colleges|institutes:|campuses:|and others", name, re.I))

def canon(c):
    n = c.get("name", "").strip()
    if n == "St. Xavier's College (Autonomous)":
        return f"St. Xavier's College, {c.get('city') or 'India'}"
    return ALIAS.get(n, n)

EMPTY = {"", "—", "Not published", "Not published here", None}
CUT_RANK = {"official": 0, "unofficial": 1, "not_published": 2}
def merge_routes(routes):
    """Several source entries for the same college + exam become one route. Conflicting
    figures are kept side by side, labelled by programme, so nothing is lost."""
    by = collections.OrderedDict()
    for e, c in routes:
        by.setdefault(e["id"], []).append((e, c))
    out = []
    for eid, grp in by.items():
        if len(grp) == 1:
            out.append(grp[0]); continue
        e = grp[0][0]
        def lab(c):
            return ", ".join(re.sub(r"\s*\(.*?\)", "", p) for p in c.get("programmes", [])[:2]) or c.get("name", "")
        def item(l, v):  # values that already itemise by programme get no extra label
            return v if (";" in str(v) or ":" in str(v)) else f"{l}: {v}"
        m = {"name": grp[0][1].get("name"), "city": "", "state": "", "type": "", "url": "", "programmes": [], "_slug": grp[0][1].get("_slug")}
        for _, c in grp:
            for k in ("city", "state", "type", "url"):
                if not m[k] and c.get(k): m[k] = c[k]
            for p in c.get("programmes", []):
                if p not in m["programmes"]: m["programmes"].append(p)
        for k in ("seats", "fees", "selection", "placements"):
            vals = [(lab(c), c.get(k)) for _, c in grp if c.get(k) not in EMPTY]
            distinct = list(dict.fromkeys(v for _, v in vals))
            m[k] = distinct[0] if len(distinct) <= 1 and distinct else (" · ".join(item(l, v) for l, v in vals) if distinct else "")
        cuts = [(lab(c), c.get("cutoff") or {}) for _, c in grp if (c.get("cutoff") or {}).get("value") not in EMPTY]
        if not cuts:
            m["cutoff"] = {"value": "Not published", "status": "not_published", "year": None, "note": ""}
        elif len({ct.get("value") for _, ct in cuts}) == 1:
            m["cutoff"] = cuts[0][1]
        else:
            best = min(cuts, key=lambda x: CUT_RANK.get(x[1].get("status"), 2))[1]
            m["cutoff"] = {"value": " · ".join(item(l, ct.get("value")) for l, ct in cuts), "status": best.get("status"), "year": best.get("year"),
                           "note": "; ".join(dict.fromkeys(ct.get("note") for _, ct in cuts if ct.get("note") not in EMPTY))}
        out.append((e, m))
    return out

POPULAR = ["ipmat-indore", "cuet-ug", "nmims-npat", "symbiosis-set", "ipmat-rohtak", "jipmat", "christ-university-et", "iimk-bms-at",
           "iimb-ug-test", "mah-bba-bms-cet", "ggsipu-cet-bba", "ashoka-aptitude-assessment", "flame-feat", "jgu-jsat", "krea-kat",
           "aima-ugat", "xavier-entrance-test-mumbai", "hsnc-h-cet", "sat-digital-india", "snusat", "azim-premji-net", "jmi-entrance-ug",
           "amu-admission-test-ug", "nirma-ug-management", "pdeu-sls-aptitude-test", "kiitee-ug-management", "sjcc-smat", "sxc-kolkata-bms-test",
           "mit-wpu-cet", "iimb-dbe-test", "ahmedabad-university-ug", "jee-iim-ug", "gujarat-ug-commerce-merit", "isbf-imet", "presidency-kolkata-ug-test", "mse-ima-entrance", "upes-upesmet-ug", "xim-university-ug"]
def pop_rank(eid):
    return POPULAR.index(eid) if eid in POPULAR else 99

def prepare():
    with contextlib.redirect_stdout(io.StringIO()):
        exams = B.collect()
    for e in exams:
        meta = CAT[e["category"]]
        e["_cc"], e["_tok"] = meta["cc"], meta["tok"]
        e["_mono"] = mono_exam(e["name"])
    # colleges
    cols = collections.OrderedDict()
    for e in exams:
        for c in e["colleges"]:
            if is_group(c.get("name", "")):
                c["_slug"] = None; continue
            cn = canon(c)
            sl = slug(cn)
            c["_slug"] = sl
            if sl not in cols:
                cols[sl] = {"slug": sl, "name": cn, "city": "", "state": "", "type": "", "url": "", "routes": [], "cc": e["_cc"]}
            C = cols[sl]
            for k in ("city", "state", "type", "url"):
                if not C[k] and c.get(k): C[k] = c[k]
            C["routes"].append((e, c))
    for C in cols.values():
        C["routes"] = merge_routes(C["routes"])
        C["mono"] = mono_college(C["name"])
        C["exam_ids"] = list(dict.fromkeys(e["id"] for e, _ in C["routes"]))
        C["programmes"] = list(dict.fromkeys(p for _, c in C["routes"] for p in c.get("programmes", [])))
        C["tags"] = prog_tags(C["programmes"]) or sorted({p for e, _ in C["routes"] for p in e["programme_types"]}, key=[x[0] for x in PROGS].index)
        C["bucket"] = type_bucket(C["type"], C["name"])
        C["state"] = re.split(r"\s*/\s*", (C["state"] or "").replace("Delhi NCR", "Delhi"))[0].strip()
    return exams, cols

# ---------------- page shell ----------------
class Ctx:
    def __init__(self, mode, depth):
        self.mode, self.depth = mode, depth
        self.root = "../" * depth
        self.idx = "index.html" if mode == "preview" else ""
    def u(self, path=""):
        p = self.root + path + self.idx
        return p or "./"
    def ex(self, eid): return self.u(f"{eid}/")
    def col(self, sl): return self.u(f"colleges/{sl}/")
    def asset(self, name, ver=""):
        return f"{self.root}assets/{name}" + (f"?v={ver}" if ver and self.mode == "live" else "")

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,500;1,9..144,600&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@500;600;700&display=swap">'

def header(x, active="", search=True):
    a = lambda k: ' aria-current="page"' if active == k else ""
    tools = [("tools/eligibility/", "check", "Am I eligible?", "Find exams you can apply for"),
             ("tools/calendar/", "cal", "Exam calendar", "Every deadline for the next 12 months"),
             ("tools/compare/", "cols", "Compare exams", "Up to three side by side"),
             ("tools/english/", "lang", "English share", "How much of each paper is verbal")]
    menu = "".join(f'<a href="{x.u(p)}"><span class="ic">{ic(i)}</span><b>{t}</b><span>{d}</span></a>' for p, i, t, d in tools)
    srch = f'''<form class="hsearch" role="search" action="#" autocomplete="off">{ic("search")}<label class="sr" for="hq">Search exams and colleges</label><input id="hq" class="js-search" type="search" placeholder="Search exams, colleges, cities…"></form>''' if search else ""
    return f'''<header class="hdr"><div class="wrap hdr-in">
  <a class="logo" href="{x.u()}" aria-label="UG Exam Atlas home">{SHIELD}<span class="logo-t"><b>Exam Atlas</b><small>by Camp Verbal</small></span></a>
  <button class="burger" type="button" aria-label="Menu" aria-expanded="false" aria-controls="nav">{ic("menu")}</button>
  {srch}
  <nav class="nav" id="nav" aria-label="Main">
    <a href="{x.u('all/')}"{a("exams")}>Exams</a>
    <a href="{x.u('colleges/')}"{a("colleges")}>Colleges</a>
    <div class="dd"><button class="dd-btn" type="button" aria-expanded="false" aria-controls="dd-tools">Tools {ic("chev")}</button><div class="dd-menu" id="dd-tools" hidden>{menu}</div></div>
    <a href="{x.u('tools/my-list/')}"{a("list")}>My list <span class="badge" data-listcount hidden>0</span></a>
    <a class="btn gold nav-elig" href="{x.u('tools/eligibility/')}">Am I eligible?</a>
  </nav>
  <a class="btn gold sm hdr-cta" href="{x.u('tools/eligibility/')}">Am I eligible?</a>
</div></header>'''

def footer(x, exams):
    cv = "https://www.campverbal.com"
    return f'''<footer class="ftr"><div class="wrap ftr-in">
  <div><a class="logo" href="{x.u()}">{SHIELD}<span class="logo-t"><b>Exam Atlas</b><small>by Camp Verbal</small></span></a>
    <p>A free guide to every entrance exam for BBA, IPM, BMS, BCom, Economics, Finance and Liberal Arts in India: dates, patterns, eligibility, colleges and cutoffs.</p></div>
  <div><h4>Exams</h4><ul><li><a href="{x.u('all/')}">All {len(exams)} exams</a></li><li><a href="{x.u('all/')}#iim">IIMs &amp; IPM</a></li><li><a href="{x.u('all/')}#cuet">CUET &amp; central universities</a></li><li><a href="{x.u('all/')}#liberal">Liberal arts</a></li><li><a href="{x.u('colleges/')}">All colleges</a></li></ul></div>
  <div><h4>Tools</h4><ul><li><a href="{x.u('tools/eligibility/')}">Am I eligible?</a></li><li><a href="{x.u('tools/calendar/')}">Exam calendar</a></li><li><a href="{x.u('tools/compare/')}">Compare exams</a></li><li><a href="{x.u('tools/english/')}">English share</a></li><li><a href="{x.u('tools/my-list/')}">My list</a></li></ul></div>
  <div><h4>Camp Verbal</h4><ul><li><a href="{cv}/">Home</a></li><li><a href="{cv}/#products">Programmes</a></li><li><a href="{cv}/#enquiry">Contact us</a></li><li><span>letsgoverbal@gmail.com</span></li></ul></div>
  <div class="base"><span>Official sources first. Cutoffs are marked <span class="cut official">official</span> <span class="cut unofficial">unofficial</span> or <span class="cut not_published">not published</span>. Always confirm on the official site before you apply.</span><span>Updated {TODAY.day} {MON[TODAY.month-1]} {TODAY.year} · © {TODAY.year} Camp Verbal</span><span style="flex-basis:100%">Camp Verbal is an independent guide. It is not affiliated with any exam body, university or college listed here.</span></div>
</div></footer>'''

MONO_LONG = re.compile(r'class="mono([^"]*)">([^<]{6,})<')
def page(x, title, desc, canon_path, body, exams, active="", jsonld=None, search=True, ver=""):
    body = MONO_LONG.sub(lambda m: f'class="mono{m.group(1)} long">{m.group(2)}<', body)
    canonical = SITE + BASE + canon_path
    content = f'''<div id="atlas" data-root="{x.root}" data-idx="{x.idx}">
{header(x, active, search)}
<main id="main">{body}</main>
{footer(x, exams)}
</div>
<script src="{x.asset('data.js', ver)}"></script>
<script src="{x.asset('atlas.js', ver)}"></script>'''
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    if x.mode == "bare":  # artifact main page: the host adds doctype/head/body
        return f'''<title>UG Exam Atlas</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="{H(desc)}">
{FONTS}
<link rel="stylesheet" href="{x.asset('atlas.css')}">
{content}'''
    live = x.mode == "live"
    return f'''<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{H(title)}</title>
<meta name="description" content="{H(desc)}">
<link rel="canonical" href="{H(canonical)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Camp Verbal">
<meta property="og:title" content="{H(title)}"><meta property="og:description" content="{H(desc)}"><meta property="og:url" content="{H(canonical)}">
<meta property="og:image" content="{SITE}/og-image.jpg"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#13205a">
{'<link rel="icon" href="/favicon.ico"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">' if live else ''}
{FONTS}
<link rel="stylesheet" href="{x.asset('atlas.css', ver)}">
<style>html{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}[hidden]{{display:none!important}}</style>
{'<script defer src="/_vercel/insights/script.js"></script>' if live else ''}
{ld}
</head>
<body>
<a class="sr" href="#main">Skip to content</a>
{content}
</body>
</html>
'''

# ---------------- reusable blocks ----------------
def ecard(x, e):
    p = e.get("pattern") or {}
    patt = " · ".join(v for v in [f"{p['total_questions']} Qs" if p.get("total_questions") else "", f"{p['duration_min']} min" if p.get("duration_min") else ""] if v) or "—"
    va = f"{round(e['va_share']*100)}%" if e.get("va_share") is not None else "—"
    return f'''<article class="ecard js-card" data-id="{e['id']}">
  <div class="hd"><span class="mono {e['_cc']}">{H(e['_mono'])}</span><div><h3><a href="{x.ex(e['id'])}">{H(e['name'])}</a></h3><p class="by">{H(e.get('conducted_by') or e.get('full_name'))}</p></div>{star(e['id'], True)}</div>
  <div>{pill(e)}</div>
  <dl class="kv"><div><dt>Next step</dt><dd data-next="{e['id']}">{H(next_text(e))}</dd></div><div><dt>Pattern</dt><dd>{H(patt)}</dd></div><div><dt>English</dt><dd>{va}</dd></div><div><dt>Colleges</dt><dd>{len(e['colleges'])}</dd></div></dl>
  <div class="row"><span class="tags">{"".join(f'<span class="tag">{H(t)}</span>' for t in e['programme_types'][:3])}</span><label class="cmpbox"><input type="checkbox" data-cmp="{e['id']}"> Compare</label></div>
</article>'''

def lcard(x, e):
    p = e.get("pattern") or {}
    patt = " · ".join(v for v in [f"{p['total_questions']} Qs" if p.get("total_questions") else "", f"{p['duration_min']} min" if p.get("duration_min") else ""] if v) or "—"
    va = f"{round(e['va_share']*100)}%" if e.get("va_share") is not None else "—"
    search = " ".join([e["name"], e.get("full_name", ""), e.get("conducted_by", "")] + [c["name"] + " " + (c.get("city") or "") for c in e["colleges"]]).lower()
    lvl = e.get("level") or ""
    lvl_tok = "national" if "national" in lvl.lower() else "state" if "state" in lvl.lower() else "university"
    return f'''<article class="lcard js-card" data-id="{e['id']}" data-name="{H(e['name'].lower())}" data-cols="{len(e['colleges'])}" data-va="{e['va_share'] if e.get('va_share') is not None else ''}" data-prog="{'|'.join(e['programme_types'])}" data-cat="{e['_tok']}" data-level="{lvl_tok}" data-status="" data-pop="{pop_rank(e['id'])}" data-search="{H(search)}">
  <span class="mono {e['_cc']}">{H(e['_mono'])}</span>
  <div style="min-width:0">
    <div class="t1"><h3><a href="{x.ex(e['id'])}">{H(e['name'])}</a></h3>{pill(e)}</div>
    <p class="by">{H(e.get('conducted_by') or '')}{' · ' + H(lvl) if lvl else ''}</p>
    <dl class="kv"><div><dt>Next step</dt><dd data-next="{e['id']}">{H(next_text(e))}</dd></div><div><dt>Pattern</dt><dd>{H(patt)}</dd></div><div><dt>English share</dt><dd>{va}</dd></div><div><dt>Colleges</dt><dd>{len(e['colleges'])}</dd></div></dl>
    <div class="tags">{"".join(f'<span class="tag gold">{H(t)}</span>' for t in e['programme_types'])}</div>
  </div>
  <div class="acts">{star(e['id'])}<label class="cmpbox"><input type="checkbox" data-cmp="{e['id']}"> Compare</label><a class="btn sm" href="{x.ex(e['id'])}">View exam</a></div>
</article>'''

def dcard(x, e):
    s = status(e)
    return f'''<article class="dcard" data-id="{e['id']}">
  <div class="top"><span data-st="{e['id']}"><span class="pill {s['key']}">{H(s['label'])}</span></span>{star(e['id'], True)}</div>
  <div><h3><a href="{x.ex(e['id'])}">{H(e['name'])}</a></h3><p class="sub">{H(', '.join(e['programme_types'][:4]))}</p></div>
  <div class="cd" data-cd="{e['id']}">{cd_fallback(e)}</div>
  <div class="meter"><i style="width:0"></i></div>
  <div class="foot"><span data-next="{e['id']}">{H(next_text(e))}</span><span>{plural(len(e['colleges']), 'college')}</span></div>
</article>'''

def col_card(x, C, extra=""):
    href = x.col(C["slug"])
    loc = ", ".join(v for v in [C["city"], C["state"]] if v)
    search = (C["name"] + " " + loc + " " + " ".join(C["programmes"])).lower()
    return f'''<article class="ccard js-card" data-name="{H(C['name'].lower())}" data-state="{H(C['state'])}" data-prog="{'|'.join(C['tags'])}" data-type="{H(C['bucket'])}" data-exam="{'|'.join(C['exam_ids'])}" data-nex="{len(C['exam_ids'])}" data-search="{H(search)}">
  <div class="hd"><span class="mono sm {C['cc']}">{H(C['mono'])}</span><div><h3><a class="stretch" href="{href}">{H(C['name'])}</a></h3><p class="loc">{H(loc)}{' · ' + H(C['bucket']) if C['bucket'] != 'Other' else ''}</p></div></div>
  <div class="tags">{"".join(f'<span class="tag">{H(t)}</span>' for t in C['tags'][:4])}</div>
  <div class="cutline"><b>{plural(len(C['exam_ids']), 'exam')}</b> <small>{H(', '.join(EXAMS_BY_ID[i]['name'] for i in C['exam_ids'][:4]))}</small></div>{extra}
</article>'''

def donut(v):
    r, C = 19, 2 * math.pi * 19
    return f'<svg width="54" height="54" viewBox="0 0 54 54" role="img" aria-label="{v}% English"><circle cx="27" cy="27" r="{r}" fill="none" stroke="var(--line2)" stroke-width="6"/><circle cx="27" cy="27" r="{r}" fill="none" stroke="var(--gold)" stroke-width="6" stroke-linecap="round" stroke-dasharray="{max(.01, C*v/100):.2f} {C:.2f}" transform="rotate(-90 27 27)"/><text x="27" y="31" text-anchor="middle" font-size="12" font-weight="700" font-family="JetBrains Mono, monospace" fill="var(--ink)">{v}%</text></svg>'

def contour_svg():
    # faint "atlas" contour lines for the hero
    paths = []
    cx, cy = 520, 300
    for k in range(1, 12):
        r = 30 + k * 36
        pts = []
        for i in range(0, 361, 6):
            a = math.radians(i)
            w = 1 + 0.10 * math.sin(3 * a + k * .7) + 0.06 * math.sin(5 * a - k) + 0.04 * math.cos(7 * a + k * 1.3)
            pts.append(f"{cx + r * w * math.cos(a):.1f},{cy + r * .78 * w * math.sin(a):.1f}")
        op = .26 - k * .016
        paths.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#e2b23e" stroke-opacity="{op:.3f}" stroke-width="{1.4 if k % 3 == 0 else .9}"/>')
    grid = "".join(f'<path d="M{x} -20 Q{x+60} 300 {x} 640" fill="none" stroke="#ffffff" stroke-opacity=".05"/>' for x in range(80, 1000, 110))
    pin = f'<g transform="translate({cx-11} {cy-30})"><path d="M11 30s9-8 9-15a9 9 0 1 0-18 0c0 7 9 15 9 15z" fill="#e2b23e"/><circle cx="11" cy="15" r="3.4" fill="#13205a"/></g>'
    return f'<svg viewBox="0 0 1000 620" aria-hidden="true">{grid}{"".join(paths)}{pin}</svg>'

def crumbs(x, items):
    out = []
    for i, (t, href) in enumerate(items):
        out.append(f'<a href="{href}">{H(t)}</a>' if href else f'<span aria-current="page">{H(t)}</span>')
    return '<nav class="crumbs wrap" aria-label="Breadcrumb">' + '<span aria-hidden="true">›</span>'.join(out) + '</nav>'

# ---------------- pages ----------------
EXAMS_BY_ID = {}

def page_home(x, exams, cols, ver):
    popular = [i for i in POPULAR[:6] if i in EXAMS_BY_ID]
    rail = [e for e in exams if (e.get("next_cycle") or {}).get("apply_close") or (e.get("next_cycle") or {}).get("apply_open") or (e.get("next_cycle") or {}).get("exam_dates") or (e.get("next_cycle") or {}).get("rounds") or (e.get("next_cycle") or {}).get("status") == "open"]
    rail.sort(key=lambda e: (status(e)["key"] != "open", e["name"]))
    prog_icons = {"IPM": "cap", "BBA": "brief", "BMS": "bars", "BCom": "ledger", "Economics": "trend", "Finance": "coins", "Liberal Arts": "feather"}
    ptiles = "".join(f'''<a class="tile" href="{x.u('all/')}#{tok}"><span class="ic">{ic(prog_icons[p])}</span>{ic("arrow", "arr")}<h3>{p}</h3><p>{d}</p><span class="count">{sum(p in e['programme_types'] for e in exams)} exams · {sum(p in C['tags'] for C in cols.values())} colleges</span></a>''' for p, tok, d in PROGS)
    ctiles = "".join(f'''<a class="tile" href="{x.u('all/')}#{c[1]}"><span class="ic" style="background:var(--{c[2]}s);color:var(--{c[2]})">{ic("bldg")}</span>{ic("arrow", "arr")}<h3>{c[3]}</h3><p>{c[4]}</p><span class="count">{sum(e['category'] == c[0] for e in exams)} exams</span></a>''' for c in CATS)
    states = collections.Counter(C["state"] for C in cols.values() if C["state"])
    schips = "".join(f'<a class="chip" href="{x.u("colleges/")}#{slug(s)}">{H(s)} <b>{n}</b></a>' for s, n in states.most_common())
    tools = [("tools/eligibility/", "check", "Am I eligible?", "Enter your marks, stream and age. See every exam you can apply for, and why not for the rest."),
             ("tools/calendar/", "cal", "Exam calendar", "Every application window and exam date for the next 12 months, on one chart."),
             ("tools/compare/", "cols", "Compare exams", "Put up to three exams side by side: dates, pattern, eligibility and selection."),
             ("tools/english/", "lang", "English share", "See how much of each paper is verbal ability and reading. One prep covers most exams.")]
    ttiles = "".join(f'<a class="tile" href="{x.u(p)}"><span class="ic">{ic(i)}</span>{ic("arrow", "arr")}<h3>{t}</h3><p>{d}</p></a>' for p, i, t, d in tools)
    pop_links = " ".join(f'<a href="{x.ex(i)}">{H(EXAMS_BY_ID[i]["name"])}</a>' for i in ["ipmat-indore", "cuet-ug", "nmims-npat", "symbiosis-set", "christ-university-et"] if i in EXAMS_BY_ID)
    open_n = sum(status(e)["key"] == "open" for e in exams)
    body = f'''
<section class="hero"><div class="hero-art">{contour_svg()}</div>
  <div class="wrap hero-in">
    <p class="eyebrow">Free guide · UG admissions {CYCLE}</p>
    <h1>Find your exam. <em>Find every college it opens.</em></h1>
    <p class="lede">{len(exams)} entrance exams and {len(cols)} colleges for BBA, IPM, BMS, BCom, Economics, Finance and Liberal Arts. Dates, patterns, eligibility and cutoffs in one place.</p>
    <form class="bigsearch" role="search" action="#" autocomplete="off">{ic("search")}<label class="sr" for="bq">Search an exam, college or city</label><input id="bq" class="js-search" type="search" placeholder="Try “IPMAT”, “SRCC” or “Ahmedabad”"><button class="btn gold" type="submit">{ic("search")}<span>Search</span></button></form>
    <p class="popular">Popular: {pop_links}</p>
  </div>
</section>
<div class="wrap statband"><div class="stats">
  <div><b>{len(exams)}</b><span>Entrance exams</span></div>
  <div><b>{len(cols)}</b><span>Colleges profiled</span></div>
  <div class="live"><b data-opencount>{open_n}</b><span>Taking applications now</span></div>
  <div><b>{len(states)}</b><span>States covered</span></div>
</div></div>

<section class="sec first"><div class="wrap">
  <div class="sec-head"><div><p class="eyebrow">Deadlines</p><h2>Open now and coming up</h2><p>Live countdowns for the {CYCLE} admission cycle. Save an exam with ★ to track it.</p></div>
    <div class="rail-nav"><button type="button" data-rail="prev" aria-label="Scroll back">{ic("left")}</button><button type="button" data-rail="next" aria-label="Scroll forward">{ic("arrow")}</button></div></div>
  <div class="rail-wrap"><div class="rail">{"".join(dcard(x, e) for e in rail)}</div><p class="empty js-railempty" hidden>Nothing is open right now. Most exams open applications between January and March. See the <a class="link" href="{x.u('tools/calendar/')}">exam calendar</a>.</p></div>
</div></section>

<section class="sec tint"><div class="wrap">
  <div class="sec-head"><div><p class="eyebrow">Browse</p><h2>What do you want to study?</h2><p>Pick a programme to see every exam that leads to it.</p></div><a class="more" href="{x.u('all/')}">All exams {ic("arrow")}</a></div>
  <div class="tiles t4">{ptiles}</div>
</div></section>

<section class="sec"><div class="wrap">
  <div class="sec-head"><div><p class="eyebrow">Most searched</p><h2>Popular exams</h2></div><a class="more" href="{x.u('all/')}">See all {len(exams)} exams {ic("arrow")}</a></div>
  <div class="grid3">{"".join(ecard(x, EXAMS_BY_ID[i]) for i in popular)}</div>
</div></section>

<section class="sec tint"><div class="wrap">
  <div class="sec-head"><div><p class="eyebrow">How it works</p><h2>From “which exams?” to “applied” in three steps</h2></div></div>
  <div class="steps">
    <div class="step"><span class="n">Step 1</span><h3>Check what you qualify for</h3><p>Enter your Class X and XII marks, stream and date of birth. We check every exam's rules for you.</p><a class="more" href="{x.u('tools/eligibility/')}">Am I eligible? {ic("arrow")}</a></div>
    <div class="step"><span class="n">Step 2</span><h3>Shortlist your exams</h3><p>Open any exam to see its pattern, selection process and every college it opens. Save the ones you want with ★.</p><a class="more" href="{x.u('all/')}">Browse exams {ic("arrow")}</a></div>
    <div class="step"><span class="n">Step 3</span><h3>Never miss a deadline</h3><p>Your list sorts itself by the next deadline. Sign up and we'll message you before each one.</p><a class="more" href="{x.u('tools/my-list/')}">My list {ic("arrow")}</a></div>
  </div>
</div></section>

<section class="sec"><div class="wrap">
  <div class="sec-head"><div><p class="eyebrow">Browse</p><h2>Exams by type</h2></div></div>
  <div class="tiles t5">{ctiles}</div>
</div></section>

<section class="sec tint"><div class="wrap">
  <div class="sec-head"><div><p class="eyebrow">Colleges</p><h2>Find colleges by state</h2><p>Every college page shows each exam that gets you in, with cutoffs.</p></div><a class="more" href="{x.u('colleges/')}">All {len(cols)} colleges {ic("arrow")}</a></div>
  <div class="states">{schips}</div>
</div></section>

<section class="sec"><div class="wrap">
  <div class="sec-head"><div><p class="eyebrow">Free tools</p><h2>Plan your exam season</h2></div></div>
  <div class="tiles t4f">{ttiles}</div>
</div></section>

<section class="sec" style="padding-top:0"><div class="wrap"><div class="cvband">
  <div><p class="eyebrow">From the makers of this guide</p><h2>The English section decides more seats than you think</h2>
  <p>Verbal ability and reading make up a third to half of most exams here. Camp Verbal Practice gives you timed verbal tests built for these exams, with a root-based vocabulary course and an active reading course on the way.</p></div>
  <a class="btn gold" href="https://www.campverbal.com/#products">Explore Camp Verbal {ic("arrow")}</a>
</div></div></section>

<section class="sec tint"><div class="wrap">
  <div class="trust">
    <div><h3>{ic("shield")} Official sources first</h3><p>Dates, patterns and rules come from each institute's own site and bulletin. News and coaching sites are used only where nothing official exists.</p></div>
    <div><h3>{ic("tag")} Every cutoff labelled</h3><p>Each cutoff says whether it is official, an unofficial estimate, or not published at all, with the year and its source.</p></div>
    <div><h3>{ic("refresh")} Updated each cycle</h3><p>Last updated {TODAY.day} {MON[TODAY.month-1]} {TODAY.year}. Dates not yet announced are shown as estimates from last year, and marked that way.</p></div>
  </div>
</div></section>'''
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": "UG Exam Atlas by Camp Verbal", "url": SITE + BASE}
    return page(x, f"UG Exam Atlas {CYCLE}: Every BBA, IPM, BCom, Economics & Liberal Arts Entrance Exam | Camp Verbal",
                f"{len(exams)} Indian UG entrance exams and {len(cols)} colleges: what's open now, am I eligible, exam patterns, dates and cutoffs. Free, by Camp Verbal.",
                "", body, exams, "", ld, search=False, ver=ver)

def page_all(x, exams, ver):
    def cb(group, val, label, n, hashtok=None):
        return f'<label><input type="checkbox" data-f="{group}" value="{H(val)}" data-hash="{H(hashtok or slug(val))}"> {H(label)}<span class="n">{n}</span></label>'
    progs = "".join(cb("prog", p, p, sum(p in e["programme_types"] for e in exams), tok) for p, tok, _ in PROGS)
    cats = "".join(cb("cat", c[1], c[3], sum(e["category"] == c[0] for e in exams), c[1]) for c in CATS)
    stat = cb("status", "open", "Open now", "", "open") + cb("status", "soon", "Opening soon", "", "soon") + cb("status", "exam", "Exam coming up", "", "exam") + cb("status", "na", "Dates not out yet", "", "na")
    lvl = "".join(cb("level", v, l, sum(1 for e in exams if (("national" if "national" in (e.get("level") or "").lower() else "state" if "state" in (e.get("level") or "").lower() else "university") == v)), v) for v, l in [("national", "National"), ("state", "State"), ("university", "One university")])
    body = f'''{crumbs(x, [("Exam Atlas", x.u()), ("All exams", None)])}
<section class="tool-hero" style="padding-top:8px"><div class="wrap"><h1>All entrance exams</h1><p>Every exam that leads to BBA, IPM, BMS, BCom, Economics, Finance and Liberal Arts. Filter by programme or type, and sort by the next deadline.</p></div></section>
<section class="tool"><div class="wrap dir js-dir">
  <aside class="filters" aria-label="Filters">
    <div class="fhead"><h2>Filters</h2><button class="clear js-clear" type="button">Clear all</button></div>
    <label class="sr" for="fq">Search within exams</label><input id="fq" class="fsearch js-fq" type="search" placeholder="Search within results…">
    <fieldset class="fgroup"><legend>Programme</legend>{progs}</fieldset>
    <fieldset class="fgroup"><legend>Status for {CYCLE}</legend>{stat}</fieldset>
    <fieldset class="fgroup"><legend>Exam type</legend>{cats}</fieldset>
    <fieldset class="fgroup"><legend>Level</legend>{lvl}</fieldset>
    <button class="btn gold apply js-apply" type="button">Show results</button>
  </aside>
  <div style="min-width:0">
    <div class="results-head"><p class="count"><b class="js-count">{len(exams)}</b> exams</p>
      <div class="results-tools"><button class="btn sm flt-btn" type="button">{ic("filter")} Filters <span class="js-fcount"></span></button>
      <label class="sr" for="sort">Sort</label><select id="sort" class="js-sort"><option value="rec">Recommended</option><option value="dl">Next deadline first</option><option value="name">Name A–Z</option><option value="cols">Most colleges</option><option value="va">Most English</option></select></div></div>
    <div class="list js-results">{"".join(lcard(x, e) for e in exams)}</div>
    <div class="empty js-empty" hidden>No exam matches these filters. <button class="btn sm js-clear" type="button" style="margin-left:8px">Clear filters</button></div>
  </div>
</div></section>'''
    return page(x, f"All UG Entrance Exams {CYCLE}: BBA, IPM, BCom, Economics, Liberal Arts | Camp Verbal",
                f"Filter {len(exams)} Indian UG entrance exams by programme, type and deadline. Patterns, English share and colleges for each.",
                "all/", body, exams, "exams", ver=ver)

def faqs_for(e):
    nc, cy, p = e.get("next_cycle") or {}, e.get("cycle_2026") or {}, e.get("pattern") or {}
    out = []
    exd = [fdate(d) for d in nc.get("exam_dates") or [] if fdate(d)]
    when = f"The {CYCLE} exam is scheduled for {', '.join(exd)}." if exd else (f"Official {CYCLE} dates are not out yet. {nc['expected'].rstrip('.')}." if nc.get("expected") else "")
    if cy.get("exam_date"): when += f" Last year's exam was held on {cy['exam_date'].rstrip('.')}."
    if when.strip(): out.append((f"When is {e['name']} {CYCLE}?", when.strip()))
    if e.get("eligibility"): out.append((f"Who can apply for {e['name']}?", e["eligibility"]))
    secs = p.get("sections") or []
    meta = ", ".join(v for v in [f"{p['total_questions']} questions" if p.get("total_questions") else "", f"{p['duration_min']} minutes" if p.get("duration_min") else ""] if v)
    if meta or secs:
        out.append((f"What is the {e['name']} exam pattern?", (meta + ". " if meta else "") + "; ".join(f"{s.get('name')}" + (f" ({s['questions']} questions)" if s.get("questions") else "") for s in secs) + (f". Marking: {p['marking']}" if p.get("marking") else "")))
    n = len(e["colleges"])
    if n:
        out.append((f"Which colleges accept {e['name']}?", ", ".join(c["name"] for c in e["colleges"][:25]) + (f", and {n-25} more." if n > 25 else ".")))
    if e.get("verbal_weight"): out.append((f"How much English is in {e['name']}?", e["verbal_weight"]))
    if e.get("selection_process"): out.append((f"How does selection work after {e['name']}?", e["selection_process"]))
    return out

def elig_rows(e):
    g = e.get("elig") or {}
    rows = []
    rows.append(("Class XII", f"{g['min_12_pct']}%+" if g.get("min_12_pct") is not None else "No minimum"))
    rows.append(("Class X", f"{g['min_10_pct']}%+" if g.get("min_10_pct") is not None else "No minimum"))
    st = g.get("streams") or ["Any"]
    rows.append(("Stream", "Any" if "Any" in st else " / ".join(st)))
    rows.append(("Maths", "Required" if g.get("maths_required") is True else "Not required" if g.get("maths_required") is False else "Check"))
    rows.append(("Age limit", f"{g['max_age']} years" if g.get("max_age") is not None else "No limit"))
    return rows if e.get("elig") else []

def timeline(e):
    nc = e.get("next_cycle") or {}
    rounds = nc.get("rounds") or []
    if rounds:
        rows = "".join(f"<tr><td>{H(r.get('label'))}</td><td class='n'>{H(fdate(r.get('apply_close')) or 'tbc')}</td><td class='n'>{H(fdate(r.get('exam_date')) or 'tbc')}</td></tr>" for r in rounds)
        return f'<div class="tbl"><table><thead><tr><th>Round</th><th>Apply by</th><th>Test</th></tr></thead><tbody>{rows}</tbody></table></div>'
    steps = []
    if nc.get("apply_open"): steps.append(("Applications open", pdate(nc["apply_open"]), ""))
    if nc.get("apply_close"): steps.append(("Last date to apply", pdate(nc["apply_close"]), ""))
    for d in nc.get("exam_dates") or []:
        if pdate(d): steps.append(("Exam", pdate(d), ""))
    if not steps:
        return ""
    steps.sort(key=lambda s: s[1])
    nxt = next((i for i, s in enumerate(steps) if s[1] >= TODAY), None)
    lis = "".join(f'<li class="{"done" if s[1] < TODAY else "next" if i == nxt else ""}"><span class="dot"></span><div><b>{H(s[0])}</b></div><span class="when">{s[1].day} {MON[s[1].month-1]} {s[1].year}</span></li>' for i, s in enumerate(steps))
    return f'<ol class="tl">{lis}</ol>'

def prep_box(e):
    va = round(e["va_share"] * 100) if e.get("va_share") else None
    if not va:
        return ""
    return f'''<div class="box prep"><span class="eyebrow">From Camp Verbal</span><h3>{va}% of this paper is English</h3>
  <p>Practise reading comprehension, vocabulary and verbal reasoning with timed tests built for IPM, BBA and liberal arts entrance exams.</p>
  <a class="btn gold" href="https://www.campverbal.com/#products">See Camp Verbal programmes</a></div>'''

def page_exam(x, e, exams, cols, ver):
    nc, cy, p = e.get("next_cycle") or {}, e.get("cycle_2026") or {}, e.get("pattern") or {}
    n = len(e["colleges"])
    va = round(e["va_share"] * 100) if e.get("va_share") is not None else None
    secs = p.get("sections") or []
    # --- hero & stats
    hero = f'''{crumbs(x, [("Exam Atlas", x.u()), ("Exams", x.u('all/')), (e['name'], None)])}
<section class="phero"><div class="wrap phero-in">
  <span class="mono lg {e['_cc']}">{H(e['_mono'])}</span>
  <div style="min-width:0"><h1>{H(e['name'])}</h1><p class="sub">{H(e.get('full_name'))}{' · ' + H(e['conducted_by']) if e.get('conducted_by') else ''}</p>
    <div class="tags">{pill(e)}{"".join(f'<span class="tag gold">{H(t)}</span>' for t in e['programme_types'])}{f'<span class="tag">{H(e["level"])}</span>' if e.get('level') else ''}{f'<span class="tag">{H(e["mode"])}</span>' if e.get('mode') else ''}</div></div>
  <div class="acts">{star(e['id'])}<button class="btn" type="button" data-cmp="{e['id']}">+ Compare</button>{f'<a class="btn gold" href="{H(nc.get("url") or e.get("official_url"))}" target="_blank" rel="noopener">Official site {ic("ext")}</a>' if (nc.get("url") or e.get("official_url")) else ''}</div>
</div>
<div class="wrap"><dl class="statgrid">
  <div class="hl"><dt>Coming cycle</dt><dd class="cd" data-cd="{e['id']}" style="font:inherit">{cd_fallback(e)}</dd></div>
  <div><dt>Last exam</dt><dd>{H(short(cy.get('exam_date'), 28) or '—')}</dd></div>
  <div><dt>Pattern</dt><dd>{H(str(p['total_questions']) + ' Qs' if p.get('total_questions') else '—')}<small>{H(str(p['duration_min']) + ' minutes' if p.get('duration_min') else '')}</small></dd></div>
  <div><dt>English share</dt><dd>{f'{va}%' if va is not None else '—'}<small>{'of the paper' if va is not None else ''}</small></dd></div>
  <div><dt>Application fee</dt><dd style="font-size:16px">{H(short(cy.get('fee'), 30) or '—')}</dd></div>
  <div><dt>Colleges</dt><dd>{n}<small>accept this exam</small></dd></div>
</dl></div></section>'''
    tabs = [("overview", "Overview"), ("dates", "Dates"), ("eligibility", "Eligibility"), ("pattern", "Pattern"), ("selection", "Selection"), ("colleges", f"Colleges ({n})"), ("faqs", "FAQs"), ("sources", "Sources")]
    secnav = '<nav class="secnav" aria-label="On this page"><div class="wrap"><ul>' + "".join(f'<li><a href="#{k}">{t}</a></li>' for k, t in tabs) + '</ul></div></nav>'
    # --- overview
    top_cols = [c["name"] for c in e["colleges"][:3]]
    ov = f"{e['name']} is run by {e.get('conducted_by') or 'the institute'} for admission to {join_and(e['programme_types']) or 'undergraduate'} programmes."
    if n: ov += f" {n} {'college accepts' if n == 1 else 'colleges listed here accept'} it" + (f", including {join_and(top_cols)}." if n > 1 else f": {top_cols[0]}.")
    overview = f'<section id="overview"><h2>Overview</h2><p class="prose">{H(ov)}</p>{f"<p class=prose>{H(e["notes"])}</p>" if e.get("notes") else ""}</section>'
    # --- dates
    est = nc.get("source_status")
    tl = timeline(e)
    estnote = ""
    if est == "estimated" or not tl:
        estnote = f'<div class="estnote">{ic("cal")}<span><b>Official {CYCLE} dates are not out yet.</b> {H(nc.get("expected") or "")}</span></div>'
    elif est == "reported":
        estnote = f'<div class="estnote rep">{ic("doc")}<span>These dates come from news reports of the official schedule. Confirm on the official site.</span></div>'
    lastc = f'''<div class="card"><h3>Last cycle (2026)</h3><dl class="kv{' wide' if not tl else ''}">
    <div><dt>Applications</dt><dd style="white-space:normal">{H(cy.get('application_window') or '—')}</dd></div>
    <div><dt>Exam</dt><dd style="white-space:normal">{H(cy.get('exam_date') or '—')}</dd></div>
    {f'<div><dt>Result</dt><dd style="white-space:normal">{H(cy["result"])}</dd></div>' if cy.get('result') else ''}
    <div><dt>Application fee</dt><dd style="white-space:normal">{H(cy.get('fee') or '—')}</dd></div></dl></div>'''
    dates = f'''<section id="dates"><h2>Dates <small>{CYCLE} admissions</small></h2>{estnote}{f'<div class="panel2"><div>{tl}</div>{lastc}</div>' if tl else lastc}</section>'''
    # --- eligibility
    er = elig_rows(e)
    facts = "".join(f'<div class="{"no" if v in ("No minimum", "No limit", "Not required", "Any") else ""}"><dt>{H(k)}</dt><dd>{H(v)}</dd></div>' for k, v in er)
    elig = f'''<section id="eligibility"><h2>Who can apply</h2>{f'<dl class="facts">{facts}</dl>' if facts else ''}<p class="prose">{H(e.get('eligibility') or 'Not published.')}</p>{f'<p class="note">{H((e.get("elig") or {}).get("note"))}</p>' if (e.get("elig") or {}).get("note") else ''}
  <p style="margin-top:16px"><a class="btn" href="{x.u('tools/eligibility/')}">{ic("check")} Check all exams against your marks</a></p></section>'''
    # --- pattern
    isv = lambda s: bool(re.search(r"verbal|english|reading|\brc\b|language|grammar|vocab|comprehension|writing|essay|critical", s.get("name", ""), re.I))
    numd = [s for s in secs if isinstance(s.get("questions"), (int, float)) and s["questions"] > 0]
    pbar = ""
    if len(numd) > 1:
        pbar = '<div class="pbar" role="img" aria-label="Questions per section">' + "".join(f'<span class="{"v" if isv(s) else ""}" style="flex:{s["questions"]}" title="{H(s["name"])}: {s["questions"]}">{s["questions"]}</span>' for s in numd) + '</div><div class="plegend">' + "".join(f'<span><i class="{"v" if isv(s) else ""}"></i>{H(s["name"])}</span>' for s in numd) + '</div>'
    rows = "".join(f"<tr><td>{H(s.get('name'))}</td><td class='n'>{H(s.get('questions') if s.get('questions') is not None else '—')}</td><td class='n'>{H(s.get('time_min') if s.get('time_min') is not None else '—')}</td><td>{H(s.get('notes', ''))}</td></tr>" for s in secs)
    meta = " · ".join(v for v in [f"{p['total_questions']} questions" if p.get("total_questions") else "", f"{p['duration_min']} minutes" if p.get("duration_min") else "", "sectional timing" if p.get("sectional_timing") else ""] if v)
    pattern = f'''<section id="pattern"><h2>Exam pattern <small>{H(meta)}</small></h2>{pbar}
  {f'<div class="tbl"><table><thead><tr><th>Section</th><th>Questions</th><th>Minutes</th><th>Notes</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else '<p class="prose">The section-wise pattern is not published.</p>'}
  {f'<p class="note"><b>Marking:</b> {H(p["marking"])}{" " + H(p["notes"]) if p.get("notes") else ""}</p>' if p.get("marking") else ''}
  <div class="eng">{donut(va) if va is not None else ''}<p><b>English &amp; verbal:</b> {H(e.get('verbal_weight') or 'Not published')}</p></div></section>'''
    selection = f'<section id="selection"><h2>How selection works</h2><p class="prose">{H(e.get("selection_process") or "Not published.")}</p></section>'
    # --- colleges
    def ccard(c, i):
        ct = c.get("cutoff") or {}
        stt = ct.get("status") or "not_published"
        val = ct.get("value") if ct.get("value") and ct.get("value") != "Not published" else ""
        note = ct.get("note") if ct.get("note") and ct.get("note") != "Not published" else ""
        loc = ", ".join(v for v in [c.get("city"), c.get("state")] if v)
        name = f'<a class="stretch" href="{x.col(c["_slug"])}">{H(c["name"])}</a>' if c.get("_slug") else H(c["name"])
        mono = mono_college(canon(c)) if c.get("_slug") else "+"
        srch = (c["name"] + " " + loc + " " + " ".join(c.get("programmes", []))).lower()
        return f'''<article class="ccard{' more' if i >= 8 else ''}" data-search="{H(srch)}">
  <div class="hd"><span class="mono sm {e['_cc']}">{H(mono)}</span><div><h3>{name}</h3><p class="loc">{H(loc)}{' · ' + H(c['type']) if c.get('type') else ''}</p></div></div>
  <dl><div class="w"><dt>Programmes</dt><dd>{H('; '.join(c.get('programmes', [])) or '—')}</dd></div><div><dt>Seats</dt><dd>{H(c.get('seats') or '—')}</dd></div><div><dt>Fees</dt><dd>{H(c.get('fees') or '—')}</dd></div></dl>
  <div class="cutline"><span class="cut {H(stt)}">{H(stt.replace('_', ' '))}{' · ' + H(ct['year']) if ct.get('year') and stt != 'not_published' else ''}</span> {H(val)}{f'<small>{H(note)}</small>' if note else ''}</div>
</article>'''
    ccards = "".join(ccard(c, i) for i, c in enumerate(sorted(e["colleges"], key=lambda c: (c.get("cutoff", {}).get("status") != "official", c["name"]))))
    colsec = f'''<section id="colleges"><h2>Colleges that accept {H(e['name'])} <small>{n} listed</small></h2>
  {f'<div class="subtools"><label class="sr" for="colq">Filter colleges</label><input id="colq" class="js-colq" type="search" placeholder="Filter by name, city or programme…"></div>' if n > 6 else ''}
  <style>.ccard.more{{display:none}}</style>
  <div class="cgrid">{ccards}</div><p class="empty js-colempty" hidden>No college matches that filter.</p>
  {f'<div class="showall"><button class="btn" type="button" data-showall>Show all {n} colleges</button></div>' if n > 8 else ''}</section>''' if n else ""
    # --- faqs, sources
    fq = faqs_for(e)
    faqs = '<section id="faqs"><h2>Common questions</h2><div class="faq">' + "".join(f"<details><summary>{H(q)}</summary><p>{H(a)}</p></details>" for q, a in fq) + '</div></section>'
    papers = "".join(f'<a class="paper" href="{H(pp["url"])}" target="_blank" rel="noopener">{ic("doc")} {H(pp.get("label") or "Sample paper")}</a>' for pp in e.get("papers", []))
    srcs = [s for s in e.get("sources", []) if s != e.get("official_url")]
    sources = f'''<section id="sources"><h2>Papers &amp; sources</h2><div class="links">{papers}
  {f'<p style="margin:6px 0 0">Official site: <a href="{H(e["official_url"])}" target="_blank" rel="noopener">{H(re.sub(r"^https?://(www[.])?", "", e["official_url"]).rstrip("/"))}</a></p>' if e.get('official_url') else ''}
  {f'<details class="src"><summary>All sources ({len(srcs)})</summary><div class="links" style="margin-top:8px">' + "".join(f'<a href="{H(s)}" target="_blank" rel="noopener nofollow">{H(re.sub(r"^https?://(www[.])?", "", s).rstrip("/"))}</a>' for s in srcs) + '</div></details>' if srcs else ''}
  {'<p class="note">Fewer official sources were available for this exam, so some details come from news and coaching sites. Check the official site before you apply.</p>' if e.get('confidence') == 'low' else ''}
  <p class="note">Spotted something out of date? Write to <b>letsgoverbal@gmail.com</b> and we'll fix it.</p></div></section>'''
    # --- sidebar
    sim = [o for o in exams if o["category"] == e["category"] and o["id"] != e["id"]][:5]
    crit = "".join(f"<li><span>{H(k)}</span><b>{H(v)}</b></li>" for k, v in er)
    side = f'''<aside class="side">
  <div class="box gold"><h3>Track this exam</h3><div class="cd" data-cd="{e['id']}">{cd_fallback(e)}</div>
    <p style="margin:12px 0 16px;color:var(--ink2)" data-detail="{e['id']}">{H(detail_text(e))}</p>
    <button class="btn navy" type="button" data-star="{e['id']}">★ Save to my list</button><button class="btn" type="button" data-cmp="{e['id']}">+ Compare</button></div>
  {f'<div class="box"><h3>Do you qualify?</h3><ul class="crit">{crit}</ul><a class="btn" href="{x.u("tools/eligibility/")}">Check with your marks</a></div>' if crit else ''}
  {prep_box(e)}
  {'<div class="box"><h3>Similar exams</h3><ul class="mini">' + "".join(f'<li><a href="{x.ex(o["id"])}"><span class="mono sm {o["_cc"]}">{H(o["_mono"])}</span><span class="t"><b>{H(o["name"])}</b><small data-next="{o["id"]}">{H(next_text(o))}</small></span></a></li>' for o in sim) + '</ul></div>' if sim else ''}
</aside>'''
    body = hero + secnav + f'<div class="wrap layout"><div class="main">{overview}{dates}{elig}{pattern}{selection}{colsec}{faqs}{sources}</div>{side}</div>'
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in fq]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "UG Exam Atlas", "item": SITE + BASE},
            {"@type": "ListItem", "position": 2, "name": "Exams", "item": SITE + BASE + "all/"},
            {"@type": "ListItem", "position": 3, "name": e["name"], "item": SITE + BASE + e["id"] + "/"}]}]}
    title = f"{e['name']} {CYCLE}: Dates, Pattern, Eligibility, Colleges & Cutoffs | Camp Verbal"
    desc = f"{e['name']} for {', '.join(e['programme_types']) or 'UG'} admissions: {CYCLE} dates, exam pattern, who can apply, and {n} colleges that accept it, with cutoffs."
    return page(x, title, desc, f"{e['id']}/", body, exams, "exams", ld, ver=ver)

def page_colleges(x, exams, cols, ver):
    states = collections.Counter(C["state"] for C in cols.values() if C["state"])
    types = collections.Counter(C["bucket"] for C in cols.values())
    def cb(group, val, label, n, tok=None):
        return f'<label><input type="checkbox" data-f="{group}" value="{H(val)}" data-hash="{H(tok or slug(val))}"> {H(label)}<span class="n">{n}</span></label>'
    sopts = "".join(f'<option value="{H(s)}" data-hash="{slug(s)}">{H(s)} ({n})</option>' for s, n in sorted(states.items()))
    eopts = "".join(f'<option value="{e["id"]}" data-hash="{e["id"]}">{H(e["name"])}</option>' for e in sorted(exams, key=lambda e: e["name"].lower()) if any(e["id"] in C["exam_ids"] for C in cols.values()))
    progs = "".join(cb("prog", p, p, sum(p in C["tags"] for C in cols.values()), tok) for p, tok, _ in PROGS)
    tps = "".join(cb("type", t, t, n) for t, n in types.most_common() if t != "Other")
    cards = "".join(col_card(x, C) for C in sorted(cols.values(), key=lambda C: C["name"].lower()))
    body = f'''{crumbs(x, [("Exam Atlas", x.u()), ("Colleges", None)])}
<section class="tool-hero" style="padding-top:8px"><div class="wrap"><h1>Colleges</h1><p>{len(cols)} colleges for BBA, IPM, BMS, BCom, Economics, Finance and Liberal Arts. Open any college to see every exam that gets you in, with cutoffs.</p></div></section>
<section class="tool"><div class="wrap dir js-dir">
  <aside class="filters" aria-label="Filters">
    <div class="fhead"><h2>Filters</h2><button class="clear js-clear" type="button">Clear all</button></div>
    <label class="sr" for="fq">Search colleges</label><input id="fq" class="fsearch js-fq" type="search" placeholder="College name or city…">
    <fieldset class="fgroup"><legend>State</legend><label class="sr" for="fs-state">State</label><select id="fs-state" data-fs="state"><option value="">All states</option>{sopts}</select></fieldset>
    <fieldset class="fgroup"><legend>Accepts this exam</legend><label class="sr" for="fs-exam">Exam</label><select id="fs-exam" data-fs="exam"><option value="">Any exam</option>{eopts}</select></fieldset>
    <fieldset class="fgroup"><legend>Programme</legend>{progs}</fieldset>
    <fieldset class="fgroup"><legend>Type</legend>{tps}</fieldset>
    <button class="btn gold apply js-apply" type="button">Show results</button>
  </aside>
  <div style="min-width:0">
    <div class="results-head"><p class="count"><b class="js-count">{len(cols)}</b> colleges</p>
      <div class="results-tools"><button class="btn sm flt-btn" type="button">{ic("filter")} Filters <span class="js-fcount"></span></button>
      <label class="sr" for="sort">Sort</label><select id="sort" class="js-sort"><option value="name">Name A–Z</option><option value="exams">Most exams accepted</option></select></div></div>
    <div class="cgrid js-results">{cards}</div>
    <div class="empty js-empty" hidden>No college matches these filters. <button class="btn sm js-clear" type="button" style="margin-left:8px">Clear filters</button></div>
  </div>
</div></section>'''
    return page(x, f"UG Colleges for BBA, IPM, BCom, Economics & Liberal Arts: Exams Accepted & Cutoffs | Camp Verbal",
                f"{len(cols)} Indian colleges for BBA, IPM, BMS, BCom, Economics and Liberal Arts, with every entrance exam each accepts and cutoffs.",
                "colleges/", body, exams, "colleges", ver=ver)

def page_college(x, C, exams, cols, ver):
    loc = ", ".join(v for v in [C["city"], C["state"]] if v)
    nex = len(C["exam_ids"])
    seats = next((c.get("seats") for _, c in C["routes"] if c.get("seats") and c.get("seats") not in ("—", "Not published")), "")
    fees = next((c.get("fees") for _, c in C["routes"] if c.get("fees") and c.get("fees") not in ("—", "Not published")), "")
    hero = f'''{crumbs(x, [("Exam Atlas", x.u()), ("Colleges", x.u('colleges/')), (C['name'], None)])}
<section class="phero"><div class="wrap phero-in">
  <span class="mono lg {C['cc']}">{H(C['mono'])}</span>
  <div style="min-width:0"><h1>{H(C['name'])}</h1><p class="sub">{ic("pin", "")}{H(loc) if loc else ''}{' · ' + H(C['type']) if C.get('type') else ''}</p>
    <div class="tags">{"".join(f'<span class="tag gold">{H(t)}</span>' for t in C['tags'])}</div></div>
  <div class="acts"><button class="btn" type="button" data-copy>{ic("link")} Copy link</button>{f'<a class="btn gold" href="{H(C["url"])}" target="_blank" rel="noopener">Official site {ic("ext")}</a>' if C.get('url') else ''}</div>
</div>
<div class="wrap"><dl class="statgrid c4">
  <div class="hl"><dt>Exams accepted</dt><dd>{nex}</dd></div>
  <div><dt>Programmes</dt><dd>{len(C['programmes']) or '—'}</dd></div>
  <div><dt>Seats</dt><dd style="font-size:16px">{H(short(seats, 40) or '—')}</dd></div>
  <div><dt>Fees</dt><dd style="font-size:16px">{H(short(fees, 40) or '—')}</dd></div>
</dl></div></section>'''
    tabs = [("ways", "Ways to get in"), ("programmes", "Programmes"), ("nearby", "Nearby colleges"), ("faqs", "FAQs")]
    secnav = '<nav class="secnav" aria-label="On this page"><div class="wrap"><ul>' + "".join(f'<li><a href="#{k}">{t}</a></li>' for k, t in tabs) + '</ul></div></nav>'
    routes = []
    for e, c in C["routes"]:
        ct = c.get("cutoff") or {}
        stt = ct.get("status") or "not_published"
        val = ct.get("value") if ct.get("value") and ct.get("value") != "Not published" else "Not published"
        note = ct.get("note") if ct.get("note") and ct.get("note") != "Not published" else ""
        routes.append(f'''<article class="route">
  <div class="hd"><span class="mono sm {e['_cc']}">{H(e['_mono'])}</span><div><h3><a href="{x.ex(e['id'])}">{H(e['name'])}</a></h3><p class="by">{H(e.get('conducted_by') or '')}</p></div>{pill(e)}{star(e['id'], True)}</div>
  <dl>
    <div><dt>Programmes via this exam</dt><dd>{H('; '.join(c.get('programmes', [])) or '—')}</dd></div>
    <div><dt>Cutoff</dt><dd><span class="cut {H(stt)}">{H(stt.replace('_', ' '))}{' · ' + H(ct['year']) if ct.get('year') and stt != 'not_published' else ''}</span><br>{H(val)}{f'<br><small style="color:var(--faint)">{H(note)}</small>' if note else ''}</dd></div>
    <div><dt>Seats</dt><dd>{H(c.get('seats') or '—')}</dd></div>
    <div><dt>Fees</dt><dd>{H(c.get('fees') or '—')}</dd></div>
    {f'<div style="grid-column:1/-1"><dt>Selection</dt><dd>{H(c["selection"])}</dd></div>' if c.get('selection') else ''}
    {f'<div style="grid-column:1/-1"><dt>Placements</dt><dd>{H(c["placements"])}</dd></div>' if c.get('placements') else ''}
  </dl>
  <div class="ft"><span data-next="{e['id']}">{H(next_text(e))}</span><a class="more" href="{x.ex(e['id'])}">Exam details {ic("arrow")}</a></div>
</article>''')
    ways = f'<section id="ways"><h2>Ways to get in <small>{plural(nex, "exam")}</small></h2><div class="routes">{"".join(routes)}</div></section>'
    progs = f'<section id="programmes"><h2>Programmes</h2>' + ('<ul class="prose" style="padding-left:20px;display:flex;flex-direction:column;gap:6px">' + "".join(f"<li>{H(pp)}</li>" for pp in C["programmes"]) + '</ul>' if C["programmes"] else '<p class="prose">Not published.</p>') + '</section>'
    near = [o for o in cols.values() if o["slug"] != C["slug"] and C["state"] and o["state"] == C["state"]]
    near.sort(key=lambda o: (o["city"] != C["city"], -len(o["exam_ids"]), o["name"]))
    if not near:
        near = [o for o in cols.values() if o["slug"] != C["slug"] and set(o["exam_ids"]) & set(C["exam_ids"])][:6]
    nearsec = f'<section id="nearby"><h2>More colleges {("in " + H(C["state"])) if C["state"] and any(o["state"] == C["state"] for o in near) else "like this"}</h2><div class="cgrid">{"".join(col_card(x, o) for o in near[:6])}</div><p style="margin-top:14px"><a class="more" href="{x.u("colleges/")}{("#" + slug(C["state"])) if C["state"] else ""}">See all {("colleges in " + H(C["state"])) if C["state"] else "colleges"} {ic("arrow")}</a></p></section>' if near else ""
    names = [EXAMS_BY_ID[i]["name"] for i in C["exam_ids"]]
    fq = [(f"Which entrance exams does {C['name']} accept?", f"{C['name']} accepts {join_and(names)} for the programmes listed in this guide.")]
    cut_bits = [f"{e['name']}: {(c.get('cutoff') or {}).get('value')} ({(c.get('cutoff') or {}).get('status', '').replace('_', ' ')}, {(c.get('cutoff') or {}).get('year', '')})" for e, c in C["routes"] if (c.get("cutoff") or {}).get("value") and (c.get("cutoff") or {}).get("value") != "Not published"]
    fq.append((f"What is the cutoff for {C['name']}?", "; ".join(cut_bits) + "." if cut_bits else f"{C['name']} does not publish an official cutoff for these routes."))
    if C["programmes"]: fq.append((f"Which UG programmes does {C['name']} offer?", "; ".join(C["programmes"]) + "."))
    if loc: fq.append((f"Where is {C['name']}?", loc + "."))
    faqs = '<section id="faqs"><h2>Common questions</h2><div class="faq">' + "".join(f"<details><summary>{H(q)}</summary><p>{H(a)}</p></details>" for q, a in fq) + '</div></section>'
    side = f'''<aside class="side">
  <div class="box"><h3>Exams to take</h3><ul class="mini">{"".join(f'<li><a href="{x.ex(i)}"><span class="mono sm {EXAMS_BY_ID[i]["_cc"]}">{H(EXAMS_BY_ID[i]["_mono"])}</span><span class="t"><b>{H(EXAMS_BY_ID[i]["name"])}</b><small data-next="{i}">{H(next_text(EXAMS_BY_ID[i]))}</small></span></a></li>' for i in C["exam_ids"])}</ul></div>
  <div class="box gold"><h3>Do you qualify?</h3><p>Check your marks, stream and age against every exam in one go.</p><a class="btn navy" href="{x.u('tools/eligibility/')}">Am I eligible?</a></div>
</aside>'''
    body = hero + secnav + f'<div class="wrap layout"><div class="main">{ways}{progs}{nearsec}{faqs}</div>{side}</div>'
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollegeOrUniversity", "name": C["name"], **({"url": C["url"]} if C.get("url") else {}), **({"address": {"@type": "PostalAddress", "addressLocality": C["city"], "addressRegion": C["state"], "addressCountry": "IN"}} if loc else {})},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in fq]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "UG Exam Atlas", "item": SITE + BASE},
            {"@type": "ListItem", "position": 2, "name": "Colleges", "item": SITE + BASE + "colleges/"},
            {"@type": "ListItem", "position": 3, "name": C["name"], "item": SITE + BASE + f"colleges/{C['slug']}/"}]}]}
    title = f"{C['name']}{', ' + C['city'] if C['city'] and C['city'] not in C['name'] else ''}: Entrance Exams, Cutoffs & Admission {CYCLE} | Camp Verbal"
    desc = f"How to get into {C['name']}: {join_and(names)}. Programmes, seats, fees and cutoffs for {CYCLE} admission."
    return page(x, title, desc, f"colleges/{C['slug']}/", body, exams, "colleges", ld, ver=ver)

TOOL_META = {
    "eligibility": ("Am I eligible?", "Enter your Class X and XII marks, stream and date of birth. We check every exam's general-category rules and show which ones you can take, and why not for the rest.", "Am I Eligible? Check UG Entrance Exam Eligibility"),
    "calendar": ("Exam calendar", "Every application window and exam date for the next 12 months. Solid marks are announced dates; dashed marks are estimates from last year.", "UG Entrance Exam Calendar"),
    "compare": ("Compare exams", "Put up to three exams side by side: dates, pattern, English share, eligibility and selection.", "Compare UG Entrance Exams"),
    "english": ("How much of each exam is English?", "The share of each paper that tests verbal ability, reading comprehension, grammar and vocabulary.", "English Share of UG Entrance Exams"),
    "mylist": ("My list", "The exams you've saved, sorted by the next deadline. Your list stays on this device.", "My Exam List"),
}
def page_tool(x, key, exams, ver):
    h1, lede, t = TOOL_META[key]
    path = "my-list" if key == "mylist" else key
    body = f'''{crumbs(x, [("Exam Atlas", x.u()), ("Tools", None), (h1 if key != "english" else "English share", None)])}
<section class="tool-hero" style="padding-top:8px"><div class="wrap"><h1>{H(h1)}</h1><p>{H(lede)}</p></div></section>
<section class="tool"><div class="wrap"><div id="tool" data-tool="{key}"><p class="empty">Loading…</p></div></div></section>'''
    return page(x, f"{t} {CYCLE} | Camp Verbal", lede, f"tools/{path}/", body, exams, "list" if key == "mylist" else "", ver=ver)

# ---------------- data.js ----------------
def data_js(exams, cols, live):
    E = []
    for e in exams:
        p = e.get("pattern") or {}
        E.append({"id": e["id"], "name": e["name"], "full": e.get("full_name", ""), "by": e.get("conducted_by", ""), "cat": e["_tok"], "cc": e["_cc"], "mono": e["_mono"],
                  "progs": e["programme_types"], "nc": e.get("next_cycle") or {}, "elig": e.get("elig"), "months": e.get("months"),
                  "va": e.get("va_share"), "vtxt": e.get("verbal_weight", ""), "etxt": e.get("eligibility", ""), "sel": e.get("selection_process", ""),
                  "fee": (e.get("cycle_2026") or {}).get("fee", ""), "dur": p.get("duration_min"), "q": p.get("total_questions"),
                  "secs": [[s.get("name"), s.get("questions")] for s in p.get("sections") or []], "mark": p.get("marking", ""), "ncol": len(e["colleges"])})
    Cs = [{"s": C["slug"], "n": C["name"], "city": C["city"], "state": C["state"], "ex": C["exam_ids"], "progs": C["tags"], "mono": C["mono"], "cc": C["cc"]} for C in cols.values()]
    cfg = {"formspree": CFG.get("formspree", ""), "email": CFG.get("email", "letsgoverbal@gmail.com"), "live": live}
    blob = json.dumps({"updated": TODAY.isoformat(), "cfg": cfg, "exams": E, "colleges": Cs}, ensure_ascii=False, separators=(",", ":"))
    return "window.ATLAS=" + blob + ";\n"

# ---------------- build ----------------
def build(mode, out):
    exams, cols = prepare()
    EXAMS_BY_ID.clear(); EXAMS_BY_ID.update({e["id"]: e for e in exams})
    if os.path.exists(out): shutil.rmtree(out)
    os.makedirs(os.path.join(out, "assets"))
    css = open(os.path.join(HERE, "atlas.css")).read()
    js = open(os.path.join(HERE, "atlas.js")).read()
    dj = data_js(exams, cols, mode == "live")
    ver = hashlib.md5((css + js + dj).encode()).hexdigest()[:8]
    for n, c in (("atlas.css", css), ("atlas.js", js), ("data.js", dj)):
        open(os.path.join(out, "assets", n), "w").write(c)
    files = []
    def w(rel, depth, fn, *a, bare_ok=False):
        m = "bare" if (mode == "preview" and bare_ok) else mode
        x = Ctx(m, depth)
        if m == "bare": x.idx = "index.html"
        path = os.path.join(out, rel, "index.html")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(fn(x, *a))
        files.append(rel)
    w("", 0, page_home, exams, cols, ver, bare_ok=True)
    w("all", 1, page_all, exams, ver)
    for e in exams: w(e["id"], 1, page_exam, e, exams, cols, ver)
    w("colleges", 1, page_colleges, exams, cols, ver)
    for C in cols.values(): w(f"colleges/{C['slug']}", 2, page_college, C, exams, cols, ver)
    for k in TOOL_META: w("tools/" + ("my-list" if k == "mylist" else k), 2, page_tool, k, exams, ver)
    if mode == "live":
        urls = [SITE + BASE + (f + "/" if f else "") for f in files if not f.startswith("tools/my-list")]
        open(os.path.join(out, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{u}</loc><lastmod>{TODAY.isoformat()}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    return exams, cols, files

if __name__ == "__main__":
    ex, co, f1 = build("live", os.path.join(PROJ, "dist", "live", "exams"))
    _, _, f2 = build("preview", os.path.join(PROJ, "dist", "preview"))
    print(f"{len(ex)} exams, {len(co)} college pages, {len(f1)} pages (live), {len(f2)} pages (preview)")
