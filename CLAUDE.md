# MSCM Job Search Pipeline

Daily automated job search for **Bhumika Choudhary** — incoming UW Foster Master of Supply Chain Management (MSCM) student, currently Global SME at Uber Risk & Compliance.

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
src/scraper.py              ← JobSpy-based multi-board scraper (Seattle + National, FT + Intern)
src/scorer.py               ← Claude inline scoring (7 dimensions, 0-100, batch mode)
src/reporter.py             ← 4-panel report (Seattle FT/Intern, National FT/Intern) + skills gap + trends
src/projects.py             ← Auto-generate portfolio projects from skill gaps
src/pipeline.py             ← Orchestrator (full pipeline or individual steps)
data/jobs.db                ← SQLite database (all jobs + scores + history)
output/report-YYYY-MM-DD.md ← Daily reports
output/skills-gap-*.md      ← Skills gap analysis
projects/                   ← Auto-generated project guides (beginner-friendly)
```

## Features

- **4-Panel Dashboard:** Seattle FT, Seattle Internships, National FT, National Internships
- **7-Dimension AI Scoring:** Role relevance, skills match, experience fit, location, company tier, growth, visa
- **Skills Gap Analysis:** What's commonly requested that Bhumika doesn't have yet
- **Portfolio Project Generator:** Auto-creates beginner-friendly project guides to fill skill gaps
- **Application Tracker:** Track applied/interviewing/offer/rejected with follow-up reminders
- **Weekly Trends:** Which roles are heating up / cooling down
- **Salary Benchmarking:** Compares found salaries against MSCM class average ($108K)

## Job Boards Scraped

- LinkedIn
- Indeed  
- Google Jobs
- ZipRecruiter

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

Seattle, WA metro area (Seattle, Bellevue, Redmond, Tacoma) + Remote positions.  
Search radius: 50 miles.

## Key Dependencies

- `python-jobspy` — Multi-board job scraping (MIT, 3.5k stars)
- `anthropic[bedrock]` — Claude via AWS Bedrock (uses corporate AWS credentials)
- `pandas` — Data manipulation
- `rich` — Terminal output formatting
- `sqlite3` — Local dedup and history database

## Notes

- Resume PDF at: `/Users/aniketsw/Downloads/Bhumika_Choudhary_Resume.pdf`
- Bhumika's LinkedIn: `bhummika`
- Program is STEM-designated (3-year OPT eligibility)
- Program starts ~September 2026
- Scoring uses Claude Sonnet via Bedrock (us-west-2, model: us.anthropic.claude-sonnet-4-20250514-v1:0)
- AWS auth: uses default credential chain (ada / SSO)
