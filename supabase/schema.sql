-- ═══════════════════════════════════════════════════════════════════════════
--  CAMP VERBAL — test platform database  (v1.0)
--
--  Run this whole file once in Supabase → SQL Editor → New query → Run.
--  It is safe to re-run: every object is created with IF NOT EXISTS or
--  CREATE OR REPLACE, and nothing here deletes data.
--
--  Security model, in one paragraph:
--    Students never read the question or attempt tables directly. Every
--    student action goes through a server function (start, save, submit,
--    review). Those functions check who the student is, whether they have
--    access, and whether the clock allows it. Answer keys and explanations
--    only leave the database after an attempt is submitted. Marking happens
--    here, on the server — the browser never knows the key while testing.
-- ═══════════════════════════════════════════════════════════════════════════

-- ───────────────────────────────────────────────────────────────────────────
-- 1. TABLES
-- ───────────────────────────────────────────────────────────────────────────

create table if not exists public.profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  email        text,
  full_name    text,
  phone        text,
  target_exam  text,
  is_admin     boolean not null default false,
  created_at   timestamptz not null default now()
);

create table if not exists public.series (
  id          uuid primary key default gen_random_uuid(),
  slug        text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{1,60}$'),
  title       text not null,
  blurb       text,
  kind        text not null default 'drill'
              check (kind in ('rapid','ladder','mock','challenge','drill','other')),
  sort        int  not null default 100,
  published   boolean not null default false,
  created_at  timestamptz not null default now()
);

create table if not exists public.tests (
  id              uuid primary key default gen_random_uuid(),
  slug            text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{1,80}$'),
  series_id       uuid references public.series(id) on delete set null,
  title           text not null,
  exam_key        text not null,
  exam_name       text not null,
  test_type       text not null check (test_type in ('full','sectional')),
  timing          text not null check (timing in ('single','locked','rapid')),
  minutes         int  not null check (minutes > 0),
  section_order   text[] not null,
  section_minutes jsonb,                      -- locked only: {"QA-SA":40,...}
  marking         jsonb not null,             -- {"c":4,"w":-1,"titaW":0}
  max_marks       int  not null,
  question_count  int  not null,
  access          text not null default 'paid' check (access in ('free','paid')),
  published       boolean not null default false,
  opens_at        timestamptz,
  closes_at       timestamptz,
  max_attempts    int check (max_attempts is null or max_attempts > 0),
  sort            int not null default 100,
  source_meta     jsonb,                      -- the envelope's meta, kept for audit
  created_at      timestamptz not null default now()
);
create index if not exists tests_series_idx on public.tests(series_id);

create table if not exists public.questions (
  id            uuid primary key default gen_random_uuid(),
  test_id       uuid not null references public.tests(id) on delete cascade,
  qid           text not null,               -- the envelope's own id, e.g. VA-07
  position      int  not null,               -- 0-based delivery order
  section       text not null,
  format        text,
  kind          text not null check (kind in ('mcq','tita')),
  passage       text,
  stem          text not null,
  options       jsonb,                       -- ["a","b","c","d"] or null for TITA
  fig           text,                        -- inline <svg> markup
  table_html    text,                        -- <table> markup
  td            int,                         -- rapid mode seconds
  difficulty    text,
  tags          jsonb,
  -- the secret part — never returned before submission:
  answer_index  int,
  answer_text   text,
  explanation   text,
  unique (test_id, qid),
  unique (test_id, position)
);
create index if not exists questions_test_idx on public.questions(test_id, position);

create table if not exists public.entitlements (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  scope       text not null check (scope in ('all','series','test')),
  ref_id      uuid,                           -- series.id or tests.id; null for 'all'
  source      text not null default 'manual', -- 'manual' now, 'razorpay' later
  note        text,
  granted_by  uuid references auth.users(id),
  expires_at  timestamptz,
  revoked_at  timestamptz,
  created_at  timestamptz not null default now(),
  check ((scope = 'all' and ref_id is null) or (scope <> 'all' and ref_id is not null))
);
create index if not exists entitlements_user_idx on public.entitlements(user_id);

create table if not exists public.attempts (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  test_id         uuid not null references public.tests(id) on delete cascade,
  attempt_no      int  not null,
  is_first        boolean not null,
  status          text not null default 'in_progress'
                  check (status in ('in_progress','submitted')),
  started_at      timestamptz not null default now(),
  deadline_at     timestamptz not null,
  state           jsonb not null default '{}'::jsonb,  -- locked: {idx, starts[]}; rapid: {pos}
  submitted_at    timestamptz,
  auto_submitted  boolean not null default false,
  score           numeric,
  correct         int,
  wrong           int,
  skipped         int,
  max_marks       int,
  time_taken_sec  int,
  breakdown       jsonb,                                -- per section / per format
  unique (user_id, test_id, attempt_no)
);
create index if not exists attempts_user_idx on public.attempts(user_id, test_id);
create unique index if not exists attempts_one_open
  on public.attempts(user_id, test_id) where status = 'in_progress';

create table if not exists public.responses (
  attempt_id     uuid not null references public.attempts(id) on delete cascade,
  question_id    uuid not null references public.questions(id) on delete cascade,
  answer         text,          -- MCQ: "0".."3"; TITA: what they typed; null = no answer
  time_ms        int not null default 0,
  marked         boolean not null default false,
  updated_at     timestamptz not null default now(),
  primary key (attempt_id, question_id)
);

-- ───────────────────────────────────────────────────────────────────────────
-- 2. ROW-LEVEL SECURITY
--    Everything is locked by default. Only the few reads below are allowed
--    directly; everything else goes through the functions in section 4.
-- ───────────────────────────────────────────────────────────────────────────

alter table public.profiles     enable row level security;
alter table public.series       enable row level security;
alter table public.tests        enable row level security;
alter table public.questions    enable row level security;
alter table public.entitlements enable row level security;
alter table public.attempts     enable row level security;
alter table public.responses    enable row level security;

drop policy if exists profiles_self_read on public.profiles;
create policy profiles_self_read on public.profiles
  for select to authenticated using (id = auth.uid());
drop policy if exists profiles_self_update on public.profiles;
create policy profiles_self_update on public.profiles
  for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists series_public_read on public.series;
create policy series_public_read on public.series
  for select to anon, authenticated using (published);

drop policy if exists tests_public_read on public.tests;
create policy tests_public_read on public.tests
  for select to anon, authenticated using (published);

drop policy if exists entitlements_self_read on public.entitlements;
create policy entitlements_self_read on public.entitlements
  for select to authenticated using (user_id = auth.uid());

