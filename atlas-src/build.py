"""Build the UG Exam Atlas.

  python3 build.py

Reads   data/{iim,liberal-arts,private,cuet,state-other}.json   (base research)
        data/extra-*.json                                         (new exams)
        data/patch-*.json                                         (field updates, extra colleges)
        months_override.json, va_override.json, config.json
Writes  dist/preview.html            single file, for previewing (data inlined)
        dist/site/exams/index.html   the app, for campverbal.com/exams/
        dist/site/exams/<id>/index.html   one static, Google-friendly page per exam
        dist/site/exams/sitemap.xml
        dist/data.json
"""
import json, re, glob, os, datetime, html, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, *p)
ORDER = ["IIM & integrated management", "Private university",
         "CUET & central universities", "State & other", "Liberal arts"]
BASE = ["iim", "liberal-arts", "private", "cuet", "state-other"]  # liberal-arts before private: its FLAME/ATLAS/AU entries win
DROP = {"state-other": {"iimk-bms-at", "iimb-ug-bsc", "iimb-bba-dbe"}}
BANNED_SOURCE = re.compile(r"imsindia", re.I)
PROG_MAP = [
    ("IPM", r"\bipm\b|integrated (programme|program|bba|mba)|five[- ]year"),
    ("BBA", r"\bbba\b|business admin"),
    ("BMS", r"\bbms\b|\bbbe\b|management stud|business econ"),
    ("BCom", r"b\.?\s?com\b|commerce"),
    ("Economics", r"econ"),
    ("Finance", r"financ|accounting|\bfia\b"),
    ("Liberal Arts", r"liberal|interdisciplin|humanit|social science"),
]
VERBAL_RE = re.compile(r"verbal|english|reading|\brc\b|language|grammar|vocab|comprehension|written|essay|critical", re.I)
CAT_FILE = {"iim": ORDER[0], "private": ORDER[1], "cuet": ORDER[2], "state-other": ORDER[3], "liberal-arts": ORDER[4]}


def load(p, default):
    return json.load(open(p)) if os.path.exists(p) else default


MONTHS_OVR = load(D("months_override.json"), {})
VA_OVR = load(D("va_override.json"), {})
CONFIG = load(D("config.json"), {"formspree": "", "siteUrl": "https://campverbal.com", "pageBase": "/exams/"})


def norm_progs(e):
    blob = " ".join(e.get("programme_types", []) + [p for c in e.get("colleges", []) for p in c.get("programmes", [])])
    got = {name for name, rx in PROG_MAP if re.search(rx, blob, re.I)}
    for p in e.get("programme_types", []):
        for name, _ in PROG_MAP:
            if p.lower() == name.lower():
                got.add(name)
    return [n for n, _ in PROG_MAP if n in got]


def va_share(e):
    if e["id"] in VA_OVR:
        return VA_OVR[e["id"]]
    secs = (e.get("pattern") or {}).get("sections") or []
    nums = [s for s in secs if isinstance(s.get("questions"), (int, float)) and s.get("questions")]
    tot = sum(s["questions"] for s in nums)
    if not tot or len(nums) != len(secs):
        return None
    va = sum(s["questions"] for s in nums if VERBAL_RE.search(s.get("name", "")))
    return round(va / tot, 3)


def merge_colleges(old, new):
    idx = {c.get("name", "").strip().lower(): i for i, c in enumerate(old)}
    out = list(old)
    for c in new:
        k = c.get("name", "").strip().lower()
        if k in idx:
            out[idx[k]] = c
        else:
            idx[k] = len(out); out.append(c)
    return out


