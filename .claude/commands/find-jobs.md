# Daily Job Search for Bhumika (MSCM)

Run the full pipeline: scrape → score → report → deploy dashboard.

## Instructions

1. Scrape and score:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.scraper import scrape_all_jobs
   from src.quick_scorer import score_all_unscored
   print('Scraping Indeed + LinkedIn (1 week)...')
   jobs = scrape_all_jobs(sites=['indeed', 'linkedin'], hours_old=168)
   print(f'Found {len(jobs)} new jobs')
   count = score_all_unscored()
   print(f'Quick-scored {count} jobs')
   "
   ```

2. Get top results:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.scraper import get_db
   conn = get_db()
   print('=== TOP SEATTLE ===')
   for r in conn.execute('SELECT score, title, company, location, salary_min, salary_max FROM jobs WHERE region=\"seattle\" AND job_type!=\"internship\" AND score>=75 AND (dismissed IS NULL OR dismissed=0) ORDER BY score DESC LIMIT 10').fetchall():
       sal = f' | \${int(r[4]/1000)}K-\${int(r[5]/1000)}K' if r[4] and r[5] else ''
       print(f'  [{int(r[0])}] {r[1]} @ {r[2]}{sal}')
   print()
   print('=== TOP NATIONAL ===')
   for r in conn.execute('SELECT score, title, company, location, salary_min, salary_max FROM jobs WHERE region=\"national\" AND job_type!=\"internship\" AND score>=70 AND (dismissed IS NULL OR dismissed=0) ORDER BY score DESC LIMIT 10').fetchall():
       sal = f' | \${int(r[4]/1000)}K-\${int(r[5]/1000)}K' if r[4] and r[5] else ''
       print(f'  [{int(r[0])}] {r[1]} @ {r[2]} — {r[3]}{sal}')
   print()
   print('=== INTERNSHIPS ===')
   for r in conn.execute('SELECT score, title, company, location, region FROM jobs WHERE job_type=\"internship\" AND score>=50 AND (dismissed IS NULL OR dismissed=0) ORDER BY score DESC LIMIT 5').fetchall():
       print(f'  [{int(r[0])}] {r[1]} @ {r[2]} ({r[4]})')
   conn.close()
   "
   ```

3. Present the report to the user organized by:
   - **Seattle & Area — Full-Time** (top priority)
   - **Seattle & Area — Internships**
   - **Rest of USA — Full-Time**
   - **Rest of USA — Internships**

4. Export deploy DB (trims jobs to FT 70+/intern 55+, copies all tracker tables — applications, coffee_chats, todos, interview_recs, star_stories):
   ```
   cd /Users/aniketsw/workspaces/mscm && python scripts/export_deploy_db.py
   ```

5. Push to GitHub (auto-deploys Streamlit Cloud):
   ```
   cd /Users/aniketsw/workspaces/mscm && git add data/jobs_deploy.db && git commit -m "Update deploy DB with latest jobs" && git push github main
   ```

## Key Files
- Config: `config/profile.json` (candidate profile + scoring weights)
- Queries: `config/search_queries.json` (search terms by category)
- Database: `data/jobs.db` (local, full, all jobs)
- Deploy DB: `data/jobs_deploy.db` (pushed to GitHub, read by Streamlit Cloud)
- Dashboard: `app.py` (Streamlit, reads from jobs_deploy.db)
