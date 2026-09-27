"""Fetch job descriptions for top LinkedIn postings, so Claude (Pass 2) can read them.

LinkedIn search results come back with NO description (JobSpy only fetches it with
one extra request per posting). That hides most of the Seattle panel from Pass 2:
on 2026-09-27, of 1,148 Seattle full-time jobs rated 80+, only 42 had a description.

Fetches serially with a 0.6-1.2s pause, and stops early if LinkedIn stops returning
descriptions (JobSpy swallows 429s and returns {}), so a block is reported, not hidden.
Rows that get a description are rescored with Pass 1 — its years / clearance /
sponsorship rules can now fire. One DB writer: don't run it during a scrape.

Usage: python scripts/backfill_linkedin_descriptions.py [--limit 300] [--region seattle|national|all] [--min-score 80]
"""

import argparse
import random
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from jobspy.linkedin import LinkedIn  # noqa: E402
from jobspy.model import DescriptionFormat  # noqa: E402

from src.quick_scorer import score_row  # noqa: E402

DB = ROOT / "data" / "jobs.db"
STOP_AFTER_EMPTY = 8  # consecutive empty responses ≈ LinkedIn is blocking us


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--region", default="seattle", choices=["seattle", "national", "all"])
    ap.add_argument("--min-score", type=float, default=80)
    a = ap.parse_args()

    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    region_sql = "" if a.region == "all" else "AND region = ?"
    params = [a.min_score] + ([] if a.region == "all" else [a.region]) + [a.limit]
    rows = conn.execute(f"""
        SELECT job_id, job_url, title, company, location, job_type, date_posted, scraped_at,
               is_remote, salary_min, score
        FROM jobs
        WHERE source = 'linkedin' AND job_type = 'fulltime' AND LENGTH(COALESCE(description, '')) < 50
          AND score >= ? {region_sql}
          AND json_extract(score_breakdown, '$.scorer') IS NULL
          AND COALESCE(date_posted, substr(scraped_at, 1, 10)) >= date('now', '-90 days')
        ORDER BY score DESC LIMIT ?""", params).fetchall()
    print(f"{len(rows)} LinkedIn postings to fetch ({a.region}, score ≥ {a.min_score:g})", flush=True)

    li = LinkedIn()
    li.scraper_input = SimpleNamespace(description_format=DescriptionFormat.MARKDOWN)
    got, empty_streak, updates, t0 = 0, 0, [], time.time()
    for i, (job_id, url, title, company, loc, jtype, posted, scraped, remote, sal, old) in enumerate(rows, 1):
        m = re.search(r"/jobs/view/(\d+)", url or "")
        if not m:
            continue
        time.sleep(random.uniform(0.6, 1.2))
        desc = (li._get_job_details(m.group(1)) or {}).get("description")
        if not desc:
            empty_streak += 1
            if empty_streak >= STOP_AFTER_EMPTY:
                print(f"  stopping: {STOP_AFTER_EMPTY} empty responses in a row — LinkedIn is likely "
                      f"blocking (fetched {i} so far)", flush=True)
                break
            continue
        empty_streak = 0
        got += 1
        desc = desc[:10000]
        score, breakdown = score_row(title, company, loc, desc, jtype, posted, scraped, remote, sal)
        updates.append((desc, score, breakdown, datetime.now().isoformat(), job_id))
        if i % 25 == 0:
            print(f"  {i}/{len(rows)} requested, {got} descriptions ({time.time()-t0:.0f}s)", flush=True)

    with conn:
        conn.executemany("UPDATE jobs SET description=?, score=?, score_breakdown=?, scored_at=? "
                         "WHERE job_id=?", updates)
    below = sum(1 for u in updates if u[1] < 70)
    conn.close()
    print(f"Done: requested {i if rows else 0}, got {got} descriptions in {time.time()-t0:.0f}s. "
          f"Rescored with Pass 1: {below} now below 70 (description revealed years/clearance/etc).")


if __name__ == "__main__":
    main()
