# UG Exam Explorer — data schema

Scope: Indian undergraduate admissions for BBA / BMS / IPM (integrated management), BCom, BSc/BA Economics, BSc Finance / Finance & Accounts, and Liberal Arts (BA/BSc liberal arts, interdisciplinary). NOT engineering, medicine, law, design, hotel management.

Latest completed cycle = 2026 admissions (exams held in 2026). If 2027 dates/notification are already announced, record them too.

Write ONE JSON file: an array of exam objects.

```json
[
  {
    "id": "ipmat-indore",                     // kebab-case, unique
    "name": "IPMAT Indore",                    // short display name
    "full_name": "Integrated Programme in Management Aptitude Test",
    "conducted_by": "IIM Indore",
    "category": "IIM & integrated management | Private university | CUET & central universities | State & other | Liberal arts",
    "programme_types": ["IPM", "BBA", "BCom", "Economics", "Finance", "Liberal Arts"],
    "mode": "Computer-based, centre",
    "level": "National",                       // National / State / University-specific
    "cycle_2026": {
      "application_window": "Feb–Mar 2026",
      "exam_date": "May 2026",
      "result": "...",
      "fee": "₹4,130 (Gen); ₹2,065 (SC/ST/PwD)"
    },
    "cycle_2027": "Announced: ... | Not announced yet (expected Feb 2027)",
    "eligibility": "Class XII passed/appearing; 60% in X and XII (55% SC/ST/PwD); age ≤ 20",
    "pattern": {
      "duration_min": 120,
      "total_questions": 100,
      "sections": [
        {"name": "Quantitative Ability (MCQ)", "questions": 30, "time_min": 40, "notes": ""},
        {"name": "Verbal Ability", "questions": 45, "time_min": 40, "notes": ""}
      ],
      "marking": "+4 / −1; short-answer: no negative",
      "sectional_timing": true,
      "notes": ""
    },
    "selection_process": "Test → PI (and WAT) → final score: aptitude 65% + PI 35% ...",
    "verbal_weight": "45 of 100 questions are Verbal Ability",   // one line: how much English/VA/RC the test has; 'None' if none
    "official_url": "https://...",
    "colleges": [
      {
        "name": "IIM Indore",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "type": "IIM | Central univ | State univ | Private univ | Deemed univ | Autonomous college | Govt college",
        "programmes": ["IPM (5-yr: BA Foundations of Management + MBA)"],
        "seats": "~150",
        "fees": "~₹4.6 L/yr for years 1–3 (approx.)",
        "cutoff": {
          "value": "Overall 2026 shortlist cutoff ... (Gen)",
          "year": 2026,
          "status": "official | unofficial | not_published",
          "note": "Source: IIM Indore admissions page / coaching estimates"
        },
        "selection": "Short note if different from exam-level process, else empty",
        "placements": "Avg ... (year) — only if published, else empty",
        "url": "https://..."
      }
    ],
    "sources": ["https://...", "https://..."],
    "notes": "Anything important a student should know (e.g. also accepts SAT; new in 2026)",
    "confidence": "high | medium | low"
  }
]
```

Rules:
- Use official sources first (institute sites, information bulletins, NTA). Use coaching/news sites only when nothing official exists, and mark cutoffs `"unofficial"` with the site name in `note`.
- Never invent numbers. If unknown, write "Not published" / empty string, and status `not_published`.
- Cutoff `value` must say what it is (shortlist cutoff, final merit rank, percentile, closing CUET score, etc.) and the category (General unless stated).
- Keep strings short and plain. Indian rupee formatting (₹, L for lakh).
- Valid JSON only (no comments) in the output file.

---
## v2 additions (Oct 2026)

Every exam object may also carry these fields (new exams MUST include them):

```json
"next_cycle": {                      // admission 2027 (the cycle running NOW, Oct 2026 onward)
  "status": "open | upcoming | closed | not_announced",   // as of 21 Oct 2026
  "apply_open": "2026-10-07",          // ISO date or null
  "apply_close": "2026-11-23",         // ISO date or null (final round's close if multi-round)
  "rounds": [                          // optional, for multi-round tests
    {"label": "Round 1", "apply_close": "2026-11-23", "exam_date": "2026-12-06"}
  ],
  "exam_dates": ["2026-12-06"],        // ISO dates; [] if unknown
  "expected": "Applications usually open early Feb; exam early May",  // plain line when dates not announced (based on past cycles)
  "url": "https://...",                // official admissions / bulletin page
  "source_status": "official | reported | estimated"
},
"elig": {
  "min_12_pct": 60,                    // General category minimum aggregate in Class XII; null if none
  "min_10_pct": 60,                    // null if none
  "streams": ["Any"],                  // or subset of ["Commerce","Science","Arts"]
  "maths_required": false,             // true if Maths in XII (or X) is mandatory; null if unclear
  "max_age": 20,                       // general category upper age limit in years, null if none
  "age_note": "born on/after 1 Aug 2006",
  "note": "Relaxed for SC/ST/PwD"
},
"papers": [ {"label": "Official sample paper", "url": "https://..."} ]   // official previous-year / sample / mock links only
```

Patch files (`data/patch-*.json`) are arrays of:
```json
{"id": "existing-exam-id", "set": { "field": "value" }, "add_colleges": [ /* college objects */ ], "remove_sources_matching": "imsindia"}
```
`set` replaces whole top-level fields. `add_colleges` adds colleges (same name replaces the old one).

Do NOT use imsindia.com (IMS) as a source anywhere.
