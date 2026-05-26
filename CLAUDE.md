# MSCM Job Search Pipeline

Daily automated job search for **Bhumika Choudhary** — incoming UW Foster Master of Supply Chain Management (MSCM) student, currently Global SME at Uber Risk & Compliance.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (for scoring)
export ANTHROPIC_API_KEY=your_key

# Run full pipeline (scrape → score → report)
python -m src.pipeline

# Or run individual steps
python -m src.pipeline scrape    # Just scrape
python -m src.pipeline score     # Just score pending
python -m src.pipeline report    # Just generate report
```

## Slash Commands

- `/find-jobs` — Run full pipeline and present ranked results
- `/job-stats` — Show database statistics
- `/add-search` — Add a new search query

## Architecture

```
config/profile.json          ← Candidate profile, target roles, scoring weights
config/search_queries.json   ← Search terms by category (primary/secondary/stretch)
src/scraper.py              ← JobSpy-based multi-board scraper
src/scorer.py               ← Claude AI scoring (7 dimensions, 0-100)
src/reporter.py             ← Markdown + CSV report generation
src/pipeline.py             ← Orchestrator (full pipeline or individual steps)
data/jobs.db                ← SQLite database (all jobs + scores + history)
output/report-YYYY-MM-DD.md ← Daily reports
```

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

**Primary:** Supply Chain Analyst, Operations Analyst, SC Risk Analyst, Procurement, Demand Planning, Logistics  
**Secondary:** Program Manager, TPM, Process Improvement, Business Ops, Compliance  
**Stretch:** SC Manager, Strategic Sourcing, S&OP, Inventory Analyst

## Target Location

Seattle, WA metro area (Seattle, Bellevue, Redmond, Tacoma) + Remote positions.  
Search radius: 50 miles.

## Key Dependencies

- `python-jobspy` — Multi-board job scraping (MIT, 3.5k stars)
- `anthropic` — Claude API for AI scoring
- `pandas` — Data manipulation
- `rich` — Terminal output formatting
- `sqlite3` — Local dedup and history database

## Notes

- Resume PDF at: `/Users/aniketsw/Downloads/Bhumika_Choudhary_Resume.pdf`
- Bhumika's LinkedIn: `bhummika`
- Program is STEM-designated (3-year OPT eligibility)
- Program starts ~September 2026
- Scoring uses Claude Sonnet for cost efficiency (~$0.01-0.03 per job scored)
