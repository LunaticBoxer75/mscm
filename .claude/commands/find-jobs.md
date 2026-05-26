# Daily Job Search for Bhumika (MSCM)

Run the full MSCM job search pipeline: scrape job boards, score against Bhumika's profile, and generate a ranked report.

## Instructions

1. First, ensure dependencies are installed:
   ```
   cd /Users/aniketsw/workspaces/mscm && pip install -r requirements.txt
   ```

2. Run the full pipeline:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -m src.pipeline
   ```

3. If the pipeline completes, read the latest report from `output/` and present the top matches to the user in a clean summary table.

4. If scraping fails (rate limits, network issues), try running with `--score-only` to score any previously scraped but unscored jobs:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -m src.pipeline score
   ```

5. After presenting results, ask if the user wants to:
   - Adjust search criteria (edit `config/search_queries.json`)
   - See more details on specific jobs
   - Export to CSV
   - Expand search window (e.g., last 72h instead of 24h)

## Key Files
- Config: `config/profile.json` (candidate profile + scoring weights)
- Queries: `config/search_queries.json` (search terms by category)
- Output: `output/report-YYYY-MM-DD.md` (daily reports)
- Database: `data/jobs.db` (SQLite - all scraped jobs + scores)
