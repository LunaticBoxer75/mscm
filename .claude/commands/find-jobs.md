# Daily Job Search for Bhumika (MSCM)

Full pipeline: preflight → scrape → Pass 1 quick-score → Pass 2 AI score → 4-panel report → export → publish.

**Cadence markers:** `[REQUIRED]` every run. `[OPTIONAL]` run if asked or if something looks off.
`[WEEKLY]` too slow or too broad for a daily run — see the Weekly section, do not put these in the daily path.

**Interpreter rule.** `python` = mise 3.12.8 and is the ONLY one with `jobspy`. Anything that imports
`src.scraper`, `src.scorer`, `src.quick_scorer` or `src.reporter` MUST use `python`. Steps that only
touch `user_store` / `tracker` / `todos` / `interview_prep` / `prep_content` use `python3` (3.9.21),
which is quieter — it does not emit the `RequestsDependencyWarning`. Do not "normalize" these.

---

## 0. Preflight [REQUIRED]

**Where things live (read once).** Three branches on the `github` remote, deliberately separate:

| Branch | Holds | Written by |
|---|---|---|
| `main` | Code + `content/` only | You, when code changes |
| `user-data` | `data/user_data.json` — her applications, chats, to-dos, stories, mocks, dismissals | The dashboard + local scripts, via the GitHub API |
| `jobs-data` | `data/jobs_deploy.db` — ONE commit, force-replaced each run | Step 8 of this skill |

Her data is never on `main`, so nothing in this skill can conflict with or clobber it — there is no
pull-before-push step for her data any more. `data/user_data.json` and `data/jobs_deploy.db` in the
working tree are local copies only (gitignored).

**0a. Her store must be reachable.** Steps 6-7 read which jobs she's tracking; without the token they
fall back to a possibly-stale local snapshot, and the export's prune protection is only as good as
that snapshot.

```
cd /Users/aniketsw/workspaces/mscm && python3 -c "from src import user_store as u; print('store:', 'REMOTE (user-data branch)' if u.is_remote() else 'LOCAL SNAPSHOT ONLY — add MSCM_GITHUB_TOKEN to .streamlit/secrets.toml'); print(u.stats())"
```

**0b. DB integrity** before anything writes to it:

```
cd /Users/aniketsw/workspaces/mscm && sqlite3 "file:data/jobs.db?mode=ro" "PRAGMA quick_check;"
```

---

## 1. Scrape [REQUIRED]

Indeed + LinkedIn, 168h lookback (1 week — tolerates missed days). ~936 searches (36 queries × 2 job
types × 13 locations), **~4.5h** — run it in the background and monitor it. Each search takes ~50s,
almost all of it LinkedIn deliberately pausing 3-7s between its ~10 page requests (Indeed: <1s). The
scraper runs 3 searches in parallel (`scrape_workers` in `config/profile.json` search_preferences,
default 3 — tested with 0 blocks) and keeps every DB write on one thread. If LinkedIn returns a 429,
all workers pause 2 minutes and the progress line shows `N LinkedIn blocks`; if blocks keep coming,
lower `scrape_workers`. The user chose on 2026-09-26 to keep LinkedIn daily — do not drop or
down-sample it without asking. It commits after every query and
prints one `[done/total] … ~Nm left` line per query, so a hung run shows as a log that stops
advancing (a slow run keeps printing). "new" counts only rows actually inserted — one row per
posting URL, enforced by a unique index.

```
cd /Users/aniketsw/workspaces/mscm && python -c "
from src.scraper import scrape_all_jobs
jobs = scrape_all_jobs(sites=['indeed', 'linkedin'], hours_old=168)
print(f'Inserted {len(jobs)} new jobs')
" 2>&1 | tee /tmp/scrape.log
```

Count per-query failures. Use `;` not `&&` — `grep -c` exits 1 when the count is 0:

```
grep -c '\[!\]' /tmp/scrape.log; grep '\[!\]' /tmp/scrape.log | head
```

---

## 2. Pass 1 — quick-score, and assert nothing is left unscored [REQUIRED]

