"""MSCM Job Search Dashboard — Streamlit web UI."""

import json
import sqlite3
import zipfile
import io
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "jobs.db"
PROJECTS_DIR = Path(__file__).parent / "projects"
OUTPUT_DIR = Path(__file__).parent / "output"

st.set_page_config(
    page_title="MSCM Job Search",
    page_icon="🎯",
    layout="wide",
)


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def load_jobs(min_score=None, region=None, job_type=None):
    conn = get_conn()
    query = "SELECT * FROM jobs WHERE score IS NOT NULL"
    params = []
    if min_score:
        query += " AND score >= ?"
        params.append(min_score)
    if region:
        query += " AND region = ?"
        params.append(region)
    if job_type:
        query += " AND job_type = ?"
        params.append(job_type)
    query += " ORDER BY score DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def load_all_jobs():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM jobs", conn)
    conn.close()
    return df


def ensure_tracker_table():
    conn = get_conn()
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
    conn.close()


def get_applications():
    ensure_tracker_table()
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT j.title, j.company, j.location, j.job_url, j.score, j.job_type, j.region,
               a.status, a.applied_date, a.notes, a.follow_up_date, a.job_id
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        ORDER BY
            CASE a.status
                WHEN 'interviewing' THEN 1
                WHEN 'applied' THEN 2
                WHEN 'offer' THEN 3
                WHEN 'new' THEN 4
                WHEN 'rejected' THEN 5
                WHEN 'skipped' THEN 6
            END,
            j.score DESC
    """, conn)
    conn.close()
    return df


def update_application(job_id, status, notes=None, follow_up_date=None):
    """Update application status — uses tracker module which auto-syncs to Firebase."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from src.tracker import update_status
    update_status(job_id, status, notes, follow_up_date)


# --- HEADER ---
st.title("🎯 MSCM Job Search Dashboard")
st.caption("Daily job identification for Bhumika Choudhary — UW Foster MSCM 2026-2028")

# --- METRICS ---
all_jobs = load_all_jobs()
scored = all_jobs[all_jobs["score"].notna()]
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Jobs", len(all_jobs))
col2.metric("Scored", len(scored))
col3.metric("Score 75+", len(scored[scored["score"] >= 75]))
col4.metric("Score 60-74", len(scored[(scored["score"] >= 60) & (scored["score"] < 75)]))
col5.metric("Unscored", len(all_jobs[all_jobs["score"].isna()]))

st.divider()

# --- SIDEBAR ---
st.sidebar.header("Filters")
min_score = st.sidebar.slider("Minimum Score", 0, 100, 50)
region_filter = st.sidebar.selectbox("Region", ["All", "seattle", "national"])
type_filter = st.sidebar.selectbox("Job Type", ["All", "fulltime", "internship"])

region_val = None if region_filter == "All" else region_filter
type_val = None if type_filter == "All" else type_filter

st.sidebar.divider()
st.sidebar.header("Export")
export_format = st.sidebar.selectbox("Export Format", ["CSV", "JSON", "Full ZIP"])

# --- MAIN TABS ---
tab_jobs, tab_tracker, tab_referrals, tab_skills, tab_projects, tab_export = st.tabs([
    "📋 Job Listings", "📊 Application Tracker", "🤝 Referrals",
    "🎓 Skills Gap", "🛠️ Projects", "📤 Export"
])

