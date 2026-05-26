# MSCM Job Search System — User Guide

A complete daily job identification and career development system for Bhumika Choudhary's UW Foster MSCM journey.

---

## Table of Contents
1. [Daily Workflow (5 minutes)](#daily-workflow)
2. [Slash Commands Reference](#slash-commands)
3. [Understanding the Reports](#understanding-reports)
4. [Managing Your Job Search](#managing-search)
5. [Portfolio Projects](#portfolio-projects)
6. [Application Tracking](#application-tracking)
7. [Customization](#customization)
8. [Troubleshooting](#troubleshooting)

---

## Daily Workflow

Every morning (or whenever you want fresh results), open Claude Code in this workspace and run:

```
/find-jobs
```

That's it. The system will:
1. Scrape LinkedIn, Indeed, Google Jobs, and ZipRecruiter for new postings
2. Score each job against Bhumika's profile (0-100)
3. Generate a report organized into 4 sections:
   - **Seattle & Area — Full-Time** (highest priority)
   - **Seattle & Area — Internships** (for CPT during MSCM)
   - **Rest of USA — Full-Time** (backup options)
   - **Rest of USA — Internships** (broader net)
4. Show salary comparisons against the MSCM class average ($108K)
5. Highlight top matches with reasons why they fit

### What Happens Automatically
- A cron job runs weekdays at 8:23 AM (when Claude Code is open)
- Previously seen jobs are deduplicated (won't show duplicates)
- All results are saved to `data/jobs.db` for historical tracking

---

## Slash Commands

| Command | What It Does |
|---------|-------------|
| `/find-jobs` | Full pipeline: scrape → score → report |
| `/job-stats` | Show database statistics and trends |
| `/add-search` | Add a new search term (e.g., "add data analyst") |
| `/generate-projects` | Create portfolio projects from skill gaps |
| `/track` | View/update application status tracker |

### Usage Examples

**Add a new role to search for:**
```
/add-search
> "supply chain data scientist"
```

**Check how many jobs you've found:**
```
/job-stats
```

**Generate projects to build your resume:**
```
/generate-projects
```

**Mark a job as applied:**
```
/track
> "Mark the Amazon Supply Chain Analyst as applied"
```

---

## Understanding Reports

### Score Breakdown (0-100)
Each job is scored across 7 dimensions:

| Dimension | Weight | What It Means |
|-----------|--------|---------------|
| Role Relevance | 25% | Does the title/description match SCM/ops/PM roles? |
| Skills Match | 20% | How many of Bhumika's skills are relevant? |
| Experience Fit | 15% | Right level? (3yr exp = entry-to-mid is ideal) |
| Location Match | 15% | Seattle/WA area or remote? |
| Company Tier | 10% | Amazon, Boeing, Costco, etc.? |
| Growth Potential | 10% | Career trajectory opportunity? |
| Visa Friendliness | 5% | Large company likely to sponsor OPT/H1B? |

### Score Tiers
- **90-100: Excellent** — Apply immediately, strong fit
- **75-89: Strong** — Highly relevant, worth applying
- **60-74: Good** — Solid option, review description carefully
- **50-59: Consider** — Partially relevant, stretch opportunity

### Report Files
After each run, reports are saved to:
- `output/report-YYYY-MM-DD.md` — Daily markdown report
- `output/jobs-YYYY-MM-DD.csv` — Full CSV export (all scored jobs)
- `output/skills-gap-YYYY-MM-DD.md` — Skills gap analysis

---

## Managing Your Job Search

### Adjusting Search Terms
Edit `config/search_queries.json` to add/remove search queries:
```json
{
  "search_term": "your new search term",
  "category": "primary"  // or "secondary" or "stretch"
}
```

### Adjusting Target Locations
Edit `config/profile.json` → `search_preferences`:
- `locations_seattle`: Cities near UW (highest priority)
- `locations_national`: Other major metros + Remote

### Changing Scoring Weights
Edit `config/profile.json` → `scoring_weights` to prioritize what matters most.

### Widening the Search Window
By default, the system looks at jobs posted in the last 24 hours. To look further back:
```bash
cd /Users/aniketsw/workspaces/mscm
python -c "from src.scraper import scrape_all_jobs; scrape_all_jobs(hours_old=72)"
```

---

## Portfolio Projects

The system auto-identifies skills gaps by analyzing what top-scoring job listings request vs. what Bhumika already has.

### How It Works
1. Run `/generate-projects`
2. The system analyzes 50+ top job descriptions
3. Identifies commonly requested skills (Python, Tableau, SAP, etc.)
4. Generates step-by-step project guides in `projects/` directory

### Available Projects
Each project includes:
- **Full beginner-friendly walkthrough** (no prior experience needed)
- **Expected duration** (1-2 weeks each)
- **Resume line** (copy-paste when done)
- **Interview talking points**
- **Free tools only** (no paid software required)

### Current Project Templates
1. **Supply Chain Demand Forecasting with Python** — ML model, pandas, scikit-learn
2. **Supply Chain KPI Dashboard in Tableau** — Interactive viz, free Tableau Public
3. **Procurement Spend Analytics in Power BI** — DAX, data modeling
4. **SAP S/4HANA Supply Chain Simulation** — ERP navigation, MM/PP modules

---

## Application Tracking

### Updating Status
Tell Claude: "Mark [job] at [company] as [status]"

Valid statuses:
- `new` — Just identified, not acted on
- `applied` — Application submitted
- `interviewing` — In interview process
- `offer` — Received offer
- `rejected` — Didn't get it
- `skipped` — Decided not to apply

### Setting Follow-ups
"Set follow-up for [job] on [date]" — Claude will remind you when it's due.

### Viewing Pipeline
`/track` shows:
- Status summary (how many in each stage)
- Follow-ups due today
- All applied jobs awaiting response
- Jobs in interview process

---

## Customization

### Add a New Target Company
Edit `config/profile.json` → `target_companies` → add to `tier1_seattle_scm` or `tier2_national`.

### Change Salary Expectations
Edit `config/profile.json` → `search_preferences` → `min_salary`.

### Exclude Certain Roles
Edit `config/profile.json` → `search_preferences` → `exclude_terms` (e.g., add "warehouse associate" if getting irrelevant results).

---

## Troubleshooting

### "No new jobs found"
- The system only shows NEW jobs (not previously seen). If you ran it recently, there may genuinely be no new postings.
- Try widening the search: increase `hours_old` to 72 or 168 (1 week).

### Scoring not working
- Scoring runs inline within Claude Code (uses your corporate Claude access).
- If Claude Code is working (you're reading this!), scoring will work too.

### Too many irrelevant results
- Add exclusion terms to `config/profile.json` → `exclude_terms`
- Adjust scoring weights to penalize poor matches harder

### Want to start fresh
```bash
rm data/jobs.db  # Delete all historical data
```

---

## System Architecture

```
You say "/find-jobs"
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  JobSpy Scraper │────▶│  SQLite Database  │
│  (4 job boards) │     │  (dedup + store)  │
└─────────────────┘     └────────┬─────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  Claude Inline Scoring  │
                    │  (7 dimensions, 0-100)  │
                    └────────────┬───────────┘
                                 │
                    ┌────────────▼───────────┐
                    │     4-Panel Report      │
                    │  Seattle FT | Intern    │
                    │  National FT | Intern   │
                    └────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
     Skills Gap Report    Project Generator    Application Tracker
```