def collect():
    exams, seen = [], {}
    for f in BASE:
        for e in load(D("data", f + ".json"), []):
            if e["id"] in DROP.get(f, ()) or e["id"] in seen:
                continue
            if e.get("category") not in ORDER:
                e["category"] = CAT_FILE[f]
            seen[e["id"]] = e; exams.append(e)
    for p in sorted(glob.glob(D("data", "extra-*.json"))):
        for e in load(p, []):
            if e["id"] in seen:
                print("extra duplicates existing id, merging:", e["id"]); seen[e["id"]].update(e); continue
            if e.get("category") not in ORDER:
                e["category"] = ORDER[3]
            seen[e["id"]] = e; exams.append(e)
    for p in sorted(glob.glob(D("data", "patch-*.json"))):
        for pt in load(p, []):
            e = seen.get(pt.get("id"))
            if not e:
                print("patch for unknown id", pt.get("id"), "in", os.path.basename(p)); continue
            for k, v in (pt.get("set") or {}).items():
                if k == "colleges":
                    e["colleges"] = v
                else:
                    e[k] = v
            for path, v in (pt.get("setp") or {}).items():  # dotted path, e.g. "pattern.notes" or "colleges[IIM Indore].fees"
                obj, parts = e, path.split(".")
                for part in parts[:-1]:
                    m = re.match(r"(\w+)\[(.+)\]$", part)
                    if m:
                        obj = next((c for c in obj.get(m.group(1), []) if c.get("name") == m.group(2)), None)
                    else:
                        obj = obj.setdefault(part, {})
                    if obj is None:
                        break
                if obj is None:
                    print("setp target not found:", pt.get("id"), path); continue
                obj[parts[-1]] = v
            if pt.get("add_colleges"):
                e["colleges"] = merge_colleges(e.get("colleges", []), pt["add_colleges"])
    # normalise
    for e in exams:
        e["sources"] = [s for s in e.get("sources", []) if not BANNED_SOURCE.search(s)]
        for c in e.get("colleges", []):
            for k in ("url",):
                if c.get(k) and BANNED_SOURCE.search(c[k]):
                    c[k] = ""
            ct = c.get("cutoff") or {}
            if ct.get("note") and BANNED_SOURCE.search(ct["note"]):
                ct["note"] = re.sub(r"(?i)\s*\(?[^;]*ims[^;]*\)?", "", ct["note"]).strip()
        e["papers"] = [p for p in e.get("papers", []) if p.get("url") and not BANNED_SOURCE.search(p["url"])]
        e["programme_types"] = norm_progs(e)
        mo = MONTHS_OVR.get(e["id"])
        e["months"] = {"apply": mo[0], "exam": mo[1]} if mo else None
        e["va_share"] = va_share(e)
        uniq, cs = [], set()
        for c in e.get("colleges", []):
            k = c.get("name", "").strip().lower()
            if k and k not in cs:
                cs.add(k); uniq.append(c)
        e["colleges"] = uniq
    exams.sort(key=lambda e: (ORDER.index(e["category"]), e["name"].lower()))
    return exams


# ---------------- static exam pages ----------------
H = lambda s: html.escape(str(s if s is not None else ""), quote=True)
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fdate(s):
    try:
        d = datetime.date.fromisoformat(s)
        return f"{d.day} {MON[d.month-1]} {d.year}"
    except Exception:
        return ""


FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,500;1,9..144,600&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@500;600&display=swap">'
BRAND_SVG = '<svg viewBox="0 0 20 22" aria-hidden="true"><path d="M1.5 1.5h17v8.7c0 5.6-4.3 9.8-8.5 10.6C5.8 20 1.5 15.8 1.5 10.2z" fill="var(--maroon-deep)" stroke="var(--gold)" stroke-width="1.4"/><path d="M5.6 14.6 10 6.4l4.4 8.2" fill="none" stroke="var(--gold)" stroke-width="1.6" stroke-linejoin="round"/></svg>'


def doc(title, desc, canonical, body, css, extra_head=""):
    return f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{H(title)}</title>