# ============================================================
# TAB 1: JOB LISTINGS (4 panels)
# ============================================================
with tab_jobs:
    jobs = load_jobs(min_score=min_score, region=region_val, job_type=type_val)

    sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5 = st.tabs([
        "Seattle Full-Time", "Seattle Internships",
        "National Full-Time", "National Internships", "All"
    ])

    def render_job_table(df, tab_name, key_suffix=""):
        if df.empty:
            st.info(f"No {tab_name} jobs found matching filters.")
            return

        display_df = df[["score", "title", "company", "location", "salary_min", "salary_max", "job_url", "date_posted"]].copy()
        display_df["salary"] = display_df.apply(
            lambda r: f"${r['salary_min']:,.0f}-${r['salary_max']:,.0f}"
            if pd.notna(r["salary_min"]) and pd.notna(r["salary_max"])
            else (f"${r['salary_min']:,.0f}+" if pd.notna(r["salary_min"]) else "—"),
            axis=1,
        )
        display_df = display_df.drop(columns=["salary_min", "salary_max"])
        display_df["score"] = display_df["score"].astype(int)
        display_df = display_df.rename(columns={
            "score": "Score", "title": "Title", "company": "Company",
            "location": "Location", "salary": "Salary", "job_url": "Link",
            "date_posted": "Posted",
        })

        event = st.dataframe(
            display_df,
            column_config={
                "Link": st.column_config.LinkColumn("Apply", display_text="Apply →"),
                "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            },
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            key=f"table_{tab_name}_{key_suffix}",
        )

        # If a row is selected in this table, store it in session state
        if event and event.selection and event.selection.rows:
            selected_row_idx = event.selection.rows[0]
            original_idx = df.index[selected_row_idx]
            st.session_state["selected_job_idx"] = original_idx

    with sub_tab1:
        seattle_ft = jobs[(jobs["region"] == "seattle") & (jobs["job_type"] != "internship")]
        untagged_ft = jobs[(jobs["region"].isna()) & (jobs["job_type"] != "internship")]
        seattle_ft = pd.concat([seattle_ft, untagged_ft])
        render_job_table(seattle_ft, "Seattle full-time", "sea_ft")

    with sub_tab2:
        seattle_intern = jobs[(jobs["region"] == "seattle") & (jobs["job_type"] == "internship")]
        untagged_intern = jobs[(jobs["region"].isna()) & (jobs["job_type"] == "internship")]
        seattle_intern = pd.concat([seattle_intern, untagged_intern])
        render_job_table(seattle_intern, "Seattle internship", "sea_int")

    with sub_tab3:
        national_ft = jobs[(jobs["region"] == "national") & (jobs["job_type"] != "internship")]
        render_job_table(national_ft, "National full-time", "nat_ft")

    with sub_tab4:
        national_intern = jobs[(jobs["region"] == "national") & (jobs["job_type"] == "internship")]
        render_job_table(national_intern, "National internship", "nat_int")

    with sub_tab5:
        render_job_table(jobs, "all", "all")

    # Job detail panel — driven by table row selection
    if not jobs.empty:
        st.divider()
        st.subheader("Job Details")

        selected_idx = st.session_state.get("selected_job_idx")

        # Validate the selection is still in current filtered jobs
        if selected_idx is None or selected_idx not in jobs.index:
            selected_idx = jobs.index[0]

        # Show which job is selected (also allow manual override via dropdown)
        selected_idx = st.selectbox(
            "Selected job (click a row above to change):",
            options=jobs.index,
            index=list(jobs.index).index(selected_idx) if selected_idx in jobs.index else 0,
            format_func=lambda i: f"[{int(jobs.loc[i, 'score'])}] {jobs.loc[i, 'title']} @ {jobs.loc[i, 'company']}",
            key="detail_select",
        )

        job = jobs.loc[selected_idx]
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"### {job['title']}")
            st.markdown(f"**{job['company']}** — {job['location']}")
            if job.get("job_url"):
                st.markdown(f"[Apply Here]({job['job_url']})")
            if job.get("description"):
                with st.expander("Full Description", expanded=False):
                    st.markdown(str(job["description"])[:3000])

        with col2:
            st.metric("Overall Score", f"{int(job['score'])}/100")
            if job.get("score_breakdown"):
                try:
                    breakdown = json.loads(job["score_breakdown"]) if isinstance(job["score_breakdown"], str) else {}
                    if breakdown.get("reasoning"):
                        st.info(breakdown["reasoning"])
                    if breakdown.get("highlights"):
                        st.success("**Highlights:** " + ", ".join(breakdown["highlights"]))
                    if breakdown.get("red_flags") and breakdown["red_flags"]:
                        st.warning("**Concerns:** " + ", ".join(breakdown["red_flags"]))
                except (json.JSONDecodeError, TypeError):
                    pass

            # Quick action: track this job
            st.divider()
            track_status = st.selectbox("Track:", ["—", "applied", "interviewing", "skipped"], key="track_status")
            if track_status != "—":
                if st.button("Update Status"):
                    update_application(job["job_id"], track_status)
                    st.success(f"Marked as {track_status}!")
                    st.rerun()

