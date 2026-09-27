# MSCM Job Search Pipeline

Daily automated job search for **Bhumika Choudhary** — incoming UW Foster Master of Supply Chain Management (MSCM) student, currently Global SME at Uber Risk & Compliance.

> **Career plan:** A full Jul–Dec 2026 upskilling + job-search plan lives in [`career-plan/`](career-plan/) — start at [`career-plan/INDEX.md`](career-plan/INDEX.md). It's a browsable binder (strategy, skills, 10 portfolio projects, networking templates, reading list, consulting fit-test, edge track) plus 24 printable weekly pages (`career-plan/weekly/`). Skill ordering there is evidence-based (from analyzing this repo's scraped JDs) and supersedes the older 90-Day PM Track doc.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# No API key needed. Pass-2 scoring is Claude Code reading descriptions inline.
# (Bedrock is NOT used — the corporate IAM principal lacks bedrock:InvokeModel and 403s.)

# Run full pipeline (scrape → score → report)
python -m src.pipeline

# Or run individual steps
python -m src.pipeline scrape    # Just scrape
python -m src.pipeline score     # Just score pending
python -m src.pipeline report    # Just generate report
```

## Slash Commands

- `/find-jobs` — Run full pipeline: scrape → score (inline) → report (4 panels)
- `/job-stats` — Show database statistics (by region, type, company)
- `/add-search` — Add a new search query
- `/generate-projects` — Analyze skill gaps and create portfolio project guides
- `/track` — Application tracker: update status, set follow-ups, view pipeline

## Priorities (current)

- **Full-time is the priority.** Internships are a FALLBACK ONLY as of 2026-09-23 — the UW CPT
  one-year rule likely rules out an internship inside her first academic year. Report full-time
  first; do not re-elevate internships without being told.
- **Risk / Compliance / Operations roles rank highest** — they match her actual Uber background.
- **Seattle & area before national.**

## Architecture

```
config/profile.json          ← Candidate profile, target roles, scoring weights
config/search_queries.json   ← Search terms by category (primary/secondary/stretch)
content/*.json               ← Static interview-prep content (cases, frameworks, metrics,
                               companies, loop map, resources, playbook)
src/scraper.py              ← JobSpy-based multi-board scraper (Seattle + National, FT + Intern)
src/quick_scorer.py         ← Pass 1: rule-based triage over ALL jobs
src/scorer.py               ← Pass 2 scaffolding (7 dimensions, 0-100, batch prompts)
src/reporter.py             ← 4-panel report + skills gap + trends
src/user_store.py           ← HER data: durable JSON + GitHub write-back  ★ see Data Stores
src/prep_content.py         ← Loader/validator for content/*.json
src/interview_prep.py       ← Mentor recs, STAR stories, mock bank + session history
src/tracker.py              ← Application status tracking with follow-ups
src/todos.py, networking.py ← To-dos; coffee-chat log
src/sponsor_data.py         ← H1B / E-Verify sponsor lookup (USCIS-verified counts)
src/projects.py             ← Auto-generate portfolio projects from skill gaps
src/referrals.py            ← LinkedIn referral link generator (search links only, never scraped)
src/pipeline.py             ← Orchestrator (full pipeline or individual steps)
app.py                      ← Streamlit dashboard, 13 pages via st.navigation (local + Cloud)
src/jobs_data.py            ← Downloads the deploy DB from the jobs-data branch
scripts/publish_jobs_db.py  ← Publishes the deploy DB to jobs-data (single commit, force-replaced)
scripts/dedupe_jobs.py      ← One-time cleanup of same-URL duplicate rows
scripts/smoke_test_pages.py ← Renders all 13 pages headlessly; exit 1 on any exception
scripts/export_deploy_db.py ← Trim + prune → data/jobs_deploy.db
scripts/migrate_user_data.py ← One-time SQLite → user_data.json migration (idempotent)
```

## Data Stores — three branches, deliberately separate

| Where | Holds | Written by |
|---|---|---|
| `data/jobs.db` (local only, gitignored, ~280MB) | Full corpus, one row per posting URL | `/find-jobs` scrape |
| `jobs-data` branch → `data/jobs_deploy.db` | Jobs scoring 70+ — **one commit, force-replaced each run** | `scripts/publish_jobs_db.py` |
| `user-data` branch → `data/user_data.json` | Her applications, coffee chats, todos, recs, STAR stories, mock sessions, dismissals | Dashboard + local scripts, via GitHub API (`src/user_store.py`) |
| `main` | Code + `content/` only | Normal reviewed commits |

**Why three:**
- Her data used to live in the deploy DB, so every `/find-jobs` push destroyed what she typed on the
  hosted dashboard (Streamlit Cloud's filesystem is ephemeral).
- Saving her data to `main` restarted the app on every click (Cloud reloads on commits to its branch).
- Committing the deploy DB to `main` put 13 × ~20MB into history that every cold start downloads.
  The `jobs-data` branch holds one commit, so that stops growing. (Old history is still ~250MB;
  purging it is a separate, irreversible step that hasn't been approved.)

**Never collapse these.** Nothing may write her data into a jobs DB, commit a jobs DB to `main`, or
force-push anything except `jobs-data`.

**Token:** `MSCM_GITHUB_TOKEN` (fine-grained, this repo only, Contents read/write, with expiry) in
Streamlit Cloud secrets AND local `.streamlit/secrets.toml` — see `.streamlit/secrets.toml.example`.
Not `GITHUB_TOKEN`: gh/CI set that name and it would make local scripts commit. Without the token,
`user_store` uses a local snapshot (not authoritative) and the dashboard can't download jobs.

**Store behaviour:** every save is read-latest → apply → write-with-SHA; on a conflict it re-applies
the change on the newer copy, so no writer loses data. If GitHub is unreachable the dashboard shows
her last-good data read-only with a banner and refuses writes rather than dropping them.

## Data Flow

```
/find-jobs in Claude Code
    → Scrapes Indeed + LinkedIn (36 queries × 2 job types × 13 locations, 3 in parallel, commit per search)
    → Pass 1: quick-scores ALL jobs, then ASSERTS zero unscored
    → Pass 2: Claude reads descriptions inline for top candidates, stamps scorer="ai"
    → 4-panel report (full-time first, internships flagged as fallback)
    → export_deploy_db.py (90-day prune by posting date, 70+ floor)
    → publish_jobs_db.py → jobs-data branch → dashboard swaps it in within ~10 min, no redeploy
```

## Scoring Architecture (Two-Pass)

1. **Pass 1 — Quick Scorer** (`src/quick_scorer.py`): Rule-based triage applied to ALL jobs immediately after scraping. Uses title keywords, seniority detection, years-of-experience extraction from description, and location matching. Kills obvious irrelevant jobs (retail, medical, etc.) at score <30. Fast — handles 1000+ jobs in seconds.

2. **Pass 2 — AI Scorer** (Claude inline, no API key): Claude Code itself reads descriptions and
   rescores with nuance (e.g. "2+ required, 5+ preferred" vs "must have 9+ years"), stamping
   `score_breakdown.scorer = "ai"`. `/find-jobs` runs it per-panel on the latest scrape day with
   caps skewed toward full-time (30 Seattle FT / 30 national FT / 5 + 5 internship).

**Known limits of this architecture — do not paper over them:**
- **Pass 1 alone cannot rank.** Only 5 distinct scores exist above 70 (95, 77, 75, 74, 71), with
  ~1,825 jobs tied at exactly 95. Within a bucket the order is arbitrary. Pass 2 is what creates
  real ordering; a row without `scorer="ai"` has never been read by anyone.
- **Pass 1 false positives are gross.** "Podiatrist (Program Manager)" at the VA scores 95. Senior
  TPM roles land in the internship panel.
- **65% of the corpus cannot be AI-scored at all.** All 58,474 LinkedIn rows have an empty
  `description`; only Indeed's ~31K are readable. Mark unread rows `(quick score only)` in reports.

## Dashboard

**Hosted on Streamlit Cloud** — same `app.py` runs locally and deployed.
- URL: https://mscm-bhumika.streamlit.app/
- GitHub repo: https://github.com/LunaticBoxer75/mscm (private)
- Reads jobs from the committed `data/jobs_deploy.db`; her data from `data/user_data.json`
- Access: Invite-only via Streamlit Cloud sharing settings

### Pages (14, in sidebar sections)
**☀️ Today** (landing) · **Find:** 📋 Jobs · 🤝 Referrals · 🛂 Sponsors · **Apply & Track:** 📊 Tracker ·
✅ To-Dos · ☕ Networking · **Prepare:** 🎤 Interview Prep · 🎓 Skills Gap · 📈 Skills Insights ·
🛠️ Projects · 🏆 Fellowships · **Tools:** ⚡ Tools · 📤 Export

Pages, not `st.tabs`: tabs execute every tab's code on every click (3,871 elements / 2.6s per click);
with `st.navigation` only the open page runs (0.01–0.25s warm).

**Today** — new-since-last-visit count (her visit dates live in `user_store` "meta", written at most
once a day), a 12-job shortlist (full-time, not acted on, posted ≤14 days, max 2 per company,
Seattle 8 / national 4), follow-ups due, high-priority to-dos, mock/STAR nudges.

**Job rows** (shared `job_row()` on Today and Jobs): 🤖 = Claude read it (Pass 2); ties rank
Claude-read first, then newest — never alphabetical. "Open ↗" never tracks; ✓ marks applied and queues
a 7-day follow-up; ✕ dismisses everywhere. Scraped text is HTML-escaped and only http(s) links render
(rows use `unsafe_allow_html`). Every save shows a "Saved — …" toast via `user_store.on_write`.

**Jobs** — 4 panels (Seattle FT, National FT, then the two internship panels labelled fallback). Row-per-job with
25-per-page pagination — `st.dataframe(on_select=...)` was unreliable and 500 buttons was slow.

**Interview Prep** — 7 sub-tabs, driven by `content/*.json`:
`🗺️ Loop Map · 🧩 Frameworks · 🧪 Case Bank · ⭐ STAR Stories · 🎯 Mock · 🏢 Company Prep · 📚 Resources`
28 worked cases, 22 frameworks, 41 metrics, 8-stage loop map with per-stage F-1 notes, 11 companies
(Amazon's 16 LPs verified), 84 grouped link-out resources, prep playbook. Mock answers persist as
STAR drafts; story-theme coverage gaps are surfaced.

### Content accuracy rules
- **"SIMDC" is a FAKE framework** circulating in AI-generated advice. Never use it. The real
  supply-chain diagnostic framework is **SCOR** (ASCM): Plan → Source → Transform → Order → Fulfill
  → Return → Orchestrate.
- **Amazon has 16 Leadership Principles, not 14.**
- Entries marked `verified: false` in `content/companies.json` were NOT confirmed from an official
  source — don't present them as fact.

## Features

- **4-Panel Dashboard:** Seattle FT, Seattle Internships, National FT, National Internships
- **7-Dimension AI Scoring:** Role relevance, skills match, experience fit, location, company tier, growth, visa
- **LinkedIn Referral Finder:** Auto-generates search links for employees, recruiters, alumni at target companies
- **Skills Gap Analysis:** What's commonly requested that Bhumika doesn't have yet
- **Portfolio Project Generator:** Builds complete beginner-friendly projects with runnable code
- **Application Tracker:** Track applied/interviewing/offer/rejected with follow-up reminders
- **Salary Benchmarking:** Compares found salaries against MSCM class average ($108K)
- **Durable Personal Data:** Her writes persist to `data/user_data.json` via GitHub write-back, surviving every deploy
- **Internship Detection:** Titles with "intern"/"co-op"/"new grad" auto-classified correctly

## Job Boards Scraped

- Indeed (primary — most reliable, no rate limits)
- LinkedIn (secondary — ~98% of scrape time: JobSpy paginates ~10/request with 3-7s pauses; rows arrive
  with NO description. User chose 2026-09-26 to keep it daily. Searches run 3 in parallel → ~4.5h per
  run instead of ~13h; a LinkedIn 429 pauses all workers 2 min.)
- ~~Google Jobs~~ (deprecated in jobspy, returns 0)
- ~~ZipRecruiter~~ (403 blocked)

## Scoring Dimensions

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| Role Relevance | 25% | Alignment with SCM/ops/PM target roles |
| Skills Match | 20% | Overlap with candidate's skills |
| Experience Fit | 15% | Appropriate level (3yr exp, entry-to-mid) |
| Location Match | 15% | Seattle/WA area or remote |
| Company Tier | 10% | Known SCM companies (Amazon, Boeing, etc.) |
| Growth Potential | 10% | Career trajectory opportunity |
| Visa Friendliness | 5% | OPT/H1B sponsorship likelihood |

## Target Roles

**Primary:** Supply Chain Analyst, Operations Analyst, SC Risk Analyst, Procurement, Demand Planning, Logistics, Program Manager, TPM  
**Secondary:** Process Improvement, Business Ops, Compliance, Risk Analyst  
**Stretch:** SC Manager, Strategic Sourcing, S&OP, Inventory Analyst

## Target Location

**Seattle & Area (priority):** Seattle, Tacoma, Everett (Bellevue/Kirkland/Redmond dropped 2026-09-26 —
Seattle's ~50mi search radius covers them; they added 9 of 169 new postings)
**National:** SF, SJ, LA, NYC, Chicago, Austin, Dallas, Atlanta, Boston, Denver, Remote

## Key Dependencies

- `python-jobspy` — Multi-board job scraping (MIT, 3.5k stars)
- `anthropic[bedrock]` — Claude via AWS Bedrock (uses corporate AWS credentials)
- `pandas` — Data manipulation
- `rich` — Terminal output formatting
- `streamlit` — Web dashboard (local + Streamlit Cloud)
- `requests` — GitHub contents API for user-data write-back (ships with streamlit)

## Notes

- Resume PDF at: `/Users/aniketsw/Downloads/Bhumika_Choudhary_Resume.pdf`
- Bhumika's LinkedIn: `bhummika`
- Program is STEM-designated (3-year OPT eligibility)
- Program: June 2026 — May/June 2027 (1-year, STEM-designated)
- Scoring uses Claude Sonnet via Bedrock (us-west-2, model: us.anthropic.claude-sonnet-4-20250514-v1:0)
- AWS auth: uses default credential chain (ada / SSO)
- Firestore was DROPPED (free-tier quota) and its code deleted. Audited 2026-09-26: it holds only a stale
  May 26-27 snapshot (9,800 jobs, all posted before June, + 8,558 empty score-only docs) and NONE of
  her data. `data/jobs.db` is the only real job source. Revoke the service-account key when convenient.
- GitHub: `git@github.com:LunaticBoxer75/mscm.git` (push via SSH)
- Internship postings are seasonal (summer: Aug-Oct, winter: Sep-Nov)