Rule-based triage over every row. The standing invariant is "no job is ever left unscored" — a row
with `score IS NULL` is invisible in every panel and in the export. This step heals then asserts.

```
cd /Users/aniketsw/workspaces/mscm && python -c "
from src.reporter import get_stats
from src.quick_scorer import score_all_unscored
n = get_stats()['unscored_jobs']
print('unscored before:', n)
if n: print('rescued:', score_all_unscored()); print('unscored after:', get_stats()['unscored_jobs'])
assert get_stats()['unscored_jobs'] == 0, 'INVARIANT VIOLATED: unscored jobs remain'"
```

If this fails, the offender is almost certainly a row with a falsy title —
`src/quick_scorer.py:229-230` `continue`s past those forever. Fix the row or the `continue`; do not
skip the assert.

---

## 3. Run coverage by panel [REQUIRED]

Proves the run actually produced rows in all four panels. `STALE!` means the newest data in the DB
is not from today — i.e. this run inserted nothing, which a plain GROUP BY would hide. A dead panel
shows as an explicit `0`, not a missing line.

```
cd /Users/aniketsw/workspaces/mscm && sqlite3 -header -column "file:data/jobs.db?mode=ro" "
WITH latest(d) AS (SELECT MAX(substr(scraped_at,1,10)) FROM jobs),
     panels(region, job_type) AS (VALUES ('seattle','fulltime'),('seattle','internship'),('national','fulltime'),('national','internship'))
SELECT (SELECT d FROM latest) AS run_date,
       CASE WHEN (SELECT d FROM latest) = date('now','localtime') THEN 'fresh' ELSE 'STALE!' END AS status,
       p.region, p.job_type,
       COUNT(j.job_id) AS new_rows,
       SUM(CASE WHEN j.source='indeed'   THEN 1 ELSE 0 END) AS indeed,
       SUM(CASE WHEN j.source='linkedin' THEN 1 ELSE 0 END) AS linkedin,
       SUM(CASE WHEN j.job_id IS NOT NULL AND j.source NOT IN ('indeed','linkedin') THEN 1 ELSE 0 END) AS other
FROM panels p
LEFT JOIN jobs j
       ON j.region = p.region AND j.job_type = p.job_type
      AND substr(j.scraped_at,1,10) = (SELECT d FROM latest)
GROUP BY p.region, p.job_type
ORDER BY p.region, p.job_type;"
```

A zero Seattle panel is a real, recurring failure (it happened on 2026-09-14, -19 and -20). If it
shows, report it — the `[!]` lines from step 1 are the diagnostic.

---

## 4. Pass 2 — AI scoring, inline [REQUIRED]

Pass 1 is keyword-only, and its misses are gross: a podiatrist post scores 95, and Senior TPM roles
land in the internship panel. Pass 2 is you reading the actual job description. There is no API key
and no Bedrock call in this path — **you** are the scorer.

**4a. Select candidates.** Per-panel latest scrape day (a single global MAX silently zeroes Seattle
when only the national queries ran), description gate, per-panel cap. Read-only.

```
cd /Users/aniketsw/workspaces/mscm && python3 - <<'PY'
import sqlite3, json, os
conn = sqlite3.connect("file:data/jobs.db?mode=ro", uri=True); conn.row_factory = sqlite3.Row
# Caps are deliberately lopsided toward full-time. Pass 2 is the scarce resource
# (you reading descriptions), and as of 2026-09-23 internships are a FALLBACK ONLY —
# full-time is the priority. Do not rebalance these without the user saying so.
PANELS = [("seattle_ft","region='seattle' AND job_type!='internship'",70,30),
          ("seattle_intern","region='seattle' AND job_type='internship'",70,5),
          ("national_ft","region='national' AND job_type!='internship'",75,30),
          ("national_intern","region='national' AND job_type='internship'",75,5)]
out = []
for name, where, floor, cap in PANELS:
    day = conn.execute(f"SELECT substr(MAX(scraped_at),1,10) FROM jobs WHERE {where}").fetchone()[0]
    rows = conn.execute(f"""SELECT job_id,title,company,location,job_type,salary_min,salary_max,
               substr(description,1,4000) AS description
        FROM jobs WHERE {where} AND score>=? AND LENGTH(description)>200
          AND json_extract(score_breakdown,'$.scorer') IS NULL
          AND substr(scraped_at,1,10)=? ORDER BY score DESC LIMIT ?""", (floor, day, cap)).fetchall()
    print(f"{name}: day={day} candidates={len(rows)}")
    out += [dict(r) for r in rows]
json.dump(out, open("/tmp/pass2_candidates.json","w"))
print("total", len(out), "| bytes", os.path.getsize("/tmp/pass2_candidates.json"))
PY
```