# ============================================================
# TAB 2: APPLICATION TRACKER
# ============================================================
with tab_tracker:
    st.subheader("Application Pipeline")

    apps = get_applications()

    if apps.empty:
        st.info("No applications tracked yet. Go to Job Listings → select a job → set status.")
    else:
        # Pipeline summary
        status_counts = apps["status"].value_counts()
        cols = st.columns(6)
        statuses = ["new", "applied", "interviewing", "offer", "rejected", "skipped"]
        colors = ["🔵", "📨", "🎤", "🎉", "❌", "⏭️"]
        for col, status, emoji in zip(cols, statuses, colors):
            count = status_counts.get(status, 0)
            col.metric(f"{emoji} {status.title()}", count)

        st.divider()

        # Follow-ups due
        today = datetime.now().strftime("%Y-%m-%d")
        due = apps[apps["follow_up_date"].notna() & (apps["follow_up_date"] <= today)]
        if not due.empty:
            st.warning(f"⏰ **{len(due)} follow-ups due!**")
            for _, row in due.iterrows():
                st.markdown(f"- **{row['title']}** @ {row['company']} — due {row['follow_up_date']}")

        # Full table
        st.dataframe(
            apps[["status", "title", "company", "score", "applied_date", "notes", "follow_up_date"]].rename(columns={
                "status": "Status", "title": "Title", "company": "Company",
                "score": "Score", "applied_date": "Applied", "notes": "Notes",
                "follow_up_date": "Follow-up",
            }),
            hide_index=True,
            use_container_width=True,
        )

        # Update form
        st.divider()
        st.subheader("Update Application")
        app_idx = st.selectbox("Select application:", apps.index,
                               format_func=lambda i: f"{apps.loc[i, 'title']} @ {apps.loc[i, 'company']}")
        if app_idx is not None:
            c1, c2, c3 = st.columns(3)
            new_status = c1.selectbox("New Status", statuses, key="update_status")
            new_notes = c2.text_input("Notes", value=apps.loc[app_idx, "notes"] or "")
            new_follow = c3.date_input("Follow-up Date", value=None)

            if st.button("Save Changes"):
                follow_str = new_follow.isoformat() if new_follow else None
                update_application(apps.loc[app_idx, "job_id"], new_status, new_notes, follow_str)
                st.success("Updated!")
                st.rerun()

# ============================================================
# TAB: REFERRALS
# ============================================================
with tab_referrals:
    st.subheader("🤝 Referral & Networking Links")
    st.caption("LinkedIn search links to find employees at top companies for warm intros")

    from src.referrals import get_referral_report, generate_referral_links

    ref_report = get_referral_report(min_score=75, limit=10)

    if not ref_report:
        st.info("No jobs scoring 75+ yet. Run /find-jobs to identify top targets.")
    else:
        for entry in ref_report:
            job = entry["job"]
            with st.expander(f"**[{int(job['score'])}] {job['title']}** @ {job['company']} — {job['location']}", expanded=False):
                cols = st.columns([2, 1])
                with cols[0]:
                    for link in entry["links"]:
                        st.markdown(f"- [{link['label']}]({link['url']}) — _{link['purpose']}_")
                with cols[1]:
                    if job.get("job_url"):
                        st.markdown(f"[View Job Posting →]({job['job_url']})")

        st.divider()
        st.subheader("📝 Outreach Template")
        st.code("""Hi [Name],

I'm an incoming MSCM student at UW Foster (starting Fall 2026) with 3 years
of operations experience at Uber. I noticed [Company] has a [Role] opening
and I'd love to learn more about the team and culture.

Would you be open to a 15-minute chat? Happy to work around your schedule.

Best,
Bhumika Choudhary""", language=None)

