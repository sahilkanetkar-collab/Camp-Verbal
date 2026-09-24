# Camp Verbal test platform — setup guide

This adds a student test app at **campverbal.com/app**. It sits alongside the main site and is set up once, in about 30 minutes.

**What's here**

| Folder | What it is | Goes live on the website? |
|---|---|---|
| `app/` | The student and admin pages (login, library, test player, results, admin) | Yes |
| `supabase/schema.sql` | The whole database: tables, security rules, marking, timers | No (you run it once in Supabase) |
| `supabase/demo/` | Three demo tests with original questions, one per timing mode | No |
| `dev/` | Automated tests (68 database checks, 39 browser checks) | No |
| `vercel.json`, `.vercelignore` | Hosting settings; keep `dev/` and `supabase/` off the public site | Settings only |

---

## 1. Create the Supabase project

1. Sign up or log in at **supabase.com** → **New project**.
2. Name: `camp-verbal`. Region: **Mumbai (ap-south-1)**, the closest to your students.
3. Set a strong database password and keep it somewhere safe. The app doesn't need it, but you will if you ever move the data.
4. Wait for the project to finish setting up (a couple of minutes).

## 2. Create the database

1. In Supabase, open **SQL Editor** → **New query**.
2. Open `supabase/schema.sql`, copy everything, paste it in, then click **Run**.
3. You should see *"Success. No rows returned."* Running it again later is safe; nothing gets deleted.

## 3. Email login (done for campverbal.com, 24 Sep 2026)

Students log in without a password: they enter their email and get a message with a **Log In link**.

- **Authentication → URL Configuration:** Site URL is `https://www.campverbal.com/app/login.html`, and the redirect URLs `https://www.campverbal.com/app/**` and `https://campverbal.com/app/**` are allowed. The link returns students to the app already logged in.
- **Email OTP Length** on this project is **8**, and `otpLength` in `config.js` is set to match.
- Supabase locks the email wording until you connect your own email sender. Until then students get Supabase's default email with just a link, and the app handles that. Once you add a sender (**Authentication → Emails → SMTP Settings**; Resend, Brevo and Zoho have free tiers), edit the *Magic Link* and *Confirm signup* templates to include the code as well:

```html
<h2>Log in to Camp Verbal</h2>
<p><a href="{{ .ConfirmationURL }}">Tap here to log in</a></p>
<p>Or enter this code: <b style="font-size:22px;letter-spacing:4px">{{ .Token }}</b></p>
```

> **Before real students:** the built-in sender only allows a handful of emails per hour and is meant for testing. Set up your own sender before a cohort starts.

## 4. Connect the app to the database

1. In Supabase: **Project Settings → API** (on newer projects it may be **API Keys**).
2. Copy the **Project URL** and the **publishable** key (older projects call it *anon*). *Never* use the `service_role` or secret key.
3. Paste both into `app/assets/config.js`.

The anon key is meant to be public. Security comes from the database rules, not from hiding the key.

## 5. Put it on the website

Upload `app/`, `vercel.json` and `.vercelignore` to the Camp-Verbal repo on GitHub. Vercel deploys by itself. `supabase/`, `dev/` and this guide can also go in the repo; `.vercelignore` keeps them off the website.

## 6. Make yourself admin

1. Go to **campverbal.com/app**, log in with your email, and fill in your name.
2. In Supabase **SQL Editor**, run (with your email):

```sql
update public.profiles set is_admin = true where email = 'you@example.com';
```

3. Reload the app. An **Admin** button appears in the header.

## 7. Try it with the demo tests

1. **Admin → Series** → create a series (e.g. "Demo"), tick *Visible to students*.
2. **Admin → Import a test** → paste `supabase/demo/demo_sprint_01.json` → **Check** → choose the series, *Free*, tick *Publish now* → **Import**.
3. Repeat with the other two demo files.
4. Open the library and take each test once, including on your phone.
5. When you're done, set the demo tests to **Draft** (Admin → Tests → Edit → untick Published). They can't be deleted once taken, which is deliberate.

---

## Day-to-day use

**Adding a test.** Make it exactly as you do now (Item Factory → Studio envelope), then paste the envelope into **Admin → Import a test**. The same Gate 1 rules run: `verified: "ok"`, `status: "approved"`, four options, answer matches `answerIndex`, section counts, and `td` 10–300 s for sprints. Timing is worked out the way Studio does it:

| Envelope says | Students get |
|---|---|
| `meta.timerMode: "perQuestion"` | **Sprint**: a clock per question (`td`), forward only |
| `meta.timerMinutes: 30` | **Single clock**: 30 min, free navigation |
| Locked exam (Indore, IIMK), no `timerMinutes`, 2+ sections | **Locked sections**: fixed order, no going back; `meta.sectionTimers` sets per-section minutes |
| Otherwise | The exam's official timing (proportional for a sectional drill) |

Marking follows the exam table (Indore +4/−1, TITA wrong 0; UGAT +3/−1; …). For VA parajumbles at −1, add `"titaW": -1` to the envelope's `meta`.

**Giving access.** Free tests are open to anyone logged in. For paid ones: **Admin → Access**, enter the student's email (they must have logged in once), and choose *Everything*, *one series* or *one test*, with an optional end date. Revoke any time; past results stay.

**Timed drops.** Set *Opens* and *Closes* on a test. The server enforces the window, not just the homepage.

**Changing a test after students have taken it.** Not allowed, so scores stay fair. Import a corrected version under a new address, then set the old one to Draft.

---

## How it stays secure

- Questions go to the browser only after a student with access starts the test. Answer keys and explanations stay in the database until they submit.
- Marking happens on the server. Clocks are checked on the server, with a 30-second allowance for slow connections.
- Locked sections: later sections aren't sent until they open, and finished sections can't be changed.
- Students can't read each other's attempts, see the questions table, or make themselves admin. Every one of these is covered by the automated tests.
- The first attempt is flagged, and it's the score shown in the library.

## Things to know

- **Keep paid test files out of the public repo.** The Camp-Verbal repo is public. Paste envelopes into Admin; don't commit them.
- **Free Supabase projects pause after about a week without use.** Once students are active this doesn't matter. Before launch, open the app now and then, or restore it from the Supabase dashboard if it pauses.
- **Backups:** the free plan's backup options are limited. Check what your plan includes, and before a big cohort consider the Pro plan or regular exports (Supabase → Database → Backups).

## Not built yet (next steps)

Razorpay payments (the access table already has a `source` field for them), leaderboards (first-attempt data is already recorded), a student progress page, and a link from the main site's navigation.

## Running the tests (for future changes)

```bash
cd dev && npm install
npm run test:db    # 68 database checks on a local Postgres
npm run test:e2e   # 39 browser checks: login, all three timing modes, admin, security
```
