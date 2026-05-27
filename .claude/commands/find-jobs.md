# Daily Job Search for Bhumika (MSCM)

Run the full MSCM job search pipeline: scrape job boards, score against Bhumika's profile, and generate a ranked report.

## Instructions

1. Ensure dependencies are installed:
   ```
   cd /Users/aniketsw/workspaces/mscm && pip install -q -r requirements.txt 2>/dev/null
   ```

2. Run the scraper to get new jobs:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.scraper import scrape_all_jobs
   jobs = scrape_all_jobs(sites=['indeed', 'linkedin', 'google'], hours_old=24)
   print(f'Found {len(jobs)} new jobs')
   "
   ```

3. Get unscored jobs and score them inline. Run:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.scorer import score_all_pending, batch_score_prompt
   import json
   jobs = score_all_pending(limit=30)
   if jobs:
       prompt = batch_score_prompt(jobs)
       print('SCORING_PROMPT_START')
       print(prompt)
       print('SCORING_PROMPT_END')
       print(f'JOBS_DATA: {json.dumps([{\"job_id\": j[\"job_id\"], \"title\": j[\"title\"], \"company\": j[\"company\"]} for j in jobs])}')
   else:
       print('NO_JOBS_TO_SCORE')
   "
   ```

4. **IMPORTANT: Score ALL jobs yourself.** Never leave unscored jobs. For bulk scoring, use title-based quick scoring for obviously irrelevant jobs (retail, healthcare, food service → score 10-20) and properly score the relevant ones. Always penalize:
   - Director/VP/Principal/Chief → score max 35 (requires 10+ years)
   - "10+ years" or "15+ years" in description → score max 40
   - "Senior Manager" → score max 60 (stretch)
   
   Then save the scores:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.scorer import parse_batch_scores, update_job_score
   import json
   # Paste your JSON scores here as a string
   scores_json = '''YOUR_SCORES_JSON_HERE'''
   scores = json.loads(scores_json)
   for s in scores:
       update_job_score(s['job_id'], s['score'], s)
   print(f'Saved {len(scores)} scores')
   "
   ```

5. Generate and display the report:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.reporter import generate_daily_report, get_stats
   import json
   report = generate_daily_report(min_score=50)
   stats = get_stats()
   print(report)
   print('---STATS---')
   print(json.dumps(stats, indent=2))
   "
   ```

6. Present the report to the user organized by:
   - **Seattle & Area — Full-Time** (top priority)
   - **Seattle & Area — Internships**
   - **Rest of USA — Full-Time**
   - **Rest of USA — Internships**

7. After presenting, check if skills gap analysis would be useful:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.reporter import generate_skills_gap_report
   print(generate_skills_gap_report())
   "
   ```

8. Sync everything to Firebase (ensures cloud is up-to-date):
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.firebase_db import sync_full_db, is_available
   if is_available():
       result = sync_full_db()
       print(f'Firebase synced: {result[\"jobs\"]} jobs, {result[\"applications\"]} applications')
   else:
       print('Firebase not configured — skipping cloud sync')
   "
   ```

## Key Files
- Config: `config/profile.json` (candidate profile + scoring weights)
- Queries: `config/search_queries.json` (search terms by category)
- Output: `output/report-YYYY-MM-DD.md` (daily reports)
- Database: `data/jobs.db` (SQLite - all scraped jobs + scores)
- Cloud: Firebase project `mscm-5591c` (auto-synced)