# ============================================================
# TAB: SKILLS GAP
# ============================================================
with tab_skills:
    st.subheader("Skills Gap Analysis")
    st.caption("Based on requirements from top-scoring job listings")

    if scored.empty or len(scored) < 5:
        st.info("Need at least 5 scored jobs for skills gap analysis. Run /find-jobs first.")
    else:
        # Analyze skills from descriptions
        descriptions = scored[scored["score"] >= 55]["description"].dropna().tolist()

        skills_to_check = {
            "Python": ["python", "pandas", "numpy", "scikit"],
            "Tableau": ["tableau"],
            "Power BI": ["power bi", "powerbi"],
            "SAP/ERP": ["sap", "s/4hana", "erp", "oracle scm"],
            "R": ["r programming", " r,", "rstudio"],
            "SQL": ["sql", "mysql", "postgresql"],
            "Excel Advanced": ["vlookup", "pivot table", "macros", "vba"],
            "Forecasting": ["forecasting", "demand planning", "s&op"],
            "Procurement": ["procurement", "sourcing", "rfp", "rfq"],
            "Logistics": ["logistics", "freight", "3pl", "wms"],
            "Six Sigma": ["lean", "six sigma", "kaizen", "dmaic"],
            "APICS/CSCP": ["apics", "cscp", "cpim"],
            "Project Management": ["pmp", "agile", "scrum"],
            "Data Visualization": ["data visualization", "dashboard", "reporting"],
        }

        has_skills = {"SQL", "Six Sigma", "Project Management", "Excel Advanced", "Data Visualization"}

        results = []
        for skill, keywords in skills_to_check.items():
            count = sum(1 for d in descriptions if any(kw.lower() in d.lower() for kw in keywords))
            pct = round(count / len(descriptions) * 100, 1) if descriptions else 0
            results.append({
                "Skill": skill,
                "Requested In": f"{pct}% ({count}/{len(descriptions)})",
                "Has It": "✅" if skill in has_skills else "❌ GAP",
                "Priority": "—" if skill in has_skills else ("🔴 HIGH" if pct > 40 else "🟡 Medium" if pct > 20 else "🟢 Low"),
                "pct": pct,
            })

        results.sort(key=lambda x: x["pct"], reverse=True)
        results_df = pd.DataFrame(results).drop(columns=["pct"])
        st.dataframe(results_df, hide_index=True, use_container_width=True)

        # Recommendations
        gaps = [r for r in results if "GAP" in r["Has It"] and r["pct"] > 15]
        if gaps:
            st.divider()
            st.subheader("📚 Recommended Focus Areas for MSCM Coursework")
            for i, g in enumerate(gaps[:5], 1):
                st.markdown(f"{i}. **{g['Skill']}** — {g['Requested In']}")

