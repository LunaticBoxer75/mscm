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
- **Seattle area first** (its own tab), **then big US metros** (Bay Area, New York area, Austin,
  Dallas-Fort Worth, LA, Chicago, Atlanta, Boston, Denver, …), **then everything else**. Defined once in
  `src/locations.py`; region comes from the job's location, not which search found it.
- **Nothing scoring under 70 is kept — including jobs Claude rated under 70** (user's rule, 2026-09-27).
  The scraper skips <70; the export deletes every <70 row except jobs she applied to/dismissed.
  Claude-rated ones are remembered in `rejected_urls` (30 days) so the scraper can't re-add them.
- **Claude reads Seattle LinkedIn jobs too**: `scripts/backfill_linkedin_descriptions.py` fetches their
  descriptions first (LinkedIn search returns none; ~80% success, ~1.6s each).
- **She has 4 years of experience** + an MSCM (June 2027). "5 years required" is not a blocker.

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
src/locations.py            ← Seattle-area vs rest of USA; big-metro map (city + state, exact)
src/company_size.py         ← Size tiers from config/company_sizes.json (top ~500 employers)
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

1. **Pass 1 — Quick Scorer** (`src/quick_scorer.py`, rewritten 2026-09-26): rules over ALL ~86K jobs
   in ~30s. Score = role fit (risk/compliance/fraud 50 > ops analytics 49 > supply chain 47 >
   planning/program mgmt 44 > adjacent 38) + role-scaled seniority, location (Seattle core 15 > Seattle
   area 13 > remote 11 > big metro 10 > rest of WA 8 > elsewhere 5), employer H-1B volume (USCIS counts, log scale), freshness, description signals, then hard
   caps. Every keyword rule uses word boundaries. Continuous (one decimal) so it can actually rank:
   269 distinct scores in 70–100 (was 5), largest bucket 2.8% of the 70+ set (was 42%).
   - **F-1 caps:** clearance / U.S.-person (ITAR) / citizen-only → 30; federal agencies → 35; defense
     employers with no description → 40. "Won't support STEM OPT / no E-Verify" −15.
   - **Other caps:** clinical, food, retail, driving, warehouse, trades 18–35; engineering and
     director+ 45; senior/manager titles filed as internships 35.
   - **Years required** read from the requirements section, largest stated minimum.
   - Measure changes with `scripts/eval_quick_scorer.py` (read-only; 550 hand-labelled rows).
     Precision of the ≥90 band on that sample: 21% → 69% relevant (34% → 1% irrelevant).
   - After changing rules: `python scripts/rescore_all.py --apply` (one transaction; never touches
     Pass-2 rows) so old and new rows share one scale.

2. **Pass 2 — AI Scorer** (Claude inline, no API key): Claude Code itself reads descriptions and
   rescores with nuance (e.g. "2+ required, 5+ preferred" vs "must have 9+ years"), stamping
   `score_breakdown.scorer = "ai"`. `/find-jobs` runs it per-panel on the latest scrape day with
   caps skewed toward full-time (30 Seattle FT / 30 national FT / 5 + 5 internship).

**Internship vs full-time comes from the TITLE** (`scraper.classify_job_type`): intern/internship/co-op
or "<season> 20xx". The boards' internship filter is loose — 70% of what it returned were ordinary
jobs — and new-grad roles are full-time (OPT) for her.

**Known limits — do not paper over them:**
- **65% of the corpus has no description** (all LinkedIn rows) — Pass 2 can't read them and Pass 1's
  description rules (years, clearance, sponsorship) can't fire. Mark unread rows `(quick score only)`.
  `linkedin_fetch_description=True` would fix it at one extra LinkedIn request per posting.
- Defense-employer caps are by name when there's no description — coarse.
- Company size isn't stored: JobSpy returns `company_num_employees` for Indeed only, as a text label
  ("10,000+"); LinkedIn doesn't return it.

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

**Visual design** — theme in `.streamlit/config.toml` with BOTH light and dark variants (the app follows
the device; never set `base`, which forces one mode). UW purple `#4B2E83` (lavender `#A78BDA` in dark); page styles in `app.py`'s `CSS` block, colored via `PALETTES` for the active mode (`st.context.theme`). A slim purple brand bar with the freshness pill replaces
the old big repeated title. Job rows are cards: colored score pill (≥90 green, 80s purple, 70s amber),
title line, meta line with pills (🤖 Claude read · 🏢 size · 📍 metro · salary · status). The CSS targets
action buttons by key prefix (`st-key-ok_`, `st-key-x_`, `st-key-sel_`) — keep those prefixes if you
rename keys. Phones: metrics wrap two per row and card actions stay on the card's row. Check visual
changes with real screenshots (Playwright driving the installed Chrome), not just AppTest.

**Job rows** (shared `job_row()` on Today and Jobs): 🤖 = Claude read it (Pass 2); ties rank
Claude-read first, then newest — never alphabetical. "Open ↗" never tracks; ✓ marks applied and queues
a 7-day follow-up; ✕ dismisses everywhere. Scraped text is HTML-escaped and only http(s) links render
(rows use `unsafe_allow_html`). Every save shows a "Saved — …" toast via `user_store.on_write`.
Rows also show 🏢 company size tier (or "(via agency)" for staffing firms) and 📍 metro for Rest-of-USA
jobs. The Jobs page has a "Largest companies first" sort, a City filter, and a Company filter ordered by
headcount. Sizes: `config/company_sizes.json` — 480 of the top-500 employers (87% of their jobs sized;
329 Wikipedia-verified), subsidiaries rolled up to parents, staffing firms flagged not sized. Exact-name
match is tried before suffix-stripped (else "Compass Group USA" → Compass the real-estate firm).

**Jobs** — 4 panels (Seattle FT, National FT, then the two internship panels labelled fallback). Row-per-job with
25-per-page pagination — `st.dataframe(on_select=...)` was unreliable and 500 buttons was slow.

**Tracker** — every application is editable (status incl. offer/rejected, notes, follow-up date). Each
record keeps a copy of the job's title/company/URL, and the export always ships jobs she applied to.

**Tools** — the ATS bookmarklet fills ONLY name, email, phone, LinkedIn, city, school, degree. It never
touches sponsorship, work authorization, EEO, salary or start date (substring matching once filled
"Ethnicity" with "Seattle"); those are shown as copy-ready answers. `smoke_test_pages.py` syntax-checks
it with node.

**To-Dos** — deleting marks an item `deleted` (hidden) instead of erasing it, because coffee-chat action
items are re-imported by text on every load. Every write goes through `save()`, which shows an error
instead of a traceback if GitHub is unreachable.

**Skills Gap / Skills Insights** — one analysis (`src/skills_insights.py`), computed at export from FULL
descriptions of 70+ jobs and stored in the deploy DB's `insights` table. Whole words (plural allowed),
Markdown escapes removed first. Current (2026-09-27, 3,543 descriptions): Excel 43%, data analysis 33%,
ERP 26%, data viz 18%, forecasting 17%, SQL 13%, Power BI 10%, Tableau 9%; communication 62%,
leadership 57%, stakeholder 51%. The older "Excel 70% / ERP 58%" figures were substring-inflated.

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
| Experience Fit | 15% | Appropriate level (4 yrs exp + MSCM, entry-to-mid) |
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
**National (searched):** SF, SJ, LA, NYC, Chicago, Austin, Dallas, Atlanta, Boston, Denver, Remote.
Other big metros (Houston, DC, Philadelphia, Charlotte, Minneapolis, …) still rank as big cities when
found, but aren't searched directly.

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
