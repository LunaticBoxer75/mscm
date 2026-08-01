"""Export the deploy DB: top jobs + all auxiliary tracker tables.

Run after scraping/scoring to refresh data/jobs_deploy.db for the dashboard.
Keeps full-time jobs scoring 70+ and internships 55+, plus all tracker tables
(applications, coffee_chats, todos, interview_recs, star_stories).
"""

import sqlite3
import os
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
SRC = DATA / "jobs.db"
DST = DATA / "jobs_deploy.db"

AUX_TABLES = ["applications", "coffee_chats", "todos", "interview_recs", "star_stories"]


def main():
    src = sqlite3.connect(SRC)
    dst = sqlite3.connect(DST)

    # Jobs (trimmed)
    dst.execute("DROP TABLE IF EXISTS jobs")
    dst.execute("""CREATE TABLE jobs (
        job_id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT,
        job_url TEXT, description TEXT, job_type TEXT, date_posted TEXT,
        salary_min REAL, salary_max REAL, salary_currency TEXT, source TEXT,
        search_term TEXT, search_category TEXT, scraped_at TEXT, score REAL,
        score_breakdown TEXT, scored_at TEXT, is_remote INTEGER DEFAULT 0,
        notified INTEGER DEFAULT 0, region TEXT DEFAULT 'seattle', dismissed INTEGER DEFAULT 0)""")
    rows = src.execute("""
        SELECT job_id, title, company, location, job_url,
               SUBSTR(description, 1, 800), job_type, date_posted,
               salary_min, salary_max, salary_currency, source, search_term,
               search_category, scraped_at, score, score_breakdown, scored_at,
               is_remote, notified, region, dismissed
        FROM jobs WHERE (dismissed IS NULL OR dismissed = 0)
        AND title IS NOT NULL AND title != '' AND company IS NOT NULL AND company != ''
        AND ((job_type='internship' AND score>=55) OR (job_type!='internship' AND score>=70))
    """).fetchall()
    dst.executemany("INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    # Auxiliary tracker tables — copy verbatim
    for tbl in AUX_TABLES:
        schema = src.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tbl,)
        ).fetchone()
        if not schema or not schema[0]:
            continue
        dst.execute(f"DROP TABLE IF EXISTS {tbl}")
        dst.execute(schema[0])
        trows = src.execute(f"SELECT * FROM {tbl}").fetchall()
        if trows:
            placeholders = ",".join(["?"] * len(trows[0]))
            dst.executemany(f"INSERT INTO {tbl} VALUES ({placeholders})", trows)

    dst.commit()
    dst.execute("VACUUM")
    dst.close()
    src.close()

    size_mb = os.path.getsize(DST) / 1024 / 1024
    print(f"Exported {len(rows)} jobs + aux tables ({size_mb:.1f}MB)")


if __name__ == "__main__":
    main()
