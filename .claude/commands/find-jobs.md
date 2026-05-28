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

4. Export deploy DB and push to GitHub (updates live dashboard):
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   import sqlite3, os
   src_conn = sqlite3.connect('data/jobs.db')
   dst_conn = sqlite3.connect('data/jobs_deploy.db')
   dst_conn.execute('DROP TABLE IF EXISTS jobs')
   dst_conn.execute('''CREATE TABLE jobs (
       job_id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT,
       job_url TEXT, description TEXT, job_type TEXT, date_posted TEXT,
       salary_min REAL, salary_max REAL, salary_currency TEXT, source TEXT,
       search_term TEXT, search_category TEXT, scraped_at TEXT, score REAL,
       score_breakdown TEXT, scored_at TEXT, is_remote INTEGER DEFAULT 0,
       notified INTEGER DEFAULT 0, region TEXT DEFAULT 'seattle', dismissed INTEGER DEFAULT 0)''')
   rows = src_conn.execute('''
       SELECT job_id, title, company, location, job_url,
              SUBSTR(description, 1, 1000), job_type, date_posted,
              salary_min, salary_max, salary_currency, source, search_term,
              search_category, scraped_at, score, score_breakdown, scored_at,
              is_remote, notified, region, dismissed
       FROM jobs WHERE score >= 60 AND (dismissed IS NULL OR dismissed = 0)
       AND title IS NOT NULL AND title != \"\" AND company IS NOT NULL AND company != \"\"
   ''').fetchall()
   dst_conn.executemany('INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', rows)
   try:
       dst_conn.execute('DROP TABLE IF EXISTS applications')
       dst_conn.execute('''CREATE TABLE applications (job_id TEXT PRIMARY KEY, status TEXT, applied_date TEXT, notes TEXT, follow_up_date TEXT, updated_at TEXT)''')
       apps = src_conn.execute('SELECT * FROM applications').fetchall()
       if apps:
           dst_conn.executemany('INSERT OR REPLACE INTO applications VALUES (?,?,?,?,?,?)', apps)
   except: pass
   dst_conn.commit()
   dst_conn.close()
   src_conn.close()
   print(f'Exported {len(rows)} jobs ({os.path.getsize(\"data/jobs_deploy.db\")/1024/1024:.1f}MB)')
   "
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