<meta name="description" content="{H(desc)}">
<link rel="canonical" href="{H(canonical)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Camp Verbal">
<meta property="og:title" content="{H(title)}"><meta property="og:description" content="{H(desc)}"><meta property="og:url" content="{H(canonical)}">
<meta property="og:image" content="https://www.campverbal.com/og-image.jpg"><meta name="twitter:card" content="summary_large_image">
<meta property="og:image" content="https://www.campverbal.com/og-image.jpg">
<meta name="theme-color" content="#0a1230">
<link rel="icon" href="/favicon.ico"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
{FONTS}
<style>{css}</style>
{extra_head}
</head>
<body>
{body}
</body>
</html>
"""


def exam_page(e, all_exams, css, cfg):
    base, site = cfg["pageBase"], cfg["siteUrl"].rstrip("/")
    url = f"{site}{base}{e['id']}/"
    nc = e.get("next_cycle") or {}
    cy = e.get("cycle_2026") or {}
    year = 2027
    title = f"{e['name']} {year}: Dates, Pattern, Eligibility, Colleges & Cutoffs | Camp Verbal"
    ncol = len(e.get("colleges", []))
    desc = f"{e['name']} ({e.get('full_name','')}) for {', '.join(e.get('programme_types', [])) or 'UG'} admissions: {year} dates, exam pattern, who can apply, and {ncol} colleges that accept it, with cutoffs."
    # cycle lines
    lines = []
    if nc.get("apply_open") or nc.get("apply_close"):
        lines.append(f"<p><b>Applications:</b> {fdate(nc.get('apply_open')) or 'open'} – {fdate(nc.get('apply_close')) or 'tbc'}</p>")
    exd = [fdate(x) for x in nc.get("exam_dates") or [] if fdate(x)]
    if exd:
        lines.append(f"<p><b>Exam:</b> {', '.join(exd)}</p>")
    if not lines and nc.get("expected"):
        lines.append(f"<p><b>Expected:</b> {H(nc['expected'])}</p>")
    if nc.get("source_status") == "estimated":
        lines.append('<p class="est">Estimated from last year\'s dates. Official dates are not out yet.</p>')
    elif nc.get("source_status") == "reported":
        lines.append('<p class="est">Dates from news reports of the official schedule.</p>')
    rounds = "".join(f'<span class="round">{H(r.get("label"))}: apply by {fdate(r.get("apply_close")) or "tbc"}{" · test " + fdate(r.get("exam_date")) if fdate(r.get("exam_date")) else ""}</span>' for r in nc.get("rounds") or [])
    cycle = f"""<div class="cycle"><div class="big" style="font-size:22px">{year}<small>Coming cycle</small></div>
      <div class="lines">{''.join(lines) or '<p>Dates not announced yet.</p>'}{f'<div class="rounds">{rounds}</div>' if rounds else ''}</div>
      {f'<a class="btn primary" href="{H(nc["url"])}" target="_blank" rel="noopener">Official page</a>' if nc.get("url") else ''}</div>"""
    # pattern
    p = e.get("pattern") or {}
    secs = p.get("sections") or []
    prow = "".join(f"<tr><td>{H(s.get('name'))}</td><td class='n'>{H(s.get('questions') if s.get('questions') is not None else '—')}</td><td class='n'>{H(s.get('time_min') if s.get('time_min') is not None else '—')}</td><td>{H(s.get('notes',''))}</td></tr>" for s in secs)
    meta = " · ".join(x for x in [f"{p['duration_min']} min" if p.get("duration_min") else "", f"{p['total_questions']} questions" if p.get("total_questions") else "", "sectional timing" if p.get("sectional_timing") else ""] if x)
    pattern = f"""<section><h2 class="h3">Exam pattern <small>{H(meta)}</small></h2>
      {f'<div class="tblwrap"><table><thead><tr><th>Section</th><th>Questions</th><th>Minutes</th><th>Notes</th></tr></thead><tbody>{prow}</tbody></table></div>' if prow else ''}
      {f'<p class="note" style="margin-top:12px"><b>Marking:</b> {H(p.get("marking"))} {H(p.get("notes",""))}</p>' if p.get("marking") else ''}</section>"""
    # colleges
    crow = []
    for c in sorted(e.get("colleges", []), key=lambda c: c.get("name", "")):
        ct = c.get("cutoff") or {}
        stt = ct.get("status") or "not_published"
        name = f'<a href="{H(c["url"])}" target="_blank" rel="noopener">{H(c["name"])}</a>' if c.get("url") else H(c.get("name"))
        val = ct.get("value") if ct.get("value") and ct.get("value") != "Not published" else ""
        note = ct.get("note") if ct.get("note") and ct.get("note") != "Not published" else ""
        crow.append(f"""<tr><td class="colname">{name}<small>{H(', '.join(x for x in [c.get('city'), c.get('state')] if x))}{' · ' + H(c['type']) if c.get('type') else ''}</small></td>
          <td data-l="Programmes">{H('; '.join(c.get('programmes', [])))}</td><td data-l="Seats" class="n">{H(c.get('seats') or '—')}</td><td data-l="Fees">{H(c.get('fees') or '—')}</td>
          <td data-l="Cutoff" class="cut"><span class="pill {H(stt)}">{H(stt.replace('_',' '))}{' · ' + H(ct['year']) if ct.get('year') else ''}</span><br>{H(val)}{f'<small>{H(note)}</small>' if note else ''}</td>
          <td data-l="Placements / notes">{H(c.get('placements') or '—')}</td></tr>""")
    colleges = f"""<section><h2 class="h3">Colleges that accept {H(e['name'])} <small>{ncol} listed</small></h2>
      <div class="tblwrap"><table class="cards-sm"><thead><tr><th>College</th><th>Programmes</th><th>Seats</th><th>Fees</th><th>Cutoff</th><th>Placements / notes</th></tr></thead><tbody>{''.join(crow)}</tbody></table></div></section>""" if crow else ""
    papers = "".join(f'<a class="paper" href="{H(x["url"])}" target="_blank" rel="noopener">📄 {H(x.get("label") or "Sample paper")}</a>' for x in e.get("papers", []))
    srcs = "".join(f'<a href="{H(s)}" target="_blank" rel="noopener nofollow">{H(re.sub(r"^https?://(www[.])?", "", s).rstrip("/"))}</a>' for s in e.get("sources", []) if s != e.get("official_url"))
    related = [x for x in all_exams if x["category"] == e["category"] and x["id"] != e["id"]][:8]
    rel = "".join(f'<a class="chip" href="{base}{x["id"]}/">{H(x["name"])}</a>' for x in related)
    vs = e.get("va_share")
    # FAQ (also as structured data)
    faqs = []
    when = ""
    if exd:
        when = f"The {year} exam is scheduled for {', '.join(exd)}."
    elif nc.get("expected"):
        when = f"Official {year} dates are not out yet. {nc['expected']}."
    if cy.get("exam_date"):
        when += f" Last year's exam was held on {cy['exam_date']}."
    if when.strip():
        faqs.append((f"When is {e['name']} {year}?", when.strip()))
    if e.get("eligibility"):
        faqs.append((f"Who can apply for {e['name']}?", e["eligibility"]))
    if meta or secs:
        faqs.append((f"What is the {e['name']} exam pattern?", (meta + ". " if meta else "") + "; ".join(f"{s.get('name')}" + (f" ({s['questions']} questions)" if s.get("questions") else "") for s in secs) + (f". Marking: {p['marking']}" if p.get("marking") else "")))
    if ncol:
        faqs.append((f"Which colleges accept {e['name']}?", ", ".join(c["name"] for c in e["colleges"][:25]) + (f", and {ncol-25} more." if ncol > 25 else ".")))
    if e.get("verbal_weight"):
        faqs.append((f"How much English is in {e['name']}?", e["verbal_weight"]))
    faq_html = "".join(f"<details><summary>{H(q)}</summary><p>{H(a)}</p></details>" for q, a in faqs)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Camp Verbal", "item": site + "/"},
            {"@type": "ListItem", "position": 2, "name": "UG Exam Atlas", "item": f"{site}{base}"},
            {"@type": "ListItem", "position": 3, "name": e["name"], "item": url}]}]}
    tags = "".join(f'<span class="tag gold">{H(t)}</span>' for t in e.get("programme_types", [])) + (f'<span class="tag">{H(e["level"])}</span>' if e.get("level") else "") + (f'<span class="tag">{H(e["mode"])}</span>' if e.get("mode") else "")
    body = f"""<div class="topbar"><div class="topbar-in"><a class="brand" href="/">{BRAND_SVG}<span>Camp Verbal</span></a>
  <nav class="tabs" aria-label="Sections"><a class="tab" href="{base}">All exams</a><a class="tab" href="{base}#eligible">Am I eligible?</a><a class="tab" href="{base}#calendar">Calendar</a><a class="tab" href="{base}#colleges">Colleges</a></nav></div></div>
