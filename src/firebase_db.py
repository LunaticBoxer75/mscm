"""Firebase Firestore integration for MSCM job search.

Architecture: Stores daily report documents (not individual jobs).
Each document contains the top jobs for that day as a JSON array.
This keeps read/write counts minimal (1 write per /find-jobs run,
1 read per dashboard page load).

Local SQLite remains the primary database for all jobs.
Firestore is the cloud-accessible layer for the dashboard.
"""

import json
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"
FIREBASE_CREDS_PATH = CONFIG_DIR / "firebase-credentials.json"

_db = None
_initialized = False


def _init_firebase():
    global _db, _initialized
    if _initialized:
        return _db
    _initialized = True
    if not FIREBASE_CREDS_PATH.exists():
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        cred = credentials.Certificate(str(FIREBASE_CREDS_PATH))
        firebase_admin.initialize_app(cred)
        _db = firestore.client()
        return _db
    except Exception as e:
        print(f"[Firebase] Init failed: {e}")
        return None


def is_available():
    return _init_firebase() is not None


def publish_daily_report(jobs_data, date_str=None):
    """Publish today's top jobs as a single Firestore document.

    jobs_data: list of job dicts (already scored and filtered)
    """
    db = _init_firebase()
    if not db:
        return False

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Sanitize data — remove None values, limit fields
    clean_jobs = []
    for job in jobs_data:
        clean = {}
        for key in ["job_id", "title", "company", "location", "job_url", "job_type",
                    "score", "region", "date_posted", "salary_min", "salary_max",
                    "score_breakdown", "source"]:
            val = job.get(key)
            if val is not None:
                clean[key] = val
            else:
                clean[key] = ""
        # Parse score_breakdown if it's a string
        if isinstance(clean.get("score_breakdown"), str):
            try:
                clean["score_breakdown"] = json.loads(clean["score_breakdown"])
            except (json.JSONDecodeError, TypeError):
                clean["score_breakdown"] = {}
        clean_jobs.append(clean)

    doc_ref = db.collection("reports").document(date_str)
    doc_ref.set({
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "job_count": len(clean_jobs),
        "jobs": clean_jobs,
    })
    return True


def get_daily_report(date_str=None):
    """Fetch today's report from Firestore. Returns list of job dicts."""
    db = _init_firebase()
    if not db:
        return []

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    doc_ref = db.collection("reports").document(date_str)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("jobs", [])
    return []


def get_latest_report():
    """Fetch the most recent report (in case today's hasn't been generated yet)."""
    db = _init_firebase()
    if not db:
        return [], ""

    reports_ref = db.collection("reports")
    docs = reports_ref.order_by("date", direction="DESCENDING").limit(1).stream()

    for doc in docs:
        data = doc.to_dict()
        return data.get("jobs", []), data.get("date", "")

    return [], ""


def publish_applications(applications):
    """Publish application tracker state as a single document."""
    db = _init_firebase()
    if not db:
        return False

    doc_ref = db.collection("state").document("applications")
    doc_ref.set({
        "updated_at": datetime.now().isoformat(),
        "applications": applications,
    })
    return True


def get_applications():
    """Fetch application tracker state."""
    db = _init_firebase()
    if not db:
        return []

    doc_ref = db.collection("state").document("applications")
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get("applications", [])
    return []


def sync_from_sqlite(min_score=60, limit=2000):
    """Sync top jobs from SQLite to Firestore as a single master document.

    Stores all jobs scoring >= min_score (up to limit) in one doc.
    Firestore max doc size is 1MB — ~2000 jobs with key fields fits.
    """
    from .scraper import get_db
    import sqlite3

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT job_id, title, company, location, job_url, job_type,
               score, region, date_posted, salary_min, salary_max,
               score_breakdown, source
        FROM jobs
        WHERE score IS NOT NULL AND score >= ?
        AND title IS NOT NULL AND title != '' AND company IS NOT NULL AND company != ''
        AND (dismissed IS NULL OR dismissed = 0)
        ORDER BY score DESC
        LIMIT ?
    """, (min_score, limit))
    jobs = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not jobs:
        return {"synced": False, "reason": "No scored jobs"}

    # Publish as daily report + update the master doc
    success = publish_daily_report(jobs)

    # Also update master doc (all-time best jobs)
    db = _init_firebase()
    if db:
        # Sanitize
        clean_jobs = []
        for job in jobs:
            clean = {k: (v if v is not None else "") for k, v in job.items()}
            if isinstance(clean.get("score_breakdown"), str):
                try:
                    clean["score_breakdown"] = json.loads(clean["score_breakdown"])
                except (json.JSONDecodeError, TypeError):
                    clean["score_breakdown"] = {}
            clean_jobs.append(clean)

        # Split into chunks of 500 per doc (Firestore 1MB limit)
        for i in range(0, len(clean_jobs), 500):
            chunk_id = f"jobs_chunk_{i // 500}"
            db.collection("master").document(chunk_id).set({
                "updated_at": datetime.now().isoformat(),
                "chunk_index": i // 500,
                "job_count": len(clean_jobs[i:i+500]),
                "jobs": clean_jobs[i:i+500],
            })

    return {"synced": success, "jobs": len(jobs)}
