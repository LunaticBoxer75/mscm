# Backfill Jobs (4 months)

Run a deep scrape to catch all jobs from the last 4 months. Use this once to populate the database, then rely on daily /find-jobs for new listings.

## Instructions

1. Run the backfill scrape (this takes 10-20 minutes):
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.scraper import scrape_all_jobs
   # 4 months = ~2880 hours
   jobs = scrape_all_jobs(hours_old=2880)
   print(f'Backfill complete: {len(jobs)} new jobs found')
   "
   ```

2. Quick-score all new jobs:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.quick_scorer import score_all_unscored
   count = score_all_unscored()
   print(f'Quick-scored {count} jobs')
   "
   ```

3. AI-score the promising ones (40+):
   Get jobs with quick-score 40+ and score them with Claude inline (follow /find-jobs step 4).

4. Sync to Firebase:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.firebase_db import sync_full_db
   result = sync_full_db()
   print(f'Synced {result[\"jobs\"]} jobs')
   "
   ```
