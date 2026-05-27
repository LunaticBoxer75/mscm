"""MSCM Job Search Dashboard — Streamlit web UI.

Reads all data from Google Firestore (same source locally and deployed).
"""

import json
import zipfile
import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

PROJECTS_DIR = Path(__file__).parent / "projects"
OUTPUT_DIR = Path(__file__).parent / "output"
CONFIG_DIR = Path(__file__).parent / "config"

st.set_page_config(page_title="MSCM Job Search", page_icon="🎯", layout="wide")


# --- FIREBASE INIT ---
@st.cache_resource
def get_firestore_client():
    """Initialize Firestore client. Works locally (credentials file) and deployed (secrets)."""
    if not firebase_admin._apps:
        creds_path = CONFIG_DIR / "firebase-credentials.json"
        if creds_path.exists():
            cred = credentials.Certificate(str(creds_path))
        elif "FIREBASE_CREDENTIALS_JSON" in st.secrets:
            # Stored as a single JSON string — avoids TOML escaping issues with private_key
            creds_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS_JSON"])
            cred = credentials.Certificate(creds_dict)
        else:
            st.error("Firebase credentials not found. Set FIREBASE_CREDENTIALS_JSON in Streamlit secrets.")
            st.stop()
        firebase_admin.initialize_app(cred)
    return firestore.client()


def load_jobs_from_firestore(min_score=None):
    """Load jobs from Firestore."""
    db = get_firestore_client()
    jobs_ref = db.collection("jobs")

    if min_score and min_score > 0:
        q = jobs_ref.where("score", ">=", min_score).order_by("score", direction=firestore.Query.DESCENDING)
    else:
        q = jobs_ref.order_by("score", direction=firestore.Query.DESCENDING)

    docs = q.stream()
    jobs = []
    for doc in docs:
        data = doc.to_dict()
        if data.get("score") is not None:
            jobs.append(data)
    return pd.DataFrame(jobs) if jobs else pd.DataFrame()


def load_applications_from_firestore():
    """Load applications from Firestore."""
    db = get_firestore_client()
    apps_ref = db.collection("applications")
    docs = apps_ref.stream()
    apps = [doc.to_dict() for doc in docs]
    return pd.DataFrame(apps) if apps else pd.DataFrame()


def update_application_firestore(job_id, status, notes=None, follow_up_date=None):
    """Update application status in Firestore."""
    db = get_firestore_client()
    doc_ref = db.collection("applications").document(job_id)
    doc_ref.set({
        "job_id": job_id,
        "status": status,
        "notes": notes,
        "follow_up_date": follow_up_date,
        "updated_at": datetime.now().isoformat(),
        "applied_date": datetime.now().isoformat() if status == "applied" else None,
    }, merge=True)


# --- HEADER ---
st.title("🎯 MSCM Job Search Dashboard")
st.caption("Daily job identification for Bhumika Choudhary — UW Foster MSCM 2026-2028")

# --- LOAD DATA ---
all_jobs = load_jobs_from_firestore(min_score=0)
scored = all_jobs[all_jobs["score"].notna()] if not all_jobs.empty else pd.DataFrame()

# --- METRICS ---
if not scored.empty:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Jobs", len(all_jobs))
    col2.metric("Scored", len(scored))
    col3.metric("Score 75+", len(scored[scored["score"] >= 75]))
    col4.metric("Score 60-74", len(scored[(scored["score"] >= 60) & (scored["score"] < 75)]))
    col5.metric("Unscored", len(all_jobs) - len(scored))
    st.divider()

# --- SIDEBAR ---
st.sidebar.header("Filters")
min_score = st.sidebar.slider("Minimum Score", 0, 100, 50)
region_filter = st.sidebar.selectbox("Region", ["All", "seattle", "national"])
type_filter = st.sidebar.selectbox("Job Type", ["All", "fulltime", "internship"])

# --- MAIN TABS ---
tab_jobs, tab_tracker, tab_referrals, tab_skills, tab_projects, tab_export = st.tabs([
    "📋 Job Listings", "📊 Application Tracker", "🤝 Referrals",
    "🎓 Skills Gap", "🛠️ Projects", "📤 Export"
])


