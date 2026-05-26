"""Application status tracker — track which jobs have been applied to, skipped, or are in progress."""

import json
from datetime import datetime
from pathlib import Path

from .scraper import get_db

OUTPUT_DIR = Path(__file__).parent.parent / "output"

STATUSES = ["new", "applied", "interviewing", "offer", "rejected", "skipped"]


def _ensure_tracker_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            job_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'new',
            applied_date TEXT,
            notes TEXT,
            follow_up_date TEXT,
            updated_at TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        )
    """)
    conn.commit()
    return conn


def update_status(job_id, status, notes=None, follow_up_date=None):
    """Update application status for a job."""
    if status not in STATUSES:
        raise ValueError(f"Status must be one of: {STATUSES}")

    conn = _ensure_tracker_table()
    now = datetime.now().isoformat()

    conn.execute("""
        INSERT INTO applications (job_id, status, applied_date, notes, follow_up_date, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            status = excluded.status,
            notes = excluded.notes,
            follow_up_date = excluded.follow_up_date,
            updated_at = excluded.updated_at
    """, (job_id, status, now if status == "applied" else None, notes, follow_up_date, now))
    conn.commit()
    conn.close()

    # Auto-sync to Firebase
    try:
        from .firebase_db import sync_application
        sync_application(job_id, status, notes, follow_up_date)
    except Exception:
        pass


def get_application_summary():
    """Get counts by status."""
    conn = _ensure_tracker_table()
    cursor = conn.execute("""
        SELECT a.status, COUNT(*) as cnt
        FROM applications a
        GROUP BY a.status
    """)
    summary = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return summary


def get_applications_by_status(status):
    """Get all applications with a given status, joined with job details."""
    conn = _ensure_tracker_table()
    cursor = conn.execute("""
        SELECT j.title, j.company, j.location, j.job_url, j.score,
               a.status, a.applied_date, a.notes, a.follow_up_date
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.status = ?
        ORDER BY j.score DESC
    """, (status,))
    columns = [desc[0] for desc in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_follow_ups_due():
    """Get applications where follow-up date has passed."""
    conn = _ensure_tracker_table()
    now = datetime.now().isoformat()[:10]
    cursor = conn.execute("""
        SELECT j.title, j.company, j.job_url, a.follow_up_date, a.notes
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.follow_up_date <= ? AND a.status IN ('applied', 'interviewing')
        ORDER BY a.follow_up_date
    """, (now,))
    columns = [desc[0] for desc in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return rows


def generate_tracker_report():
    """Generate application tracking report."""
    summary = get_application_summary()
    follow_ups = get_follow_ups_due()

    lines = [
        "# Application Tracker",
        "",
        "## Status Summary",
        f"| Status | Count |",
        f"|--------|-------|",
    ]
    for status in STATUSES:
        count = summary.get(status, 0)
        lines.append(f"| {status.capitalize()} | {count} |")

    if follow_ups:
        lines.extend(["", "## Follow-ups Due", ""])
        for f in follow_ups:
            lines.append(f"- **{f['title']}** @ {f['company']} (due: {f['follow_up_date']})")
            if f.get("notes"):
                lines.append(f"  Notes: {f['notes']}")

    applied = get_applications_by_status("applied")
    if applied:
        lines.extend(["", "## Applied (Awaiting Response)", ""])
        for a in applied:
            lines.append(f"- [{a['score']}] **{a['title']}** @ {a['company']} — applied {a['applied_date'][:10]}")

    interviewing = get_applications_by_status("interviewing")
    if interviewing:
        lines.extend(["", "## In Interview Process", ""])
        for a in interviewing:
            lines.append(f"- **{a['title']}** @ {a['company']} — {a.get('notes', '')}")

    return "\n".join(lines)
