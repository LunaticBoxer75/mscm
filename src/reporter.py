"""Generate daily job reports in markdown and CSV formats."""

import json
from datetime import datetime
from pathlib import Path

from .scraper import get_db

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def generate_daily_report(min_score=50, limit=30):
    """Generate a markdown report of today's top jobs."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    conn = get_db()
    cursor = conn.execute("""
        SELECT * FROM jobs
        WHERE score IS NOT NULL AND score >= ?
        ORDER BY score DESC
        LIMIT ?
    """, (min_score, limit))
    columns = [desc[0] for desc in cursor.description]
    jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()

    if not jobs:
        return "No scored jobs found above threshold."

    today = datetime.now().strftime("%Y-%m-%d")
    report_lines = [
        f"# Daily Job Report - {today}",
        f"",
        f"**Total matches:** {len(jobs)} jobs scoring {min_score}+",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"---",
        f"",
    ]

    tier_labels = {
        (90, 101): "Excellent Match (90+)",
        (75, 90): "Strong Match (75-89)",
        (60, 75): "Good Match (60-74)",
        (50, 60): "Worth Considering (50-59)",
    }

    for (low, high), label in tier_labels.items():
        tier_jobs = [j for j in jobs if low <= (j.get("score") or 0) < high]
        if not tier_jobs:
            continue

        report_lines.append(f"## {label}")
        report_lines.append("")

        for job in tier_jobs:
            score = job.get("score", 0)
            title = job.get("title", "Unknown")
            company = job.get("company", "Unknown")
            location = job.get("location", "Unknown")
            url = job.get("job_url", "")
            salary_str = ""
            if job.get("salary_min") and job.get("salary_max"):
                salary_str = f" | ${job['salary_min']:,.0f}-${job['salary_max']:,.0f}"
            elif job.get("salary_min"):
                salary_str = f" | ${job['salary_min']:,.0f}+"

            breakdown = {}
            if job.get("score_breakdown"):
                try:
                    breakdown = json.loads(job["score_breakdown"]) if isinstance(job["score_breakdown"], str) else job["score_breakdown"]
                except (json.JSONDecodeError, TypeError):
                    pass

            reasoning = breakdown.get("reasoning", "")
            highlights = breakdown.get("highlights", [])
            red_flags = breakdown.get("red_flags", [])

            report_lines.append(f"### [{score}] {title} @ {company}")
            report_lines.append(f"**Location:** {location}{salary_str}")
            if url:
                report_lines.append(f"**Apply:** {url}")
            if reasoning:
                report_lines.append(f"**Why:** {reasoning}")
            if highlights:
                report_lines.append(f"**Highlights:** {', '.join(highlights)}")
            if red_flags and red_flags != ["parse_error"]:
                report_lines.append(f"**Concerns:** {', '.join(red_flags)}")
            report_lines.append("")

    report_content = "\n".join(report_lines)

    report_path = OUTPUT_DIR / f"report-{today}.md"
    report_path.write_text(report_content)

    return report_content


def generate_csv_export(min_score=0):
    """Export all scored jobs to CSV."""
    import csv

    OUTPUT_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.execute("""
        SELECT job_id, title, company, location, job_url, job_type,
               date_posted, salary_min, salary_max, source, search_term,
               search_category, score, scored_at, is_remote
        FROM jobs
        WHERE score IS NOT NULL AND score >= ?
        ORDER BY score DESC
    """, (min_score,))
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    csv_path = OUTPUT_DIR / f"jobs-{today}.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    return str(csv_path), len(rows)


def get_stats():
    """Get summary statistics."""
    conn = get_db()
    stats = {}
    stats["total_jobs"] = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    stats["scored_jobs"] = conn.execute("SELECT COUNT(*) FROM jobs WHERE score IS NOT NULL").fetchone()[0]
    stats["unscored_jobs"] = conn.execute("SELECT COUNT(*) FROM jobs WHERE score IS NULL").fetchone()[0]
    stats["high_matches"] = conn.execute("SELECT COUNT(*) FROM jobs WHERE score >= 75").fetchone()[0]
    stats["good_matches"] = conn.execute("SELECT COUNT(*) FROM jobs WHERE score >= 60 AND score < 75").fetchone()[0]

    top_companies = conn.execute("""
        SELECT company, COUNT(*) as cnt, AVG(score) as avg_score
        FROM jobs WHERE score IS NOT NULL
        GROUP BY company ORDER BY avg_score DESC LIMIT 10
    """).fetchall()
    stats["top_companies"] = [{"company": r[0], "count": r[1], "avg_score": round(r[2], 1)} for r in top_companies]
    conn.close()
    return stats


if __name__ == "__main__":
    from rich.console import Console
    console = Console()
    report = generate_daily_report()
    console.print(report)