def filter_jobs(df):
    """Apply sidebar filters."""
    if df.empty:
        return df
    filtered = df[df["score"] >= min_score].copy()
    if region_filter != "All":
        filtered = filtered[filtered.get("region", pd.Series(dtype=str)) == region_filter]
    if type_filter != "All":
        filtered = filtered[filtered.get("job_type", pd.Series(dtype=str)) == type_filter]
    return filtered


# ============================================================
# TAB 1: JOB LISTINGS
# ============================================================
with tab_jobs:
    if scored.empty:
        st.info("No scored jobs yet. Run `/find-jobs` in Claude Code.")
    else:
        jobs = filter_jobs(scored)

        sub_tabs = st.tabs(["Seattle Full-Time", "Seattle Internships", "National Full-Time", "National Internships", "All"])

        def render_table(df, name, key):
            if df.empty:
                st.info(f"No {name} jobs matching filters.")
                return
            display = df[["score", "title", "company", "location", "job_url"]].copy()
            display["score"] = display["score"].astype(int)
            display = display.rename(columns={"score": "Score", "title": "Title", "company": "Company", "location": "Location", "job_url": "Link"})

            # Determine which row is currently selected
            current_sel = st.session_state.get("selected_job_idx")
            default_selection = []
            if current_sel is not None and current_sel in df.index:
                pos = list(df.index).index(current_sel)
                default_selection = [pos]

            event = st.dataframe(
                display,
                column_config={
                    "Link": st.column_config.LinkColumn("Apply", display_text="Apply →"),
                    "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
                },
                hide_index=True, use_container_width=True,
                on_select="rerun", selection_mode="single-row", key=key,
            )
            if event and event.selection and event.selection.rows:
                row_idx = event.selection.rows[0]
                st.session_state["selected_job_idx"] = df.index[row_idx]

        with sub_tabs[0]:
            sea_ft = jobs[(jobs.get("region", pd.Series(dtype=str)).isin(["seattle", ""]) | jobs.get("region", pd.Series(dtype=str)).isna()) & (jobs.get("job_type", pd.Series(dtype=str)) != "internship")]
            render_table(sea_ft, "Seattle full-time", "t_sea_ft")
        with sub_tabs[1]:
            sea_int = jobs[(jobs.get("region", pd.Series(dtype=str)).isin(["seattle", ""]) | jobs.get("region", pd.Series(dtype=str)).isna()) & (jobs.get("job_type", pd.Series(dtype=str)) == "internship")]
            render_table(sea_int, "Seattle internship", "t_sea_int")
        with sub_tabs[2]:
            nat_ft = jobs[jobs.get("region", pd.Series(dtype=str)) == "national"]
            nat_ft = nat_ft[nat_ft.get("job_type", pd.Series(dtype=str)) != "internship"]
            render_table(nat_ft, "National full-time", "t_nat_ft")
        with sub_tabs[3]:
            nat_int = jobs[(jobs.get("region", pd.Series(dtype=str)) == "national") & (jobs.get("job_type", pd.Series(dtype=str)) == "internship")]
            render_table(nat_int, "National internship", "t_nat_int")
        with sub_tabs[4]:
            render_table(jobs, "all", "t_all")

        # Job detail panel — driven by table row selection
        if not jobs.empty:
            st.divider()
            sel_idx = st.session_state.get("selected_job_idx")
            if sel_idx is None or sel_idx not in jobs.index:
                sel_idx = jobs.index[0]

            job = jobs.loc[sel_idx]
            st.markdown(f"### 📄 {job['title']}")
            st.markdown(f"**{job['company']}** · {job.get('location', '')} · Score: **{int(job['score'])}/100**")
            st.caption("👆 Click any row in the table above to view details here")
            c1, c2 = st.columns([2, 1])
            with c1:
                if job.get("job_url"):
                    st.markdown(f"🔗 [Apply Here]({job['job_url']})")
                if job.get("description"):
                    with st.expander("Full Description"):
                        st.markdown(str(job["description"])[:3000])
            with c2:
                st.metric("Score", f"{int(job['score'])}/100")
                breakdown = {}
                if job.get("score_breakdown"):
                    try:
                        breakdown = json.loads(job["score_breakdown"]) if isinstance(job["score_breakdown"], str) else (job["score_breakdown"] or {})
                    except (json.JSONDecodeError, TypeError):
                        pass
                if breakdown.get("reasoning"):
                    st.info(breakdown["reasoning"])
                if breakdown.get("highlights"):
                    st.success("**Highlights:** " + ", ".join(breakdown["highlights"]))
                if breakdown.get("red_flags") and breakdown["red_flags"]:
                    st.warning("**Concerns:** " + ", ".join(breakdown["red_flags"]))

                st.divider()
                track_st = st.selectbox("Track:", ["—", "applied", "interviewing", "skipped"], key="trk")
                if track_st != "—" and st.button("Update Status"):
                    update_application_firestore(job.get("job_id", ""), track_st)
                    st.success(f"Marked as {track_st}!")
                    st.rerun()

            # Referral links for this specific job
            import urllib.parse
            company = job.get("company", "")
            title = job.get("title", "")
            if company:
                role_kw = title.lower().replace("sr.", "").replace("senior", "").replace("jr.", "").strip()
                st.markdown("#### 🤝 Find Referrals at " + company)
                ref_cols = st.columns(4)
                ref_cols[0].markdown(f"[👥 Same Role]({('https://www.linkedin.com/search/results/people/?keywords=' + urllib.parse.quote(role_kw) + '&company=' + urllib.parse.quote(company))})")
                ref_cols[1].markdown(f"[🎯 Recruiters]({('https://www.linkedin.com/search/results/people/?keywords=recruiter%20talent%20acquisition&company=' + urllib.parse.quote(company))})")
                ref_cols[2].markdown(f"[📦 SC Team]({('https://www.linkedin.com/search/results/people/?keywords=supply%20chain%20procurement&company=' + urllib.parse.quote(company))})")
                ref_cols[3].markdown(f"[🎓 UW Alumni]({('https://www.linkedin.com/search/results/people/?keywords=' + urllib.parse.quote(company) + '&schoolFilter=%5B%224399%22%5D')})")