Expect ~30-40 candidates / ~150KB. If a panel returns 0, say so in the report and say why: 65% of
the DB (every LinkedIn row) has `description=''`, so the description gate excludes it. Those rows
keep their Pass-1 score and were never read by anyone — never present them as AI-scored.

**4b. Build the prompts** (15 jobs per batch; the prompt builder truncates each description at 2000
chars, so a batch is ~35K chars):

```
cd /Users/aniketsw/workspaces/mscm && python -c "
import json
from src.scorer import batch_score_prompt
jobs = json.load(open('/tmp/pass2_candidates.json'))
for i in range(0, len(jobs), 15):
    path = f'/tmp/pass2_batch{i//15+1}.txt'
    open(path,'w').write(batch_score_prompt(jobs[i:i+15]))
    print(path, len(jobs[i:i+15]), 'jobs')
"
```

**4c. Score them.** `Read` each `/tmp/pass2_batchN.txt`, score every job in it yourself, and write
the combined JSON array for ALL batches to `/tmp/pass2_scores.json` — freshly, every run (a leftover
file from yesterday will happily re-stamp yesterday's scores). One entry per job:

```json
[{"job_id": "...", "score": 0, "reasoning": "1-2 sentences", "highlights": ["..."], "red_flags": ["..."]}]
```

Score with the 7 documented dimensions (role relevance 25 / skills 20 / experience fit 15 /
location 15 / company tier 10 / growth 10 / visa 5). Read the description for the things Pass 1
cannot see: "2+ required, 5+ preferred" is fine, "must have 9+ years" is not; a clinical or retail
role with "Program Manager" in the title is a 10, not a 95; an internship panel entry that is
actually a senior FT req should be called out in `red_flags`.

**4d. Write back — one transaction, one connection.** Do NOT loop `scraper.update_job_score` (new
connection + DDL + commit + a dead Firestore import per row) and do NOT use
`scorer.parse_batch_scores` (silently returns `[]` on a JSON error and never reports what it
dropped). This exact script is the safe pattern: it commits the good rows FIRST, then reports
mismatches — reporting inside the transaction rolls back the whole batch over one bad id.

```
cd /Users/aniketsw/workspaces/mscm && python3 - <<'PY'
import sqlite3, json, datetime, sys
DB = "data/jobs.db"
ai = json.load(open("/tmp/pass2_scores.json"))   # the JSON array Claude produced
assert isinstance(ai, list) and ai, "pass2_scores.json must be a non-empty JSON array"
now = datetime.datetime.now().isoformat()
rows = [(e["score"], json.dumps({**e, "scorer": "ai"}), now, str(e["job_id"])) for e in ai]
conn = sqlite3.connect(DB, timeout=60)
conn.execute("PRAGMA busy_timeout=60000")
try:
    with conn:                       # commits the good rows
        cur = conn.executemany(
            "UPDATE jobs SET score=?, score_breakdown=?, scored_at=? WHERE job_id=?", rows)
        written = cur.rowcount
    if written != len(rows):         # report AFTER commit, never inside the txn
        missing = [r[3] for r in rows
                   if not conn.execute("SELECT 1 FROM jobs WHERE job_id=?", (r[3],)).fetchone()]
        print(f"WARN wrote {written}/{len(rows)}; unknown job_ids: {missing}")
        sys.exit(1)
    print(f"OK wrote {written}/{len(rows)} scores")
finally:
    conn.close()
PY
```

400 rows land in ~0.04s. The `"scorer": "ai"` stamp is what makes 4a idempotent — re-running the day
after will not re-pick the same jobs.

**4e. Verify.** Re-run 4a. Every panel must now report `candidates=0`. If not, the missing job_ids
were dropped — score them before moving on.

---

## 5. 4-panel report [REQUIRED]

Thresholds match what the export actually publishes (flat 70), so nothing appears in the terminal
that she cannot then find on the dashboard. Dismissed ids are subtracted from `user_store`.

```
cd /Users/aniketsw/workspaces/mscm && python3 - <<'PY'
import sqlite3, sys
sys.path.insert(0, ".")
from src import user_store
dismissed = {d.get("job_id") for d in user_store.get("dismissed_jobs") if d.get("job_id")}
conn = sqlite3.connect("file:data/jobs.db?mode=ro", uri=True)
PANELS = [("SEATTLE & AREA - FULL-TIME (top priority)",   "region='seattle' AND job_type!='internship'", 70, 12),
          ("REST OF USA - FULL-TIME",                     "region='national' AND job_type!='internship'", 75, 12),
          ("SEATTLE & AREA - INTERNSHIPS (fallback)",     "region='seattle' AND job_type='internship'",  70, 5),
          ("REST OF USA - INTERNSHIPS (fallback)",        "region='national' AND job_type='internship'",  75, 5)]
for name, where, floor, lim in PANELS:
    rows = conn.execute(f"""SELECT job_id, score, title, company, location, salary_min, salary_max, job_url,
               json_extract(score_breakdown,'$.scorer') AS scorer
        FROM jobs WHERE {where} AND score>=? AND (dismissed IS NULL OR dismissed=0)
        ORDER BY score DESC, scraped_at DESC LIMIT ?""", (floor, lim + len(dismissed))).fetchall()
    rows = [r for r in rows if r[0] not in dismissed][:lim]
    print(f"\n=== {name} ({len(rows)}) ===")
    for jid, sc, t, c, loc, smin, smax, url, scorer in rows:
        sal = f" | ${int(smin/1000)}K-${int(smax/1000)}K" if smin and smax else ""
        tag = "" if scorer == "ai" else "  (quick score only)"
        print(f"  [{int(sc)}] {t} @ {c} - {loc}{sal}{tag}\n      {url}")
conn.close()
PY
```

Present it in exactly this order: **both full-time panels first, Seattle before national, then the
two internship panels clearly labelled as fallback.** Full-time is the priority as of 2026-09-23;
internships only matter if a full-time role does not land. Lead the report with full-time — do not
open with internships even if an internship happens to score highest.

Keep the `(quick score only)` marker visible. It is the difference between "Claude read this JD" and
"a keyword matched a title."

---

## 6. Her pulse — follow-ups, to-dos, prep [REQUIRED, ~2s total]

Follow-ups due today or earlier (applied / interviewing only):

```
cd /Users/aniketsw/workspaces/mscm && python -W ignore -c "
from src.tracker import get_follow_ups_due
rows = get_follow_ups_due()
if not rows:
    print('  No follow-ups due.')
for f in rows:
    print(f\"  [{f['follow_up_date']}] {f['title']} @ {f['company']}\" + (f\" - {f['notes']}\" if f.get('notes') else '') + (f\"\n      {f['job_url']}\" if f.get('job_url') else ''))
"
```

Open high-priority to-dos:

```
cd /Users/aniketsw/workspaces/mscm && python3 -c "from src.todos import get_todos
for t in get_todos('open'):
    if t.get('priority') == 'high': print('  HIGH:', t['item'])"
```

STAR story coverage (behavioural themes with no story yet):

```
cd /Users/aniketsw/workspaces/mscm && python3 -c "from src.interview_prep import story_coverage
c = story_coverage(); print(f\"STAR themes covered {len(c['covered'])}/{len(c['covered'])+len(c['missing'])}\"); print('  missing:', ', '.join(c['missing'][:6]))" 2>/dev/null
```

---

## 7. Export the deploy DB [REQUIRED]

Keeps jobs scoring **70+, full-time and internships alike** (the old 55 internship floor is gone —
the UW CPT one-year rule makes internships a fallback). **DROPS** the legacy aux tables
(`applications`, `coffee_chats`, `todos`, `interview_recs`, `star_stories`) so a stale copy cannot
shadow the real store — her data lives in `data/user_data.json` and must never be copied here.
**Destructive:** it also `DELETE`s rows older than 90 days from `data/jobs.db`, the only full copy,
protected only by job_ids that have an application record. Report the prune count it prints.

```
cd /Users/aniketsw/workspaces/mscm && python scripts/export_deploy_db.py
```

---

## 8. Publish [REQUIRED]

Publishes the deploy DB to the `jobs-data` branch as a single, history-free commit. The running
dashboard notices within ~10 minutes and swaps it in — no redeploy, no push to `main`.

```
cd /Users/aniketsw/workspaces/mscm && python scripts/publish_jobs_db.py
```

The script force-pushes `refs/heads/jobs-data` ONLY — that branch is designed to hold one commit.
Never force-push `main` or `user-data`. It refuses files over 95MB (GitHub's limit is 100MB).

Push `main` only when code or `content/` changed, as a normal reviewed commit — never as part of the
daily data refresh.

---

## Health checks

Run all four after step 8. Any failure is a silent-failure alarm — report it, do not swallow it.

```
cd /Users/aniketsw/workspaces/mscm && python -c "
from src.reporter import get_stats
s = get_stats(); print(s)
assert s['unscored_jobs'] == 0, 'unscored jobs remain'"
```

```
cd /Users/aniketsw/workspaces/mscm && python3 -c "from src import prep_content; bad={k:v for k,v in prep_content.status().items() if not isinstance(v,int) or v==0}; print('CONTENT UNHEALTHY:',bad) if bad else print('content OK:',sum(prep_content.status().values()),'rows'); __import__('sys').exit(1 if bad else 0)"
```

```
cd /Users/aniketsw/workspaces/mscm && python3 -c "from src import user_store; s=user_store.stats(); print(s); assert sum(s.values())>0, 'her store read as empty — check MSCM_GITHUB_TOKEN / the user-data branch'"
```

Every dashboard page renders (headless; forces MSCM_STORE_MODE=file, never touches GitHub):

```
cd /Users/aniketsw/workspaces/mscm && python scripts/smoke_test_pages.py
```

Then state, in the summary you give her: new rows inserted, Pass-2 jobs actually AI-scored, rows
exported, prune count, deploy DB size.

---

## Failure modes

- **`database is locked`** — the Streamlit app or another run holds the WAL. The Pass-2 writeback
  already sets `timeout=60` + `PRAGMA busy_timeout=60000`; wait it out, or close the dashboard.
  A `mode=ro` read of a WAL DB can also fail transiently with error 14 while a writer commits —
  retry once. Never add `immutable=1` to work around it: that returns torn reads.
- **`database disk image is malformed`** — stop immediately. Do not export, do not push (the export
  rebuilds the deploy DB from this file and prunes it). Run
  `sqlite3 "file:data/jobs.db?mode=ro" "PRAGMA integrity_check;"`, copy the file aside, and recover
  from the last good state before running anything else.
- **"Saving is paused" banner / `StoreError`** — GitHub unreachable or the token expired. The
  dashboard serves her last-good data read-only and refuses writes rather than dropping them.
  Check the token's expiry; nothing needs recovering.
- **`jobs-data` publish rejected** — usually auth. Never "fix" it by committing the DB to `main`:
  that's the 250MB-history problem this layout exists to stop.
- **Scrape hangs** — the `[done/total]` log stops advancing. Rows up to the last finished query are
  already committed. Kill it (`pkill -f scrape_all_jobs`), report where it stopped, re-run step 1 —
  already-inserted postings are skipped by URL.
- **A panel reports 0 candidates in Pass 2** — almost always empty descriptions, not "nothing good".
  Say which panel and why; do not report those jobs as AI-scored.

---

## Weekly / optional — keep OUT of the daily path

- **[WEEKLY] LinkedIn description backfill.** Every LinkedIn row (65% of the DB) has
  `description=''` because `linkedin_fetch_description` is never passed, which is why Pass 2 can
  only see a third of the corpus and why the years-of-experience caps never fire on LinkedIn rows.
  A fetch costs ~0.73s per job serially, so the whole corpus is ~23h — never daily. Backfill the
  top ~300 LinkedIn rows by quick-score with empty descriptions (~3.5 min), with 0.3-0.5s jitter to
  stay off LinkedIn's 429 path, and count "fetched N, got description for M" — the jobspy helper
  swallows every error and returns `{}`, so a silent 429 storm is otherwise invisible.
- **[WEEKLY] Broad Pass 2.** Pass 2 at `score>=40` over the whole pool is ~51K jobs / ~2,500
  batches. Do not attempt it in a daily run. The daily band in step 4 (export floor, per-panel cap,
  this run's day only) is the honest scope.
- **[OPTIONAL] Markdown report file:**
  `python -c "from src.reporter import generate_daily_report; generate_daily_report(min_score=70, limit=50)"`
- **[OPTIONAL] Tracker + referrals:**
  `python -c "from src.tracker import generate_tracker_report; print(generate_tracker_report())"`
- **[OPTIONAL] Skills insights:**
  `python -c "from src.skills_insights import analyze_skills; r=analyze_skills(min_score=70); print(r['total'], [(x['skill'], x['pct']) for x in r['technical'][:5]])"`
  Note: run this against `data/jobs.db`, not the deploy copy — the export truncates descriptions to
  800 chars, which drops the Excel hit rate from 72% to 11%.
- **[WEEKLY] H1B sponsor staleness (nag, do not auto-download):**
  `python3 -c "import json; d=json.load(open('config/h1b_sponsors_verified.json')); print(d['fiscal_year'])"`
- **[OPTIONAL] Import coffee-chat action items into to-dos:**
  `python3 -c "from src.todos import import_coffee_chat_actions; print('imported', import_coffee_chat_actions())"`
  One batched write to her store (zero if nothing is new).

---

## Known gaps — do not claim these work

- **LinkedIn rows have no description** (~65% of the DB) — Pass 2 can't read them and Pass 1's
  description rules don't fire on them. See the weekly backfill above.
- **`config/profile.json`'s `distance_miles`, `min_salary` and `exclude_terms` are read by nothing.**
  Do not tell her 10+-year or unsalaried postings were filtered out.
- **Company size isn't stored** — the scraper drops JobSpy's employee-count field, so nothing can
  sort by it yet.

---

## Key Files

- Candidate profile + scoring weights: `config/profile.json`
- Search terms (36 queries × 17 locations × 2 job types, Indeed + LinkedIn only):
  `config/search_queries.json`
- **Local source of truth (jobs):** `data/jobs.db` — gitignored, ~280MB, full history
- **Dashboard artifact (jobs only, score 70+):** `data/jobs_deploy.db` — published to the
  `jobs-data` branch by `scripts/publish_jobs_db.py`; the dashboard downloads it (`src/jobs_data.py`)
- **Her data:** `user-data` branch, `data/user_data.json`, via `src/user_store.py` — applications, coffee chats, to-dos,
  interview recs, STAR stories, mock sessions, dismissed jobs. Never copy it into a jobs DB.
- Prep corpus: `content/*.json` via `src/prep_content.py`
- Pass 1: `src/quick_scorer.py` · Pass 2 prompt: `src/scorer.py:101 batch_score_prompt`
- Scraper: `src/scraper.py` · Export: `scripts/export_deploy_db.py` · Dashboard: `app.py`
- Logs from the last run: `/tmp/scrape.log`, `/tmp/pass2_candidates.json`, `/tmp/pass2_batch*.txt`,
  `/tmp/pass2_scores.json`
