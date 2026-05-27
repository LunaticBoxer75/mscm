"""Job scraper using JobSpy to aggregate listings from multiple boards."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs

CONFIG_DIR = Path(__file__).parent.parent / "config"
DATA_DIR = Path(__file__).parent.parent / "data"


def load_config():
    with open(CONFIG_DIR / "profile.json") as f:
        profile = json.load(f)
    with open(CONFIG_DIR / "search_queries.json") as f:
        queries = json.load(f)
    return profile, queries


def get_db():
    DATA_DIR.mkdir(exist_ok=True)
    db_path = DATA_DIR / "jobs.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            job_url TEXT,
            description TEXT,
            job_type TEXT,
            date_posted TEXT,
            salary_min REAL,
            salary_max REAL,
            salary_currency TEXT,
            source TEXT,
            search_term TEXT,
            search_category TEXT,
            scraped_at TEXT,
            score REAL,
            score_breakdown TEXT,
            scored_at TEXT,
            is_remote INTEGER DEFAULT 0,
            notified INTEGER DEFAULT 0,
            region TEXT DEFAULT 'seattle'
        )
    """)
    # Add region column if upgrading from old schema
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN region TEXT DEFAULT 'seattle'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    return conn


def generate_job_id(row):
    """Create a stable ID from job URL or title+company combo."""
    if pd.notna(row.get("job_url")) and row["job_url"]:
        return str(hash(row["job_url"]))
    return str(hash(f"{row.get('title', '')}-{row.get('company', '')}-{row.get('location', '')}"))


def scrape_all_jobs(sites=None, hours_old=None, region=None):
    """Scrape jobs from all configured queries and return new (unseen) jobs.

    region: 'seattle', 'national', or None (both).
    """
    profile, queries = load_config()
    prefs = profile["search_preferences"]

    if sites is None:
        sites = ["indeed", "linkedin", "google", "zip_recruiter"]
    if hours_old is None:
        hours_old = prefs["hours_old"]

    locations_seattle = prefs["locations_seattle"]
    locations_national = prefs["locations_national"]

    if region == "seattle":
        location_groups = [("seattle", locations_seattle)]
    elif region == "national":
        location_groups = [("national", locations_national)]
    else:
        location_groups = [("seattle", locations_seattle), ("national", locations_national)]

    job_types_to_scrape = prefs["job_types"]

    conn = get_db()
    all_new_jobs = []

    for region_tag, locations in location_groups:
        for jtype in job_types_to_scrape:
            for query in queries["queries"]:
                search_term = query["search_term"]
                category = query["category"]

                for location in locations:
                    if location == "Remote":
                        continue

                    try:
                        jobs_df = scrape_jobs(
                            site_name=sites,
                            search_term=search_term,
                            location=location,
                            results_wanted=prefs["results_per_search"],
                            hours_old=hours_old,
                            country_indeed=prefs["country"],
                            job_type=jtype,
                            description_format="markdown",
                            verbose=0,
                        )
                    except Exception as e:
                        print(f"  [!] Error scraping '{search_term}' ({jtype}) in {location}: {e}")
                        continue

                    if jobs_df is None or jobs_df.empty:
                        continue

                    for _, row in jobs_df.iterrows():
                        job_id = generate_job_id(row)

                        existing = conn.execute(
                            "SELECT job_id FROM jobs WHERE job_id = ?", (job_id,)
                        ).fetchone()
                        if existing:
                            continue

                        is_remote = 1 if row.get("is_remote") else 0
                        title_str = str(row.get("title", "")) if pd.notna(row.get("title")) else ""
                        company_str = str(row.get("company", "")) if pd.notna(row.get("company")) else ""

                        # Skip entries with no title or company
                        if not title_str or not company_str:
                            continue

                        # Override job_type if title clearly indicates intern/co-op
                        effective_type = jtype
                        if any(kw in title_str.lower() for kw in ["intern", "co-op", "coop", "new grad"]):
                            effective_type = "internship"

                        job_data = {
                            "job_id": job_id,
                            "title": title_str,
                            "company": company_str,
                            "location": str(row.get("location", "")) if pd.notna(row.get("location")) else "",
                            "job_url": str(row.get("job_url", "")) if pd.notna(row.get("job_url")) else "",
                            "description": str(row.get("description", ""))[:10000] if pd.notna(row.get("description")) else "",
                            "job_type": effective_type,
                            "date_posted": str(row.get("date_posted", "")),
                            "salary_min": float(row["min_amount"]) if pd.notna(row.get("min_amount")) else None,
                            "salary_max": float(row["max_amount"]) if pd.notna(row.get("max_amount")) else None,
                            "salary_currency": str(row.get("currency", "USD")),
                            "source": str(row.get("site", "")),
                            "search_term": search_term,
                            "search_category": category,
                            "scraped_at": datetime.now().isoformat(),
                            "is_remote": is_remote,
                            "region": region_tag,
                        }

                        conn.execute("""
                            INSERT OR IGNORE INTO jobs
                            (job_id, title, company, location, job_url, description, job_type,
                             date_posted, salary_min, salary_max, salary_currency, source,
                             search_term, search_category, scraped_at, is_remote, region)
                            VALUES (:job_id, :title, :company, :location, :job_url, :description,
                                    :job_type, :date_posted, :salary_min, :salary_max,
                                    :salary_currency, :source, :search_term, :search_category,
                                    :scraped_at, :is_remote, :region)
                        """, job_data)

                        all_new_jobs.append(job_data)

    conn.commit()
    conn.close()

    # Auto-sync new jobs to Firebase
    if all_new_jobs:
        try:
            from .firebase_db import sync_jobs
            sync_jobs(all_new_jobs)
        except Exception:
            pass

    return all_new_jobs


def get_unscored_jobs(limit=50):
    """Fetch jobs that haven't been scored yet."""
    conn = get_db()
    cursor = conn.execute("""
        SELECT * FROM jobs
        WHERE score IS NULL
        ORDER BY scraped_at DESC
        LIMIT ?
    """, (limit,))
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


def update_job_score(job_id, score, breakdown):
    """Update a job's score in the database."""
    conn = get_db()
    conn.execute("""
        UPDATE jobs SET score = ?, score_breakdown = ?, scored_at = ?
        WHERE job_id = ?
    """, (score, json.dumps(breakdown), datetime.now().isoformat(), job_id))
    conn.commit()
    conn.close()

    # Auto-sync score to Firebase
    try:
        from .firebase_db import sync_scores
        sync_scores([{"job_id": job_id, "score": score, "score_breakdown": breakdown}])
    except Exception:
        pass


def get_top_jobs(min_score=60, limit=20):
    """Get top-scored jobs."""
    conn = get_db()
    cursor = conn.execute("""
        SELECT * FROM jobs
        WHERE score >= ?
        ORDER BY score DESC
        LIMIT ?
    """, (min_score, limit))
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


if __name__ == "__main__":
    from rich.console import Console
    console = Console()
    console.print("[bold]Scraping jobs...[/bold]")
    new_jobs = scrape_all_jobs()
    console.print(f"[green]Found {len(new_jobs)} new jobs[/green]")