# ============================================================
# TAB 2: APPLICATION TRACKER
# ============================================================
with tab_tracker:
    st.subheader("Application Pipeline")
    apps = load_applications_from_firestore()

    if apps.empty:
        st.info("No applications tracked yet. Go to Job Listings → select a job → set status.")
    else:
        statuses = ["applied", "interviewing", "offer", "rejected", "skipped"]
        status_counts = apps["status"].value_counts() if "status" in apps.columns else pd.Series()
        cols = st.columns(5)
        emojis = ["📨", "🎤", "🎉", "❌", "⏭️"]
        for col, status, emoji in zip(cols, statuses, emojis):
            col.metric(f"{emoji} {status.title()}", status_counts.get(status, 0))

        st.divider()
        display_cols = [c for c in ["status", "job_id", "notes", "follow_up_date", "applied_date"] if c in apps.columns]
        st.dataframe(apps[display_cols], hide_index=True, use_container_width=True)

# ============================================================
# TAB 3: REFERRALS
# ============================================================
with tab_referrals:
    st.subheader("🤝 Referral & Networking Links")
    st.caption("LinkedIn search links to find employees at top companies")

    if scored.empty:
        st.info("No scored jobs yet.")
    else:
        import urllib.parse
        top_jobs = scored[scored["score"] >= 75].head(20)
        seen_companies = set()

        for _, job in top_jobs.iterrows():
            company = job.get("company", "")
            if not company or company in seen_companies:
                continue
            seen_companies.add(company)
            title = job.get("title", "")
            role_kw = title.lower().replace("sr.", "").replace("senior", "").strip()

            with st.expander(f"**[{int(job['score'])}] {title}** @ {company} — {job.get('location', '')}"):
                links = [
                    (f"People in similar roles at {company}", f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(role_kw)}&company={urllib.parse.quote(company)}"),
                    (f"Recruiters at {company}", f"https://www.linkedin.com/search/results/people/?keywords=recruiter%20talent%20acquisition&company={urllib.parse.quote(company)}"),
                    (f"Supply Chain team at {company}", f"https://www.linkedin.com/search/results/people/?keywords=supply%20chain%20procurement&company={urllib.parse.quote(company)}"),
                    (f"UW Foster alumni at {company}", f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(company)}&schoolFilter=%5B%224399%22%5D"),
                ]
                for label, url in links:
                    st.markdown(f"- [{label}]({url})")
                if job.get("job_url"):
                    st.markdown(f"\n[View Job Posting →]({job['job_url']})")

        st.divider()
        st.subheader("📝 Outreach Template")
        st.code("Hi [Name],\n\nI'm an incoming MSCM student at UW Foster (starting Fall 2026) with 3 years\nof operations experience at Uber. I noticed [Company] has a [Role] opening\nand I'd love to learn more about the team and culture.\n\nWould you be open to a 15-minute chat? Happy to work around your schedule.\n\nBest,\nBhumika Choudhary", language=None)