drop policy if exists attempts_self_read on public.attempts;
create policy attempts_self_read on public.attempts
  for select to authenticated using (user_id = auth.uid());

-- questions and responses: no policies at all → no direct access.

-- Column-level: a student may edit their own name/phone/exam, never is_admin.
revoke all on public.profiles from anon, authenticated;
grant select on public.profiles to authenticated;
grant update (full_name, phone, target_exam) on public.profiles to authenticated;

revoke all on public.questions, public.responses from anon, authenticated;
revoke insert, update, delete on public.series, public.tests, public.entitlements, public.attempts
  from anon, authenticated;
grant select on public.series, public.tests to anon, authenticated;
grant select on public.entitlements, public.attempts to authenticated;

-- ───────────────────────────────────────────────────────────────────────────
-- 3. HELPERS
-- ───────────────────────────────────────────────────────────────────────────

-- New sign-ups get a profile row automatically.
create or replace function public.cv_handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email) values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists cv_on_auth_user_created on auth.users;
create trigger cv_on_auth_user_created
  after insert on auth.users for each row execute function public.cv_handle_new_user();

-- Exam rules — mirrors Test Builder Studio's EXAM_CONFIG exactly.
create or replace function public.cv_exam_config(p_code text)
returns jsonb language plpgsql immutable as $$
declare k text := upper(regexp_replace(coalesce(p_code,''), '[\s-]+', '_', 'g'));
begin
  k := case k
    when 'UGAT' then 'UGAT_IIMB' when 'UGAT_IIM_BANGALORE' then 'UGAT_IIMB' when 'IIMB_UG' then 'UGAT_IIMB'
    when 'INDORE' then 'IPMAT_INDORE' when 'IPMAT' then 'IPMAT_INDORE'
    when 'IIMK' then 'IIMK_BMS' when 'IIMK_BMS_AT' then 'IIMK_BMS'
    when 'ROHTAK' then 'IPMAT_ROHTAK' when 'JIPMAT_NTA' then 'JIPMAT'
    else k end;
  return case k
    when 'UGAT_IIMB' then '{"key":"UGAT_IIMB","name":"UGAT IIM Bangalore","marking":{"c":3,"w":-1},"duration":120,"timing":"single","sections":{"QADI":30,"LR":15,"VA":15},"order":["QADI","LR","VA"]}'::jsonb
    when 'IPMAT_INDORE' then '{"key":"IPMAT_INDORE","name":"IPMAT Indore","marking":{"c":4,"w":-1,"titaW":0},"duration":120,"timing":"locked","secMinutes":40,"sections":{"QA-SA":15,"QA-MCQ":30,"VA":45},"order":["QA-SA","QA-MCQ","VA"]}'::jsonb
    when 'JIPMAT' then '{"key":"JIPMAT","name":"JIPMAT (NTA)","marking":{"c":4,"w":-1},"duration":150,"timing":"single","sections":{"QA":33,"LR":33,"VA":34},"order":["QA","LR","VA"]}'::jsonb
    when 'IIMK_BMS' then '{"key":"IIMK_BMS","name":"IIMK BMS AT","marking":{"c":3,"w":-1},"duration":120,"timing":"locked","secMinutes":60,"sections":{"VA":50,"QA":50},"order":["VA","QA"]}'::jsonb
    when 'IPMAT_ROHTAK' then '{"key":"IPMAT_ROHTAK","name":"IPMAT Rohtak","marking":{"c":4,"w":-1},"duration":120,"timing":"single","sections":{"QA":40,"VA":40,"LR":40},"order":["QA","VA","LR"]}'::jsonb
    else null end;
end $$;

create or replace function public.cv_is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce((select is_admin from public.profiles where id = auth.uid()), false);
$$;

create or replace function public.cv_require_user()
returns uuid language plpgsql stable as $$
declare u uuid := auth.uid();
begin
  if u is null then raise exception 'Please log in first.' using errcode = '28000'; end if;
  return u;
end $$;

create or replace function public.cv_require_admin()
returns uuid language plpgsql stable security definer set search_path = public as $$
declare u uuid := public.cv_require_user();
begin
  if not public.cv_is_admin() then raise exception 'Admins only.' using errcode = '42501'; end if;
  return u;
end $$;

create or replace function public.cv_has_access(p_user uuid, p_test uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = p_user and is_admin)
      or exists (select 1 from public.tests t where t.id = p_test and t.access = 'free')
      or exists (
        select 1 from public.entitlements e
        join public.tests t on t.id = p_test
        where e.user_id = p_user and e.revoked_at is null
          and (e.expires_at is null or e.expires_at > now())
          and (e.scope = 'all'
               or (e.scope = 'series' and e.ref_id = t.series_id)
               or (e.scope = 'test' and e.ref_id = t.id)));
$$;

-- TITA equivalence (same rule as Studio): trim; if, after removing spaces and
-- commas, it is a number → compare as numbers ("02" = "2", "1,000" = "1000");
-- otherwise compare case-insensitively.
create or replace function public.cv_tita_norm(v text)
returns text language plpgsql immutable as $$
declare s text := btrim(coalesce(v,''));
        t text := regexp_replace(s, '[\s,]', '', 'g');
begin
  if t ~ '^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$' then
    return trim_scale(t::numeric)::text;
  end if;
  return lower(s);
end $$;

-- The public shape of a question — never includes the key.
create or replace function public.cv_q_public(q public.questions)
returns jsonb language sql immutable as $$
  select jsonb_build_object(
    'id', q.id, 'qid', q.qid, 'position', q.position, 'section', q.section,
    'format', q.format, 'kind', q.kind, 'passage', q.passage, 'stem', q.stem,
    'options', q.options, 'fig', q.fig, 'table', q.table_html, 'td', q.td);
$$;

-- Locked-section clock: works out which section should be running *now*,
-- moving past any whose time ran out while the student was away.
create or replace function public.cv_sync_locked(p_attempt uuid)
returns public.attempts language plpgsql security definer set search_path = public as $$
declare a public.attempts; t public.tests; idx int; starts jsonb; sec_end timestamptz; n int;
begin
  select * into a from public.attempts where id = p_attempt for update;
  select * into t from public.tests where id = a.test_id;
  if t.timing <> 'locked' or a.status <> 'in_progress' then return a; end if;
  idx := (a.state->>'idx')::int; starts := a.state->'starts'; n := array_length(t.section_order, 1);
  loop
    sec_end := (starts->>idx)::timestamptz
               + make_interval(mins => (t.section_minutes->>t.section_order[idx+1])::int);
    exit when now() <= sec_end or idx >= n - 1;
    idx := idx + 1;
    starts := starts || to_jsonb(sec_end);          -- next section began when the last one ran out
  end loop;
  if idx <> (a.state->>'idx')::int then
    update public.attempts set state = jsonb_build_object('idx', idx, 'starts', starts)
      where id = a.id returning * into a;
  end if;
  return a;