<div class="wrap">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Camp Verbal</a><span>›</span><a href="{base}">UG Exam Atlas</a><span>›</span><span>{H(e['name'])}</span></nav>
  <article class="sheet">
    <header class="sheet-head">
      <div><h1 style="font-size:clamp(30px,5vw,48px);margin:0">{H(e['name'])} {year}</h1><p class="sub">{H(e.get('full_name'))}{' · ' + H(e['conducted_by']) if e.get('conducted_by') else ''}</p></div>
      <div class="tags">{tags}</div>
      <div class="actions"><a class="btn primary" href="{base}#{e['id']}">Open in the Atlas ★ Add to my list</a><a class="btn" href="{base}#eligible">Check my eligibility</a></div>
    </header>
    <div class="sheet-body">
      {cycle}
      <dl class="facts">
        <div class="fact"><dt>Last cycle: applications</dt><dd>{H(cy.get('application_window') or '—')}</dd></div>
        <div class="fact"><dt>Last cycle: exam</dt><dd>{H(cy.get('exam_date') or '—')}</dd></div>
        <div class="fact"><dt>Application fee</dt><dd>{H(cy.get('fee') or '—')}</dd></div>
        <div class="fact wide"><dt>Who can apply</dt><dd>{H(e.get('eligibility') or '—')}</dd></div>
      </dl>
      <div class="verbal"><p><b>English &amp; verbal{f" · {round(vs*100)}% of the paper" if vs else ""}:</b> {H(e.get('verbal_weight') or '—')}</p></div>
      {pattern}
      <section><h2 class="h3">How selection works</h2><p class="prose">{H(e.get('selection_process') or '—')}</p></section>
      {colleges}
      {f'<p class="note">{H(e["notes"])}</p>' if e.get("notes") else ''}
      <section><h2 class="h3">Common questions</h2><div class="faq">{faq_html}</div></section>
      <section><h2 class="h3">Links</h2><div class="links">{papers}{f'<span>Official: <a href="{H(e["official_url"])}" target="_blank" rel="noopener">{H(re.sub(r"^https?://(www[.])?", "", e["official_url"]).rstrip("/"))}</a></span>' if e.get('official_url') else ''}{f'<details class="more"><summary>Sources</summary><div class="links" style="margin-top:6px">{srcs}</div></details>' if srcs else ''}</div></section>
      {f'<section><h2 class="h3">Related exams</h2><div class="related">{rel}</div></section>' if rel else ''}
    </div>
  </article>
  <footer class="foot"><div><p>Part of the <a href="{base}">UG Exam Atlas</a>, a free guide to every entrance exam for BBA, IPM, BCom, Economics, Finance and Liberal Arts. Cutoffs are tagged official, unofficial or not published. Always confirm on the official link before you apply.</p><p>Spotted something out of date? Write to letsgoverbal@gmail.com.</p></div><p class="foot-meta">Last updated {H(datetime.date.today().strftime('%d %b %Y'))}</p></footer>