# ============================================================
# TAB 4: SKILLS GAP
# ============================================================
with tab_skills:
    st.subheader("Skills Gap Analysis")

    if scored.empty or len(scored) < 5:
        st.info("Need at least 5 scored jobs. Run /find-jobs first.")
    else:
        descriptions = scored[scored["score"] >= 55]["description"].dropna().tolist()
        skills_check = {
            "Python": ["python", "pandas", "numpy"], "Tableau": ["tableau"],
            "Power BI": ["power bi", "powerbi"], "SAP/ERP": ["sap", "s/4hana", "erp"],
            "SQL": ["sql", "mysql", "postgresql"], "Excel Advanced": ["vba", "macros", "power query"],
            "Forecasting": ["forecasting", "demand planning", "s&op"],
            "Procurement": ["procurement", "sourcing", "rfp"],
            "Logistics": ["logistics", "freight", "3pl", "wms"],
            "Six Sigma": ["lean", "six sigma", "kaizen"],
            "Project Management": ["pmp", "agile", "scrum"],
        }
        has_skills = {"SQL", "Six Sigma", "Project Management", "Excel Advanced"}

        results = []
        for skill, kws in skills_check.items():
            count = sum(1 for d in descriptions if any(k in d.lower() for k in kws))
            pct = round(count / len(descriptions) * 100, 1) if descriptions else 0
            results.append({"Skill": skill, "Requested In": f"{pct}%", "Has It": "✅" if skill in has_skills else "❌ GAP", "pct": pct})
        results.sort(key=lambda x: x["pct"], reverse=True)
        st.dataframe(pd.DataFrame(results).drop(columns=["pct"]), hide_index=True, use_container_width=True)

# ============================================================
# TAB 5: PROJECTS
# ============================================================
with tab_projects:
    st.subheader("Portfolio Projects")
    if PROJECTS_DIR.exists():
        for pdir in sorted(PROJECTS_DIR.iterdir()):
            if pdir.is_dir() and (pdir / "README.md").exists():
                content = (pdir / "README.md").read_text()
                title = content.split("\n")[0].replace("# ", "")
                with st.expander(f"📁 {title}"):
                    st.markdown(content[:5000])
                    st.download_button("Download Guide", content, f"{pdir.name}.md", "text/markdown", key=f"dl_{pdir.name}")
    else:
        st.info("No projects yet. Run `/generate-projects`.")

# ============================================================
# TAB 6: EXPORT
# ============================================================
with tab_export:
    st.subheader("Export Data")
    if not scored.empty:
        csv = scored[["title", "company", "location", "job_url", "score", "job_type", "region"]].to_csv(index=False)
        st.download_button("📥 Download All Jobs (CSV)", csv, "jobs.csv", "text/csv")

    apps_exp = load_applications_from_firestore()
    if not apps_exp.empty:
        st.download_button("📥 Download Applications (CSV)", apps_exp.to_csv(index=False), "applications.csv", "text/csv")

# --- FOOTER ---
st.divider()
st.caption(f"Data source: Firebase (mscm-5591c) | Last loaded: {datetime.now().strftime('%H:%M')} | Powered by Claude Code")