end $$;

-- Marks an attempt. Idempotent: calling it on a submitted attempt returns it.
create or replace function public.cv_finalize(p_attempt uuid, p_auto boolean default false)
returns public.attempts language plpgsql security definer set search_path = public as $$
declare a public.attempts; t public.tests;
        c numeric; w numeric; tw numeric;
        v_score numeric := 0; v_cor int := 0; v_wr int := 0; v_sk int := 0;
        by_sec jsonb := '{}'::jsonb; by_fmt jsonb := '{}'::jsonb;
        r record; outcome text; pts numeric; k text;
begin
  select * into a from public.attempts where id = p_attempt for update;
  if a.status = 'submitted' then return a; end if;
  select * into t from public.tests where id = a.test_id;
  c  := (t.marking->>'c')::numeric;
  w  := (t.marking->>'w')::numeric;
  tw := coalesce((t.marking->>'titaW')::numeric, w);

  for r in
    select q.*, resp.answer from public.questions q
    left join public.responses resp on resp.question_id = q.id and resp.attempt_id = a.id
    where q.test_id = t.id order by q.position
  loop
    if r.answer is null or btrim(r.answer) = '' then
      outcome := 'skipped'; pts := 0; v_sk := v_sk + 1;
    elsif (r.kind = 'mcq' and r.answer ~ '^\d+$' and r.answer::int = r.answer_index)
       or (r.kind = 'tita' and public.cv_tita_norm(r.answer) = public.cv_tita_norm(r.answer_text)) then
      outcome := 'correct'; pts := c; v_cor := v_cor + 1;
    else
      outcome := 'wrong'; pts := case when r.kind = 'tita' then tw else w end; v_wr := v_wr + 1;
    end if;
    v_score := v_score + pts;

    k := r.section;
    by_sec := jsonb_set(by_sec, array[k], jsonb_build_object(
      'correct', coalesce((by_sec->k->>'correct')::int,0) + (outcome='correct')::int,
      'wrong',   coalesce((by_sec->k->>'wrong')::int,0)   + (outcome='wrong')::int,
      'skipped', coalesce((by_sec->k->>'skipped')::int,0) + (outcome='skipped')::int,
      'score',   coalesce((by_sec->k->>'score')::numeric,0) + pts,
      'max',     coalesce((by_sec->k->>'max')::numeric,0) + c));
    k := coalesce(nullif(btrim(r.format),''), 'other');
    by_fmt := jsonb_set(by_fmt, array[k], jsonb_build_object(
      'correct', coalesce((by_fmt->k->>'correct')::int,0) + (outcome='correct')::int,
      'wrong',   coalesce((by_fmt->k->>'wrong')::int,0)   + (outcome='wrong')::int,
      'skipped', coalesce((by_fmt->k->>'skipped')::int,0) + (outcome='skipped')::int,
      'score',   coalesce((by_fmt->k->>'score')::numeric,0) + pts,
      'max',     coalesce((by_fmt->k->>'max')::numeric,0) + c));
  end loop;

  update public.attempts set
    status = 'submitted', submitted_at = now(), auto_submitted = p_auto,
    score = v_score, correct = v_cor, wrong = v_wr, skipped = v_sk, max_marks = t.max_marks,
    time_taken_sec = greatest(0, extract(epoch from (least(now(), a.deadline_at) - a.started_at))::int),
    breakdown = jsonb_build_object('sections', by_sec, 'formats', by_fmt)
  where id = a.id returning * into a;
  return a;
end $$;

create or replace function public.cv_attempt_summary(a public.attempts)
returns jsonb language sql stable as $$
  select jsonb_build_object(
    'attempt_id', a.id, 'attempt_no', a.attempt_no, 'is_first', a.is_first,
    'status', a.status, 'started_at', a.started_at, 'submitted_at', a.submitted_at,
    'auto_submitted', a.auto_submitted, 'score', a.score, 'correct', a.correct,
    'wrong', a.wrong, 'skipped', a.skipped, 'max_marks', a.max_marks,
    'time_taken_sec', a.time_taken_sec, 'breakdown', a.breakdown);
$$;