</div>"""
    page_css = css + "\n.h3{font:600 20px/1.2 var(--display);margin:0 0 12px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}.h3 small{font:500 12.5px var(--body);color:var(--muted)}.tab{text-decoration:none}"
    return doc(title, desc, url, body, page_css, f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')


def main():
    exams = collect()
    today = datetime.date.today()
    data = {"updated": today.strftime("%d %b %Y"), "exams": exams}
    os.makedirs(D("dist"), exist_ok=True)
    json.dump(data, open(D("dist", "data.json"), "w"), ensure_ascii=False, indent=1)

    css = open(D("app.css")).read()
    js = open(D("app.js")).read()
    tpl = open(D("template.html")).read().replace("/*__CSS__*/", css).replace("/*__JS__*/", js)
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    # 1) preview (artifact): in-page navigation only
    prev_cfg = dict(CONFIG, pageBase="", siteUrl="")
    open(D("dist", "preview.html"), "w").write(tpl.replace("/*__DATA__*/", blob).replace("/*__CONFIG__*/", json.dumps(prev_cfg)))

    # 2) site build
    site = D("dist", "site", "exams")
    if os.path.exists(D("dist", "site")):
        shutil.rmtree(D("dist", "site"))
    os.makedirs(site)
    app = tpl.replace("/*__DATA__*/", blob).replace("/*__CONFIG__*/", json.dumps(CONFIG))
    # app page needs a full document when served from Vercel
    m = re.match(r"\s*<title>(.*?)</title>", app)
    head_end = app.index("</style>") + len("</style>")
    head, body = app[:head_end], app[head_end:]
    head = head.replace("<title>UG Exam Atlas</title>", "")
    noscript = "<noscript><div class='wrap'><h2>All exams</h2><ul>" + "".join(f'<li><a href="{CONFIG["pageBase"]}{e["id"]}/">{H(e["name"])}</a></li>' for e in exams) + "</ul></div></noscript>"
    # crawlable links block (visually hidden) so search engines find every exam page
    crawl = "<nav class='sr' aria-label='All exam pages'>" + "".join(f'<a href="{CONFIG["pageBase"]}{e["id"]}/">{H(e["name"])} {today.year + 1}</a>' for e in exams) + "</nav>"
    full = f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>UG Exam Atlas {today.year + 1}: BBA, IPM, BCom, Economics & Liberal Arts Entrance Exams | Camp Verbal</title>
<link rel="canonical" href="{CONFIG['siteUrl'].rstrip('/')}{CONFIG['pageBase']}">
<meta property="og:title" content="UG Exam Atlas — every BBA, IPM, BCom, Economics & Liberal Arts entrance exam in India">
<meta property="og:description" content="What's open now, am I eligible, exam patterns, and every college each exam opens up. Free, by Camp Verbal.">
<meta property="og:image" content="https://www.campverbal.com/og-image.jpg">
<meta name="theme-color" content="#0a1230">
<link rel="icon" href="/favicon.ico"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}[hidden]{{display:none!important}}img{{max-width:100%}}</style>
{head}
</head>
<body>
{noscript}{crawl}{body}
</body>
</html>
"""
    open(os.path.join(site, "index.html"), "w").write(full)
    for e in exams:
        os.makedirs(os.path.join(site, e["id"]), exist_ok=True)
        open(os.path.join(site, e["id"], "index.html"), "w").write(exam_page(e, exams, css, CONFIG))
    s = CONFIG["siteUrl"].rstrip("/") + CONFIG["pageBase"]
    urls = [s] + [f"{s}{e['id']}/" for e in exams]
    open(os.path.join(site, "sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{u}</loc><lastmod>{today.isoformat()}</lastmod></url>\n" for u in urls) + "</urlset>\n")

    ncol = len({c["name"].strip().lower() for e in exams for c in e["colleges"]})
    print(f"{len(exams)} exams, {ncol} unique colleges, {len(exams)} exam pages")


if __name__ == "__main__":
    main()
