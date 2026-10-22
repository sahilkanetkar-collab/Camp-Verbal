# UG Exam Atlas: how it is built and updated

The Atlas lives at campverbal.com/exams. Everything needed to rebuild it is in the
Camp-Verbal repo under `atlas-src/` (Vercel ignores that folder; only `exams/` is served).

## Folder map
- `atlas-src/data/*.json`  research data. Base files (iim, private, cuet, state-other,
  liberal-arts), `extra-*.json` for new exams, `patch-*.json` for corrections.
  Patches apply in alphabetical order, so a later patch wins.
- `atlas-src/SCHEMA.md`  what every field means. Read this before editing data.
- `atlas-src/config.json`  Formspree ID, site URL, contact email.
- `atlas-src/site/`  page templates (build_site.py), styles (atlas.css), behaviour (atlas.js).
- `atlas-src/build.py`  merges the data; `months_override.json` and `va_override.json`
  are hand-set calendar months and English-share figures.

## To change a fact
Add an object to a new or existing `data/patch-*.json` file:
```json
{"id": "ipmat-indore", "setp": {"next_cycle.apply_close": "2027-03-15", "cycle_2026.fee": "₹4,130"}}
```
`setp` keys are dotted paths. Use `colleges[Exact College Name].fees` to change one college.
A new exam goes in `data/extra-*.json` as a full object (see SCHEMA.md).

## To rebuild and publish
```
cd atlas-src
python3 site/build_site.py
rm -rf ../exams && cp -r dist/live/exams ../exams
git add -A && git commit -m "Update Exam Atlas" && git push
```
Vercel deploys in about a minute. Commits must come from your own GitHub account, or
Vercel will not deploy them.

The simplest route is still to open a Claude session, say what changed, and ask it to
patch, rebuild and push.

## Switch on deadline alerts
Create a form at formspree.io, paste its ID into `config.json` ("formspree"), rebuild, push.
Until then the form opens the student's email app with a ready-made message.

## When to refresh
- Early January: CUET, IPMAT Indore, IPMAT Rohtak, NPAT, SET and MAH CET usually announce.
- March to April: JIPMAT, IIMK, AIMA UGAT, IPU CET.
- August to October: IIMB UG test, Ashoka, FLAME, Krea, Christ, Azim Premji open for the next year.