-- Everything the player needs to (re)draw the test at this moment.
create or replace function public.cv_attempt_payload(p_attempt uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare a public.attempts; t public.tests; idx int; qs jsonb; resp jsonb;
        sec_deadline timestamptz; cur_sec text;
begin
  select * into a from public.attempts where id = p_attempt;
  select * into t from public.tests where id = a.test_id;
  if t.timing = 'locked' then
    idx := (a.state->>'idx')::int;
    cur_sec := t.section_order[idx+1];
    sec_deadline := (a.state->'starts'->>idx)::timestamptz
                    + make_interval(mins => (t.section_minutes->>cur_sec)::int);
    select coalesce(jsonb_agg(public.cv_q_public(q) order by q.position), '[]')
      into qs from public.questions q where q.test_id = t.id and q.section = cur_sec;
  else
    select coalesce(jsonb_agg(public.cv_q_public(q) order by q.position), '[]')
      into qs from public.questions q where q.test_id = t.id;
  end if;
  select coalesce(jsonb_object_agg(r.question_id, jsonb_build_object(
           'answer', r.answer, 'time_ms', r.time_ms, 'marked', r.marked)), '{}')
    into resp from public.responses r where r.attempt_id = a.id;
  return jsonb_build_object(
    'attempt_id', a.id, 'attempt_no', a.attempt_no, 'status', a.status,
    'server_now', now(), 'started_at', a.started_at, 'deadline_at', a.deadline_at,
    'test', jsonb_build_object(
      'id', t.id, 'slug', t.slug, 'title', t.title, 'exam_name', t.exam_name,
      'timing', t.timing, 'minutes', t.minutes, 'section_order', to_jsonb(t.section_order),
      'section_minutes', t.section_minutes, 'marking', t.marking, 'max_marks', t.max_marks,
      'question_count', t.question_count),
    'section', case when t.timing = 'locked' then jsonb_build_object(
        'index', idx, 'name', cur_sec, 'deadline_at', sec_deadline,
        'is_last', idx >= array_length(t.section_order,1) - 1) end,
    'rapid_pos', case when t.timing = 'rapid' then coalesce((a.state->>'pos')::int, 0) end,
    'questions', qs,
    'responses', resp);
end $$;

-- ───────────────────────────────────────────────────────────────────────────
-- 4. STUDENT FUNCTIONS  (called from the browser with supabase.rpc)
-- ───────────────────────────────────────────────────────────────────────────

-- Grace allowed for slow networks on every clock check.
create or replace function public.cv_grace() returns interval language sql immutable as $$
  select interval '30 seconds' $$;

create or replace function public.cv_library()
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare u uuid := public.cv_require_user(); adm boolean := public.cv_is_admin();
begin
  return jsonb_build_object(
    'is_admin', adm,
    'server_now', now(),
    'series', coalesce((
      select jsonb_agg(jsonb_build_object(
        'id', s.id, 'slug', s.slug, 'title', s.title, 'blurb', s.blurb, 'kind', s.kind,
        'tests', coalesce((
          select jsonb_agg(jsonb_build_object(
            'slug', t.slug, 'title', t.title, 'exam_name', t.exam_name, 'timing', t.timing,
            'minutes', t.minutes, 'question_count', t.question_count, 'max_marks', t.max_marks,
            'marking', t.marking, 'access', t.access, 'opens_at', t.opens_at, 'closes_at', t.closes_at,
            'published', t.published,
            'unlocked', public.cv_has_access(u, t.id),
            'window', case when t.opens_at is not null and now() < t.opens_at then 'upcoming'
                           when t.closes_at is not null and now() >= t.closes_at then 'closed'
                           else 'open' end,
            'attempts', (select count(*) from public.attempts x where x.user_id = u and x.test_id = t.id and x.status = 'submitted'),
            'first', (select public.cv_attempt_summary(x) from public.attempts x
                       where x.user_id = u and x.test_id = t.id and x.is_first and x.status = 'submitted'),
            'last_attempt_id', (select x.id from public.attempts x where x.user_id = u and x.test_id = t.id
                                 and x.status = 'submitted' order by x.attempt_no desc limit 1),
            'in_progress', exists (select 1 from public.attempts x where x.user_id = u and x.test_id = t.id and x.status = 'in_progress'),
            'attempts_left', case when t.max_attempts is null then null else greatest(0, t.max_attempts -
                             (select count(*) from public.attempts x where x.user_id = u and x.test_id = t.id)) end
          ) order by t.sort, t.created_at)
          from public.tests t where t.series_id = s.id and (t.published or adm)), '[]'::jsonb)
      ) order by s.sort, s.created_at)
      from public.series s where s.published or adm), '[]'::jsonb));
end $$;

create or replace function public.cv_start_attempt(p_test_slug text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare u uuid := public.cv_require_user(); adm boolean := public.cv_is_admin();
        t public.tests; a public.attempts; n int; mins_total int; dl timestamptz;
begin
  select * into t from public.tests where slug = p_test_slug;
  if not found or (not t.published and not adm) then
    raise exception 'This test is not available.' using errcode = 'P0002';
  end if;
  if not public.cv_has_access(u, t.id) then
    raise exception 'You don''t have access to this test yet.' using errcode = '42501';
  end if;

  -- Resume an open attempt if its clock is still running; otherwise close it out.
  select * into a from public.attempts
   where user_id = u and test_id = t.id and status = 'in_progress' for update;
  if found then
    if t.timing = 'locked' then a := public.cv_sync_locked(a.id); end if;
    if now() > a.deadline_at + public.cv_grace() then
      perform public.cv_finalize(a.id, true);
      return jsonb_build_object('expired', true, 'attempt_id', a.id);
    end if;
    return public.cv_attempt_payload(a.id);
  end if;

  if not adm then
    if t.opens_at is not null and now() < t.opens_at then
      raise exception 'This test opens on %.', to_char(t.opens_at at time zone 'Asia/Kolkata', 'DD Mon, HH12:MI AM') || ' IST';
    end if;
    if t.closes_at is not null and now() >= t.closes_at then
      raise exception 'This test window has closed.';
    end if;
  end if;

  select count(*) into n from public.attempts where user_id = u and test_id = t.id;
  if t.max_attempts is not null and n >= t.max_attempts and not adm then
    raise exception 'You have used all % attempt(s) for this test.', t.max_attempts;
  end if;

  if t.timing = 'rapid' then
    select coalesce(sum(td),0) into mins_total from public.questions where test_id = t.id;
    dl := now() + make_interval(secs => mins_total) + interval '60 seconds';
    insert into public.attempts (user_id, test_id, attempt_no, is_first, deadline_at, state)
      values (u, t.id, n + 1, n = 0, dl, '{"pos":0}') returning * into a;
  elsif t.timing = 'locked' then
    dl := now() + make_interval(mins => t.minutes);
    insert into public.attempts (user_id, test_id, attempt_no, is_first, deadline_at, state)
      values (u, t.id, n + 1, n = 0, dl, jsonb_build_object('idx', 0, 'starts', jsonb_build_array(now())))
      returning * into a;
  else
    dl := now() + make_interval(mins => t.minutes);
    insert into public.attempts (user_id, test_id, attempt_no, is_first, deadline_at)
      values (u, t.id, n + 1, n = 0, dl) returning * into a;
  end if;
  return public.cv_attempt_payload(a.id);
end $$;

-- Autosave. p_items: [{"q":"<question uuid>","a":"2"|null,"ms":12345,"m":false}, ...]
create or replace function public.cv_save(p_attempt uuid, p_items jsonb)
returns jsonb language plpgsql security definer set search_path = public as $$
declare u uuid := public.cv_require_user(); a public.attempts; t public.tests;
        it jsonb; q public.questions; cur_sec text; sec_end timestamptz; pos int; saved int := 0;
        rejected jsonb := '[]'::jsonb;
begin
  select * into a from public.attempts where id = p_attempt and user_id = u for update;
  if not found then raise exception 'Attempt not found.'; end if;
  if a.status <> 'in_progress' then
    return jsonb_build_object('ok', false, 'reason', 'submitted', 'server_now', now());
  end if;
  select * into t from public.tests where id = a.test_id;
  if now() > a.deadline_at + public.cv_grace() then
    perform public.cv_finalize(a.id, true);
    return jsonb_build_object('ok', false, 'reason', 'time_up', 'server_now', now());
  end if;
  if t.timing = 'locked' then
    a := public.cv_sync_locked(a.id);
    cur_sec := t.section_order[(a.state->>'idx')::int + 1];
    sec_end := (a.state->'starts'->>((a.state->>'idx')::int))::timestamptz
               + make_interval(mins => (t.section_minutes->>cur_sec)::int);
  end if;
  pos := coalesce((a.state->>'pos')::int, 0);

  for it in select * from jsonb_array_elements(coalesce(p_items, '[]'::jsonb)) loop
    select * into q from public.questions where id = (it->>'q')::uuid and test_id = t.id;
    if not found then rejected := rejected || to_jsonb(it->>'q'); continue; end if;
    if t.timing = 'locked' and (q.section <> cur_sec or now() > sec_end + public.cv_grace()) then
      rejected := rejected || to_jsonb(it->>'q'); continue;
    end if;
    if t.timing = 'rapid' then
      if q.position < pos then rejected := rejected || to_jsonb(it->>'q'); continue; end if;
      pos := q.position + 1;       -- forward only
    end if;
    if q.kind = 'mcq' and it->>'a' is not null
       and not (it->>'a' ~ '^[0-3]$' and (it->>'a')::int < jsonb_array_length(q.options)) then
      rejected := rejected || to_jsonb(it->>'q'); continue;
    end if;
    insert into public.responses (attempt_id, question_id, answer, time_ms, marked, updated_at)
    values (a.id, q.id, left(nullif(btrim(it->>'a'), ''), 200),
            greatest(0, least(coalesce((it->>'ms')::int, 0), 36000000)),
            coalesce((it->>'m')::boolean, false), now())
    on conflict (attempt_id, question_id) do update set
      answer = excluded.answer,
      time_ms = greatest(public.responses.time_ms, excluded.time_ms),
      marked = excluded.marked, updated_at = now();
    saved := saved + 1;
  end loop;

  if t.timing = 'rapid' then
    update public.attempts set state = jsonb_build_object('pos', pos) where id = a.id;
  end if;
  return jsonb_build_object('ok', true, 'saved', saved, 'rejected', rejected, 'server_now', now());
end $$;

-- Locked sections: finish the current section and open the next one.
create or replace function public.cv_next_section(p_attempt uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare u uuid := public.cv_require_user(); a public.attempts; t public.tests; idx int; n int;
begin
  select * into a from public.attempts where id = p_attempt and user_id = u for update;
  if not found then raise exception 'Attempt not found.'; end if;
  select * into t from public.tests where id = a.test_id;
  if t.timing <> 'locked' then raise exception 'This test has no sections to advance.'; end if;
  if a.status <> 'in_progress' then return jsonb_build_object('submitted', true, 'attempt_id', a.id); end if;
  a := public.cv_sync_locked(a.id);
  idx := (a.state->>'idx')::int; n := array_length(t.section_order, 1);
  if idx >= n - 1 then
    perform public.cv_finalize(a.id, false);
    return jsonb_build_object('submitted', true, 'attempt_id', a.id);
  end if;
  update public.attempts set
    state = jsonb_build_object('idx', idx + 1, 'starts', (a.state->'starts') || to_jsonb(now())),
    -- ending a section early shortens the whole test by the unused time
    deadline_at = now() + make_interval(mins => (
      select coalesce(sum((t.section_minutes->>s)::int),0)::int from unnest(t.section_order[idx+2:n]) s))
  where id = a.id;
  return public.cv_attempt_payload(a.id);
end $$;

create or replace function public.cv_submit(p_attempt uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare u uuid := public.cv_require_user(); a public.attempts;
begin
  select * into a from public.attempts where id = p_attempt and user_id = u;
  if not found then raise exception 'Attempt not found.'; end if;
  a := public.cv_finalize(a.id, false);
  return public.cv_attempt_summary(a);
end $$;

-- Full review — only after submission.
create or replace function public.cv_review(p_attempt uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
declare u uuid := public.cv_require_user(); a public.attempts; t public.tests; qs jsonb;
begin
  select * into a from public.attempts where id = p_attempt;
  if not found or (a.user_id <> u and not public.cv_is_admin()) then
    raise exception 'Attempt not found.';
  end if;
  if a.status <> 'submitted' then
    if now() > a.deadline_at + public.cv_grace() then a := public.cv_finalize(a.id, true);
    else raise exception 'Finish the test to see the review.'; end if;
  end if;
  select * into t from public.tests where id = a.test_id;
  select jsonb_agg(public.cv_q_public(q) || jsonb_build_object(
           'answer_index', q.answer_index, 'answer_text', q.answer_text,
           'explanation', q.explanation, 'difficulty', q.difficulty,
           'response', r.answer, 'time_ms', coalesce(r.time_ms, 0), 'marked', coalesce(r.marked, false))
         order by q.position)
    into qs from public.questions q
    left join public.responses r on r.question_id = q.id and r.attempt_id = a.id
   where q.test_id = t.id;
  return jsonb_build_object(
    'summary', public.cv_attempt_summary(a),
    'test', jsonb_build_object('slug', t.slug, 'title', t.title, 'exam_name', t.exam_name,
            'timing', t.timing, 'minutes', t.minutes, 'marking', t.marking,
            'section_order', to_jsonb(t.section_order)),
    'questions', coalesce(qs, '[]'::jsonb));
end $$;

create or replace function public.cv_my_attempts(p_test_slug text default null)
returns jsonb language sql stable security definer set search_path = public as $$
  select coalesce(jsonb_agg(public.cv_attempt_summary(a) || jsonb_build_object(
           'test_slug', t.slug, 'test_title', t.title) order by a.started_at desc), '[]')
  from public.attempts a join public.tests t on t.id = a.test_id
  where a.user_id = public.cv_require_user() and a.status = 'submitted'
    and (p_test_slug is null or t.slug = p_test_slug);
$$;

-- ───────────────────────────────────────────────────────────────────────────
-- 5. ADMIN FUNCTIONS
-- ───────────────────────────────────────────────────────────────────────────

create or replace function public.cv_admin_save_series(p jsonb)
returns uuid language plpgsql security definer set search_path = public as $$
declare v_id uuid;
begin
  perform public.cv_require_admin();
  if nullif(p->>'id','') is not null then
    update public.series set
      slug = coalesce(p->>'slug', slug), title = coalesce(p->>'title', title),
      blurb = case when p ? 'blurb' then p->>'blurb' else blurb end,
      kind = coalesce(p->>'kind', kind), sort = coalesce((p->>'sort')::int, sort),
      published = coalesce((p->>'published')::boolean, published)
    where id = (p->>'id')::uuid returning id into v_id;
  else
    insert into public.series (slug, title, blurb, kind, sort, published)
    values (p->>'slug', p->>'title', p->>'blurb', coalesce(p->>'kind','drill'),
            coalesce((p->>'sort')::int, 100), coalesce((p->>'published')::boolean, false))
    returning id into v_id;
  end if;
  return v_id;
end $$;

-- Audit an envelope with the same rules as Test Builder Studio's Gate 1.
-- Returns {"errors":[...], "warnings":[...], "delivery":{...}}.
create or replace function public.cv_audit_envelope(p_env jsonb)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare meta jsonb := p_env->'meta'; qs jsonb := p_env->'questions';
        cfg jsonb; errs text[] := '{}'; warns text[] := '{}';
        declared text[]; tt text; rapid boolean; q jsonb; i int := 0; tag text;
        ids text[] := '{}'; keys text[] := '{}'; key text; counts jsonb := '{}'::jsonb;
        sec text; have int; want int; opts jsonb;
        timing text; minutes int; sec_minutes jsonb; present text[]; mk jsonb; td_sum int := 0;
begin
  if coalesce(jsonb_typeof(meta),'') <> 'object' or coalesce(jsonb_typeof(qs),'') <> 'array' then
    return jsonb_build_object('errors', jsonb_build_array('Envelope must have top-level "meta" and "questions".'),
                              'warnings', '[]'::jsonb);
  end if;
  if jsonb_array_length(qs) = 0 then
    return jsonb_build_object('errors', jsonb_build_array('"questions" is empty.'), 'warnings', '[]'::jsonb);
  end if;
  cfg := public.cv_exam_config(meta->>'exam');
  if cfg is null then
    return jsonb_build_object('errors', jsonb_build_array(format('meta.exam "%s" is not a known exam.', meta->>'exam')),
                              'warnings', '[]'::jsonb);
  end if;
  tt := meta->>'testType';
  if tt is null or tt not in ('full','sectional') then errs := errs || format('meta.testType must be "full" or "sectional" (got "%s").', tt); end if;
  if coalesce(btrim(meta->>'testName'),'') = '' then errs := errs || 'meta.testName is missing.'::text; end if;
  select coalesce(array_agg(x), '{}') into declared
    from jsonb_array_elements_text(case when jsonb_typeof(meta->'sections') = 'array' then meta->'sections' else '[]' end) x;
  if cardinality(declared) = 0 then errs := errs || 'meta.sections is missing or empty.'::text; end if;
  foreach sec in array declared loop
    if not (cfg->'sections') ? sec then
      errs := errs || format('Section "%s" is not a %s section.', sec, cfg->>'name');
    end if;
  end loop;
  if tt = 'full' then
    for sec in select jsonb_array_elements_text(cfg->'order') loop
      if not sec = any(declared) then errs := errs || format('testType "full" but meta.sections omits %s.', sec); end if;
    end loop;
  end if;
  if meta ? 'timerMinutes' and jsonb_typeof(meta->'timerMinutes') <> 'null'
     and (jsonb_typeof(meta->'timerMinutes') <> 'number' or (meta->>'timerMinutes')::numeric <= 0) then
    errs := errs || 'meta.timerMinutes must be a positive number or null.'::text;
  end if;
  if meta ? 'timerMode' and jsonb_typeof(meta->'timerMode') <> 'null' and meta->>'timerMode' <> 'perQuestion' then
    errs := errs || format('meta.timerMode must be "perQuestion" or absent (got "%s").', meta->>'timerMode');
  end if;
  rapid := meta->>'timerMode' = 'perQuestion';
  if rapid and meta ? 'sectionTimers' and jsonb_typeof(meta->'sectionTimers') <> 'null' then
    errs := errs || 'meta.sectionTimers and timerMode "perQuestion" cannot be used together.'::text;
  end if;

  for q in select * from jsonb_array_elements(qs) loop
    tag := coalesce(nullif(q->>'id',''), 'index ' || i);
    if coalesce(q->>'id','') = '' then errs := errs || format('Question at index %s has no id.', i);
    elsif q->>'id' = any(ids) then errs := errs || format('Duplicate id: %s', q->>'id');
    else ids := ids || (q->>'id'); end if;
    if q->>'verified' is distinct from 'ok' then errs := errs || format('%s: verified is not "ok".', tag); end if;
    if q->>'status' is distinct from 'approved' then errs := errs || format('%s: status is not "approved".', tag); end if;
    if coalesce(q->>'section','') = '' or not (q->>'section') = any(declared) then
      errs := errs || format('%s: section "%s" is not in meta.sections.', tag, q->>'section');
    else
      counts := jsonb_set(counts, array[q->>'section'], to_jsonb(coalesce((counts->>(q->>'section'))::int,0) + 1));
    end if;
    if coalesce(btrim(q->>'stem'),'') = '' then errs := errs || format('%s: empty stem.', tag); end if;
    opts := case when jsonb_typeof(q->'options') = 'array' then q->'options' else '[]'::jsonb end;
    key := btrim(coalesce(q->>'stem','')) || '␀' || btrim(coalesce(q->>'passage','')) || '␀' || opts::text;
    if key = any(keys) then warns := warns || format('%s repeats an earlier question exactly.', tag); else keys := keys || key; end if;
    if coalesce(btrim(q->>'format'),'') = '' then warns := warns || format('%s: empty format label — topic analysis will fragment.', tag); end if;
    if q->>'kind' is null or q->>'kind' not in ('mcq','tita') then
      errs := errs || format('%s: kind must be "mcq" or "tita".', tag);
    end if;
    if rapid then
      if q->>'kind' = 'tita' or jsonb_array_length(opts) = 0 then
        errs := errs || format('%s: TITA is not allowed in rapid mode.', tag);
      end if;
      if coalesce(jsonb_typeof(q->'td'),'') <> 'number' or (q->>'td') !~ '^\d+$' or (q->>'td')::int not between 10 and 300 then
        errs := errs || format('%s: rapid mode needs a whole-number td between 10 and 300 seconds.', tag);
      else td_sum := td_sum + (q->>'td')::int; end if;
    end if;
    if q->>'kind' = 'tita' then
      if jsonb_array_length(opts) > 0 then errs := errs || format('%s: TITA question carries options.', tag); end if;
      if coalesce(btrim(q->>'answer'),'') = '' then errs := errs || format('%s: TITA answer is empty.', tag); end if;
    elsif q->>'kind' = 'mcq' then
      if jsonb_array_length(opts) <> 4 then
        errs := errs || format('%s: MCQ needs exactly 4 options (has %s).', tag, jsonb_array_length(opts));
      elsif coalesce(jsonb_typeof(q->'answerIndex'),'') <> 'number' or (q->>'answerIndex') !~ '^[0-3]$' then
        errs := errs || format('%s: answerIndex must be 0–3.', tag);
      elsif btrim(opts->>((q->>'answerIndex')::int)) <> btrim(coalesce(q->>'answer','')) then
        errs := errs || format('%s: answer text does not match options[answerIndex].', tag);
      end if;
    end if;
    i := i + 1;
  end loop;

  foreach sec in array declared loop
    have := coalesce((counts->>sec)::int, 0); want := (cfg->'sections'->>sec)::int;
    if tt = 'full' and have <> want then errs := errs || format('Count mismatch — %s: %s of %s.', sec, have, want);
    elsif tt = 'sectional' and have = 0 then errs := errs || format('%s is declared but has no questions.', sec);
    elsif tt = 'sectional' and want is not null and have <> want then
      warns := warns || format('%s: %s question(s) vs official %s — fine for a drill.', sec, have, want);
    end if;
  end loop;

  -- Delivery (same derivation as Studio)
  mk := cfg->'marking';
  if meta ? 'titaW' and jsonb_typeof(meta->'titaW') = 'number' then mk := mk || jsonb_build_object('titaW', meta->'titaW'); end if;
  select coalesce(array_agg(o), '{}') into present
    from jsonb_array_elements_text(cfg->'order') o
   where exists (select 1 from jsonb_array_elements(qs) x where x->>'section' = o);
  if rapid then
    timing := 'rapid'; minutes := greatest(1, ceil(td_sum / 60.0)::int);
  elsif jsonb_typeof(meta->'timerMinutes') = 'number' then
    timing := 'single'; minutes := round((meta->>'timerMinutes')::numeric)::int;
  elsif cfg->>'timing' = 'single' then
    timing := 'single';
    minutes := case when tt = 'full' then (cfg->>'duration')::int
               else greatest(5, round(jsonb_array_length(qs) * (cfg->>'duration')::numeric
                     / (select sum(v::int) from jsonb_each_text(cfg->'sections') e(k, v)))::int) end;
  elsif cardinality(present) <= 1 then
    timing := 'single';
    minutes := coalesce((meta->'sectionTimers'->>present[1])::int, (cfg->>'secMinutes')::int);
  else
    timing := 'locked';
    select jsonb_object_agg(s, coalesce((meta->'sectionTimers'->>s)::int, (cfg->>'secMinutes')::int))
      into sec_minutes from unnest(present) s;
    select sum(v::int) into minutes from jsonb_each_text(sec_minutes) e(k, v);
  end if;

  return jsonb_build_object(
    'errors', to_jsonb(errs), 'warnings', to_jsonb(warns),
    'delivery', jsonb_build_object(
      'exam_key', cfg->>'key', 'exam_name', cfg->>'name', 'test_type', tt, 'timing', timing,
      'minutes', minutes, 'section_order', to_jsonb(case when cardinality(present) > 0 then present else declared end),
      'section_minutes', sec_minutes, 'marking', mk,
      'question_count', jsonb_array_length(qs),
      'max_marks', jsonb_array_length(qs) * (mk->>'c')::int,
      'title', meta->>'testName'));
end $$;

-- Import (or replace) a test from a Studio envelope.
-- p_opts: {"slug","series_id","access":"free|paid","published":bool,"opens_at","closes_at",
--          "max_attempts","sort","title","replace":bool}
create or replace function public.cv_admin_import_test(p_env jsonb, p_opts jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path = public as $$
declare audit jsonb; d jsonb; v_slug text; existing public.tests; t public.tests;
        q jsonb; ord int := 0; order_arr text[];
begin
  perform public.cv_require_admin();
  audit := public.cv_audit_envelope(p_env);
  if jsonb_array_length(audit->'errors') > 0 then
    return jsonb_build_object('ok', false, 'audit', audit);
  end if;
  d := audit->'delivery';
  v_slug := lower(regexp_replace(coalesce(nullif(p_opts->>'slug',''), d->>'title'), '[^a-zA-Z0-9]+', '-', 'g'));
  v_slug := btrim(v_slug, '-');

  select * into existing from public.tests where slug = v_slug;
  if found then
    if not coalesce((p_opts->>'replace')::boolean, false) then
      raise exception 'A test with the address "%" already exists. Tick "replace" or choose another address.', v_slug;
    end if;
    if exists (select 1 from public.attempts where test_id = existing.id) then
      raise exception 'Students have already attempted "%", so it can''t be replaced. Import it under a new address.', v_slug;
    end if;
    delete from public.tests where id = existing.id;
  end if;

  insert into public.tests (slug, series_id, title, exam_key, exam_name, test_type, timing, minutes,
      section_order, section_minutes, marking, max_marks, question_count, access, published,
      opens_at, closes_at, max_attempts, sort, source_meta)
  values (v_slug, nullif(p_opts->>'series_id','')::uuid,
      coalesce(nullif(p_opts->>'title',''), d->>'title'), d->>'exam_key', d->>'exam_name',
      d->>'test_type', d->>'timing', (d->>'minutes')::int,
      array(select jsonb_array_elements_text(d->'section_order')), d->'section_minutes',
      d->'marking', (d->>'max_marks')::int, (d->>'question_count')::int,
      coalesce(p_opts->>'access', 'paid'), coalesce((p_opts->>'published')::boolean, false),
      nullif(p_opts->>'opens_at','')::timestamptz, nullif(p_opts->>'closes_at','')::timestamptz,
      nullif(p_opts->>'max_attempts','')::int, coalesce((p_opts->>'sort')::int, 100),
      p_env->'meta')
  returning * into t;

  order_arr := t.section_order;
  -- Delivery order: rapid keeps the envelope order; otherwise group by section order,
  -- keeping the envelope order inside each section.
  for q in
    select x.v from jsonb_array_elements(p_env->'questions') with ordinality x(v, n)
    order by case when t.timing = 'rapid' then 0 else array_position(order_arr, x.v->>'section') end, x.n
  loop
    insert into public.questions (test_id, qid, position, section, format, kind, passage, stem,
        options, fig, table_html, td, difficulty, tags, answer_index, answer_text, explanation)
    values (t.id, q->>'id', ord, q->>'section', q->>'format', q->>'kind',
        nullif(q->>'passage',''), q->>'stem',
        case when q->>'kind' = 'mcq' then q->'options' else null end,
        nullif(q->>'fig',''), nullif(q->>'table',''),
        case when jsonb_typeof(q->'td') = 'number' then (q->>'td')::int end,
        q->>'difficulty', q->'tags',
        case when q->>'kind' = 'mcq' then (q->>'answerIndex')::int end,
        q->>'answer', q->>'explanation');
    ord := ord + 1;
  end loop;

  return jsonb_build_object('ok', true, 'test_id', t.id, 'slug', t.slug, 'audit', audit);
end $$;

create or replace function public.cv_admin_update_test(p_slug text, p jsonb)
returns jsonb language plpgsql security definer set search_path = public as $$
declare t public.tests;
begin
  perform public.cv_require_admin();
  update public.tests set
    title        = coalesce(nullif(p->>'title',''), title),
    series_id    = case when p ? 'series_id' then nullif(p->>'series_id','')::uuid else series_id end,
    access       = coalesce(p->>'access', access),
    published    = coalesce((p->>'published')::boolean, published),
    opens_at     = case when p ? 'opens_at' then nullif(p->>'opens_at','')::timestamptz else opens_at end,
    closes_at    = case when p ? 'closes_at' then nullif(p->>'closes_at','')::timestamptz else closes_at end,
    max_attempts = case when p ? 'max_attempts' then nullif(p->>'max_attempts','')::int else max_attempts end,
    sort         = coalesce((p->>'sort')::int, sort)
  where slug = p_slug returning * into t;
  if not found then raise exception 'No test at "%".', p_slug; end if;
  return to_jsonb(t) - 'source_meta';
end $$;

create or replace function public.cv_admin_delete_test(p_slug text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare t public.tests;
begin
  perform public.cv_require_admin();
  select * into t from public.tests where slug = p_slug;
  if not found then raise exception 'No test at "%".', p_slug; end if;
  if exists (select 1 from public.attempts where test_id = t.id) then
    raise exception 'Students have attempted this test. Unpublish it instead of deleting it.';
  end if;
  delete from public.tests where id = t.id;
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.cv_admin_overview()
returns jsonb language plpgsql stable security definer set search_path = public as $$
begin
  perform public.cv_require_admin();
  return jsonb_build_object(
    'series', coalesce((select jsonb_agg(to_jsonb(s) order by s.sort, s.created_at) from public.series s), '[]'),
    'tests', coalesce((select jsonb_agg((to_jsonb(t) - 'source_meta') || jsonb_build_object(
                 'attempts', (select count(*) from public.attempts a where a.test_id = t.id and a.status = 'submitted'),
                 'series_title', (select title from public.series s where s.id = t.series_id))
               order by t.created_at desc) from public.tests t), '[]'),
    'students', (select count(*) from public.profiles),
    'entitlements', coalesce((select jsonb_agg(jsonb_build_object(
                 'id', e.id, 'email', p.email, 'name', p.full_name, 'scope', e.scope,
                 'target', case e.scope when 'series' then (select title from public.series where id = e.ref_id)
                                        when 'test' then (select title from public.tests where id = e.ref_id)
                                        else 'Everything' end,
                 'expires_at', e.expires_at, 'note', e.note, 'created_at', e.created_at)
               order by e.created_at desc)
               from public.entitlements e join public.profiles p on p.id = e.user_id
               where e.revoked_at is null), '[]'),
    'recent', coalesce((select jsonb_agg(x order by x->>'submitted_at' desc) from (
                 select jsonb_build_object('attempt_id', a.id, 'email', p.email, 'name', p.full_name,
                   'test', t.title, 'score', a.score, 'max', a.max_marks, 'is_first', a.is_first,
                   'submitted_at', a.submitted_at, 'auto', a.auto_submitted) x
                 from public.attempts a join public.profiles p on p.id = a.user_id
                 join public.tests t on t.id = a.test_id
                 where a.status = 'submitted' order by a.submitted_at desc limit 50) r), '[]'));
end $$;

-- Grant access by email. The student must have signed up (logged in once) first.
create or replace function public.cv_admin_grant(p_email text, p_scope text, p_ref uuid default null,
                                                 p_expires timestamptz default null, p_note text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare adm uuid := public.cv_require_admin(); target uuid; e public.entitlements;
begin
  select id into target from public.profiles where lower(email) = lower(btrim(p_email));
  if target is null then
    raise exception 'No student with the email "%" yet. Ask them to log in to campverbal.com/app once, then grant again.', p_email;
  end if;
  insert into public.entitlements (user_id, scope, ref_id, expires_at, note, granted_by)
  values (target, p_scope, case when p_scope = 'all' then null else p_ref end, p_expires, p_note, adm)
  returning * into e;
  return to_jsonb(e);
end $$;

create or replace function public.cv_admin_revoke(p_entitlement uuid)
returns jsonb language plpgsql security definer set search_path = public as $$
begin
  perform public.cv_require_admin();
  update public.entitlements set revoked_at = now() where id = p_entitlement;
  return jsonb_build_object('ok', true);
end $$;

-- ───────────────────────────────────────────────────────────────────────────
-- 6. WHO CAN CALL WHAT
--    Internal helpers are closed to the browser; only the cv_* entry points
--    below are callable, and each checks the caller itself.
-- ───────────────────────────────────────────────────────────────────────────
do $$
declare f record;
begin
  for f in select p.oid::regprocedure as sig from pg_proc p
           where p.pronamespace = 'public'::regnamespace and p.proname like 'cv\_%'
  loop
    execute format('revoke execute on function %s from public, anon, authenticated', f.sig);
  end loop;
end $$;

grant execute on function
  public.cv_library(), public.cv_start_attempt(text), public.cv_save(uuid, jsonb),
  public.cv_next_section(uuid), public.cv_submit(uuid), public.cv_review(uuid),
  public.cv_my_attempts(text), public.cv_is_admin(),
  public.cv_audit_envelope(jsonb), public.cv_admin_save_series(jsonb),
  public.cv_admin_import_test(jsonb, jsonb), public.cv_admin_update_test(text, jsonb),
  public.cv_admin_delete_test(text), public.cv_admin_overview(),
  public.cv_admin_grant(text, text, uuid, timestamptz, text), public.cv_admin_revoke(uuid)
to authenticated;

-- Functions used inside RLS policies must stay callable.
-- (auth.uid() is Supabase's own and already granted.)
