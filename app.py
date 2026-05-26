"""MSCM Job Search Dashboard — Streamlit web UI."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "jobs.db"

st.set_page_config(
    page_title="MSCM Job Search",
    page_icon="🎯",
    layout="wide",
)


@st.cache_resource
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
    return pd.read_sql_query(query, conn, params=params)


def load_all_jobs():
    conn = get_conn()
    return pd.read_sql_query("SELECT * FROM jobs", conn)


# --- HEADER ---
st.title("MSCM Job Search Dashboard")
st.caption("Daily job identification for Bhumika Choudhary — UW Foster MSCM")

# --- SIDEBAR ---
st.sidebar.header("Filters")
min_score = st.sidebar.slider("Minimum Score", 0, 100, 50)
region_filter = st.sidebar.selectbox("Region", ["All", "seattle", "national"])
type_filter = st.sidebar.selectbox("Job Type", ["All", "fulltime", "internship"])

region_val = None if region_filter == "All" else region_filter
type_val = None if type_filter == "All" else type_filter

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

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Seattle Full-Time", "Seattle Internships",
    "National Full-Time", "National Internships",
    "All Jobs"
])


def render_job_table(df, tab_name):
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

    st.dataframe(
        display_df,
        column_config={
            "Link": st.column_config.LinkColumn("Apply", display_text="Apply →"),
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
        },
        hide_index=True,
        use_container_width=True,
    )


jobs = load_jobs(min_score=min_score, region=region_val, job_type=type_val)

with tab1:
    seattle_ft = jobs[(jobs["region"] == "seattle") & (jobs["job_type"] != "internship")]
    # Include untagged jobs in seattle
    untagged_ft = jobs[(jobs["region"].isna()) & (jobs["job_type"] != "internship")]
    seattle_ft = pd.concat([seattle_ft, untagged_ft])
    render_job_table(seattle_ft, "Seattle full-time")

with tab2:
    seattle_intern = jobs[(jobs["region"] == "seattle") & (jobs["job_type"] == "internship")]
    untagged_intern = jobs[(jobs["region"].isna()) & (jobs["job_type"] == "internship")]
    seattle_intern = pd.concat([seattle_intern, untagged_intern])
    render_job_table(seattle_intern, "Seattle internship")

with tab3:
    national_ft = jobs[(jobs["region"] == "national") & (jobs["job_type"] != "internship")]
    render_job_table(national_ft, "National full-time")

with tab4:
    national_intern = jobs[(jobs["region"] == "national") & (jobs["job_type"] == "internship")]
    render_job_table(national_intern, "National internship")

with tab5:
    render_job_table(jobs, "all")

# --- SCORE BREAKDOWN (expandable) ---
st.divider()
st.subheader("Job Details")

if not jobs.empty:
    selected_job = st.selectbox(
        "Select a job to see scoring details:",
        options=jobs.index,
        format_func=lambda i: f"[{int(jobs.loc[i, 'score'])}] {jobs.loc[i, 'title']} @ {jobs.loc[i, 'company']}",
    )

    if selected_job is not None:
        job = jobs.loc[selected_job]
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"### {job['title']}")
            st.markdown(f"**{job['company']}** — {job['location']}")
            if job.get("job_url"):
                st.markdown(f"[Apply Here]({job['job_url']})")
            if job.get("description"):
                with st.expander("Full Description"):
                    st.markdown(job["description"][:3000])

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

# --- COMPANY LEADERBOARD ---
st.divider()
st.subheader("Top Companies")
if not scored.empty:
    company_stats = scored.groupby("company").agg(
        avg_score=("score", "mean"),
        count=("score", "count"),
    ).sort_values("avg_score", ascending=False).head(10).reset_index()
    company_stats["avg_score"] = company_stats["avg_score"].round(1)
    st.dataframe(company_stats.rename(columns={
        "company": "Company", "avg_score": "Avg Score", "count": "Jobs Found"
    }), hide_index=True, use_container_width=True)

# --- FOOTER ---
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Database: {DB_PATH}")