# ============================================================
# TAB 4: PORTFOLIO PROJECTS
# ============================================================
with tab_projects:
    st.subheader("Portfolio Projects")
    st.caption("Auto-generated projects to fill skill gaps and strengthen your resume")

    # List existing projects
    if PROJECTS_DIR.exists():
        project_dirs = [d for d in PROJECTS_DIR.iterdir() if d.is_dir()]
        if project_dirs:
            for pdir in sorted(project_dirs):
                readme = pdir / "README.md"
                if readme.exists():
                    content = readme.read_text()
                    title_line = content.split("\n")[0].replace("# ", "")
                    with st.expander(f"📁 {title_line}", expanded=False):
                        st.markdown(content[:5000])

                        # Download button for this project
                        st.download_button(
                            "Download Project Guide",
                            data=content,
                            file_name=f"{pdir.name}-guide.md",
                            mime="text/markdown",
                            key=f"dl_{pdir.name}",
                        )
        else:
            st.info("No projects generated yet. Run `/generate-projects` in Claude Code to create them based on your skills gaps.")
    else:
        st.info("No projects generated yet. Run `/generate-projects` in Claude Code.")

    st.divider()
    st.subheader("How Projects Are Generated")
    st.markdown("""
    1. The system analyzes **top-scoring job descriptions** to find commonly requested skills
    2. Skills you already have (SQL, Six Sigma, project management, etc.) are excluded
    3. For each **gap**, a detailed project guide is created that:
       - Teaches the skill from scratch (beginner-friendly)
       - Is completable in 1-2 weeks
       - Produces a portfolio piece for your resume
       - Includes a ready-to-use resume bullet point
    4. Projects are regenerated as new job data comes in, keeping recommendations current
    """)

# ============================================================
# TAB 5: EXPORT
# ============================================================
with tab_export:
    st.subheader("Export Data")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📋 Today's Report")
        today = datetime.now().strftime("%Y-%m-%d")
        report_path = OUTPUT_DIR / f"report-{today}.md"
        if report_path.exists():
            report_content = report_path.read_text()
            st.download_button("Download Report (Markdown)", report_content,
                             file_name=f"job-report-{today}.md", mime="text/markdown")
        else:
            st.info("No report generated today yet. Run /find-jobs first.")

        st.markdown("### 📊 All Scored Jobs (CSV)")
        if not scored.empty:
            csv_data = scored[["title", "company", "location", "job_url", "score",
                              "job_type", "region", "salary_min", "salary_max",
                              "date_posted", "source"]].to_csv(index=False)
            st.download_button("Download Jobs CSV", csv_data,
                             file_name=f"jobs-{today}.csv", mime="text/csv")

    with col2:
        st.markdown("### 📊 Application Tracker")
        apps_export = get_applications()
        if not apps_export.empty:
            apps_csv = apps_export.to_csv(index=False)
            st.download_button("Download Applications CSV", apps_csv,
                             file_name=f"applications-{today}.csv", mime="text/csv")
        else:
            st.info("No applications tracked yet.")

        st.markdown("### 📦 Full Export (ZIP)")
        if st.button("Generate Full ZIP Export"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add report
                if report_path.exists():
                    zf.writestr(f"report-{today}.md", report_path.read_text())

                # Add jobs CSV
                if not scored.empty:
                    zf.writestr(f"jobs-{today}.csv", scored.to_csv(index=False))

                # Add applications
                if not apps_export.empty:
                    zf.writestr(f"applications-{today}.csv", apps_export.to_csv(index=False))

                # Add all project guides
                if PROJECTS_DIR.exists():
                    for pdir in PROJECTS_DIR.iterdir():
                        if pdir.is_dir():
                            for f in pdir.rglob("*"):
                                if f.is_file():
                                    zf.writestr(f"projects/{pdir.name}/{f.name}", f.read_text())

                # Add skills gap
                gap_path = OUTPUT_DIR / f"skills-gap-{today}.md"
                if gap_path.exists():
                    zf.writestr(f"skills-gap-{today}.md", gap_path.read_text())

            st.download_button("📥 Download ZIP", zip_buffer.getvalue(),
                             file_name=f"mscm-export-{today}.zip", mime="application/zip")

# --- FOOTER ---
st.divider()
col1, col2 = st.columns(2)
col1.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
col2.caption(f"Database: {DB_PATH} | {len(all_jobs)} jobs tracked")
