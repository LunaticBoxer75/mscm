# MSCM Job Search Pipeline

Daily automated job search for **Bhumika Choudhary** — incoming UW Foster Master of Supply Chain Management (MSCM) student, currently Global SME at Uber Risk & Compliance.

> **Career plan:** A full Jul–Dec 2026 upskilling + job-search plan lives in [`career-plan/`](career-plan/) — start at [`career-plan/INDEX.md`](career-plan/INDEX.md). It's a browsable binder (strategy, skills, 10 portfolio projects, networking templates, reading list, consulting fit-test, edge track) plus 24 printable weekly pages (`career-plan/weekly/`). Skill ordering there is evidence-based (from analyzing this repo's scraped JDs) and supersedes the older 90-Day PM Track doc.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Scoring uses AWS Bedrock (Claude via your corporate AWS credentials)
# Ensure you have valid AWS credentials (ada credentials / SSO)

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

## Architecture

```
config/profile.json          ← Candidate profile, target roles, scoring weights
config/search_queries.json   ← Search terms by category (primary/secondary/stretch)
config/firebase-credentials.json ← Firebase service account (gitignored)
src/scraper.py              ← JobSpy-based multi-board scraper (Seattle + National, FT + Intern)
src/scorer.py               ← Claude inline scoring (7 dimensions, 0-100, batch mode)
src/reporter.py             ← 4-panel report (Seattle FT/Intern, National FT/Intern) + skills gap + trends
src/projects.py             ← Auto-generate portfolio projects from skill gaps
src/referrals.py            ← LinkedIn referral link generator for top companies
src/tracker.py              ← Application status tracking with follow-ups
src/firebase_db.py          ← Firestore sync (auto-pushes on every write)
src/pipeline.py             ← Orchestrator (full pipeline or individual steps)
app.py                      ← Streamlit dashboard (deployed on Streamlit Cloud)
data/jobs.db                ← SQLite (local cache, Firestore is source of truth)
output/report-YYYY-MM-DD.md ← Daily reports
projects/                   ← Auto-generated portfolio project guides
```

## Data Flow

```
/find-jobs in Claude Code
    → Scrapes 4 job boards (28 queries × 17 locations)
    → Quick-scores ALL jobs (rule-based triage via src/quick_scorer.py)
    → AI-scores jobs with quick-score 40+ (Claude inline, reads full description)
    → Writes to SQLite (local cache) AND Firestore (cloud)
    → Streamlit Cloud dashboard auto-reflects new data on refresh
```

## Scoring Architecture (Two-Pass)

1. **Pass 1 — Quick Scorer** (`src/quick_scorer.py`): Rule-based triage applied to ALL jobs immediately after scraping. Uses title keywords, seniority detection, years-of-experience extraction from description, and location matching. Kills obvious irrelevant jobs (retail, medical, etc.) at score <30. Fast — handles 1000+ jobs in seconds.

2. **Pass 2 — AI Scorer** (Claude inline): Applied to jobs scoring 40+ from Pass 1 (~300-500 relevant ones). Claude reads the full job description and scores with nuance (e.g., "2+ required, 5+ preferred" vs "must have 9+ years"). Returns detailed reasoning, highlights, and red flags.

This ensures: every job gets scored (no invisible unscored entries), irrelevant jobs don't waste AI time, and relevant jobs get proper contextual evaluation.

## Dashboard

**Hosted on Streamlit Cloud** — same `app.py` runs locally and deployed.
- GitHub repo: https://github.com/LunaticBoxer75/mscm (private)
- Reads from: Google Firestore (project: mscm-5591c)
- Access: Invite-only via Streamlit Cloud sharing settings

### Tabs
1. **Job Listings** — 4-panel view (Seattle FT/Intern, National FT/Intern) with row selection
2. **Application Tracker** — Pipeline status, follow-up reminders
3. **Referrals** — LinkedIn search links for employees at top companies
4. **Skills Gap** — What top jobs request vs what Bhumika has
5. **Projects** — Portfolio project guides to fill skill gaps
6. **Export** — Download jobs CSV, applications CSV

## Features

- **4-Panel Dashboard:** Seattle FT, Seattle Internships, National FT, National Internships
- **7-Dimension AI Scoring:** Role relevance, skills match, experience fit, location, company tier, growth, visa
- **LinkedIn Referral Finder:** Auto-generates search links for employees, recruiters, alumni at target companies
- **Skills Gap Analysis:** What's commonly requested that Bhumika doesn't have yet
- **Portfolio Project Generator:** Builds complete beginner-friendly projects with runnable code
- **Application Tracker:** Track applied/interviewing/offer/rejected with follow-up reminders
- **Salary Benchmarking:** Compares found salaries against MSCM class average ($108K)
- **Firebase Sync:** Every scrape/score/track action auto-syncs to Firestore
- **Internship Detection:** Titles with "intern"/"co-op"/"new grad" auto-classified correctly

## Job Boards Scraped

- Indeed (primary — most reliable, no rate limits)
- LinkedIn (secondary — works but rate-limited for large batches)
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

**Seattle & Area (priority):** Seattle, Bellevue, Kirkland, Redmond, Tacoma, Everett
**National:** SF, SJ, LA, NYC, Chicago, Austin, Dallas, Atlanta, Boston, Denver, Remote

## Key Dependencies

- `python-jobspy` — Multi-board job scraping (MIT, 3.5k stars)
- `anthropic[bedrock]` — Claude via AWS Bedrock (uses corporate AWS credentials)
- `pandas` — Data manipulation
- `rich` — Terminal output formatting
- `streamlit` — Web dashboard (local + Streamlit Cloud)
- `firebase-admin` — Google Firestore (primary database)

## Notes

- Resume PDF at: `/Users/aniketsw/Downloads/Bhumika_Choudhary_Resume.pdf`
- Bhumika's LinkedIn: `bhummika`
- Program is STEM-designated (3-year OPT eligibility)
- Program: June 2026 — May/June 2027 (1-year, STEM-designated)
- Scoring uses Claude Sonnet via Bedrock (us-west-2, model: us.anthropic.claude-sonnet-4-20250514-v1:0)
- AWS auth: uses default credential chain (ada / SSO)
- Firebase project: `mscm-5591c`
- GitHub: `git@github.com:LunaticBoxer75/mscm.git` (push via SSH)
- Internship postings are seasonal (summer: Aug-Oct, winter: Sep-Nov)
