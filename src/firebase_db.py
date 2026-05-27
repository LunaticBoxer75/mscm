"""Firebase Firestore integration for MSCM job search.

Syncs local SQLite data to Google Firebase Firestore for:
- Cloud backup and access from anywhere
- Sharing results with Bhumika directly
- Mobile-friendly web dashboard access

Setup:
1. Create a Firebase project at https://console.firebase.google.com/
2. Go to Project Settings → Service Accounts → Generate new private key
3. Save the JSON file as config/firebase-credentials.json
4. Set FIREBASE_PROJECT_ID in .env or pass it directly

If Firebase is not configured, the system gracefully falls back to SQLite-only mode.
"""

import json
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"
FIREBASE_CREDS_PATH = CONFIG_DIR / "firebase-credentials.json"

_db = None
_initialized = False


def _init_firebase():
    """Initialize Firebase connection. Returns None if not configured."""
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
        print(f"[Firebase] Init failed (falling back to SQLite): {e}")
        return None


def is_available():
    """Check if Firebase is configured and accessible."""
    return _init_firebase() is not None


def sync_jobs(jobs_data):
    """Sync a list of job dicts to Firebase."""
    db = _init_firebase()
    if not db:
        return False

    batch = db.batch()
    jobs_ref = db.collection("jobs")

    for job in jobs_data:
        doc_ref = jobs_ref.document(job["job_id"])
        batch.set(doc_ref, {
            **job,
            "synced_at": datetime.now().isoformat(),
        }, merge=True)

    batch.commit()
    return True


def sync_scores(scored_jobs):
    """Sync scored jobs to Firebase."""
    db = _init_firebase()
    if not db:
        return False

    batch = db.batch()
    jobs_ref = db.collection("jobs")

    for job in scored_jobs:
        doc_ref = jobs_ref.document(job["job_id"])
        batch.set(doc_ref, {
            "score": job.get("score"),
            "score_breakdown": job.get("score_breakdown"),
            "scored_at": datetime.now().isoformat(),
        }, merge=True)

    batch.commit()
    return True


def sync_application(job_id, status, notes=None, follow_up_date=None):
    """Sync application status to Firebase."""
    db = _init_firebase()
    if not db:
        return False

    doc_ref = db.collection("applications").document(job_id)
    doc_ref.set({
        "job_id": job_id,
        "status": status,
        "notes": notes,
        "follow_up_date": follow_up_date,
        "updated_at": datetime.now().isoformat(),
    }, merge=True)
    return True


def sync_full_db():
    """Full sync from SQLite to Firebase. Call once to bootstrap."""
    db = _init_firebase()
    if not db:
        return {"synced": False, "reason": "Firebase not configured"}

    from .scraper import get_db
    import sqlite3

    conn = get_db()
    conn.row_factory = sqlite3.Row

    import time

    # Sync all jobs
    cursor = conn.execute("SELECT * FROM jobs")
    jobs = [dict(row) for row in cursor.fetchall()]

    # Batch in groups of 200 with rate limiting to avoid quota exhaustion
    jobs_ref = db.collection("jobs")
    for i in range(0, len(jobs), 200):
        batch = db.batch()
        for job in jobs[i:i+200]:
            doc_ref = jobs_ref.document(job["job_id"])
            batch.set(doc_ref, job, merge=True)
        try:
            batch.commit()
        except Exception:
            time.sleep(30)
            batch = db.batch()
            for job in jobs[i:i+200]:
                doc_ref = jobs_ref.document(job["job_id"])
                batch.set(doc_ref, job, merge=True)
            batch.commit()
        time.sleep(1)

    # Sync applications
    try:
        cursor = conn.execute("SELECT * FROM applications")
        apps = [dict(row) for row in cursor.fetchall()]
        apps_ref = db.collection("applications")
        batch = db.batch()
        for app in apps:
            doc_ref = apps_ref.document(app["job_id"])
            batch.set(doc_ref, app, merge=True)
        batch.commit()
    except sqlite3.OperationalError:
        pass

    conn.close()
    return {"synced": True, "jobs": len(jobs), "applications": len(apps) if 'apps' in dir() else 0}


def get_daily_report_from_firebase(date_str=None):
    """Retrieve jobs from Firebase for a given date."""
    db = _init_firebase()
    if not db:
        return []

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    jobs_ref = db.collection("jobs")
    query = jobs_ref.where("score", ">=", 50).order_by("score", direction="DESCENDING").limit(50)
    docs = query.stream()

    return [doc.to_dict() for doc in docs]
