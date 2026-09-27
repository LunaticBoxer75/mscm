"""MSCM Job Search Dashboard — Streamlit web UI.

Two data sources, deliberately disjoint:
  data/jobs_deploy.db  — scraped jobs. Read-only here; refreshed by /find-jobs.
  data/user_data.json  — her data, via src/user_store.py. Read-write here.

They must stay separate. Her data used to live in the deploy DB, so every
/find-jobs push replaced it and destroyed whatever she'd typed on the hosted
dashboard (Streamlit Cloud's filesystem is ephemeral).
"""

import html
import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from src import jobs_data, user_store

PROJECTS_DIR = Path(__file__).parent / "projects"
DB_PATH = Path(__file__).parent / "data" / "jobs_deploy.db"

st.set_page_config(page_title="MSCM Job Search", page_icon="🎯", layout="wide")


def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def dismissed_ids():
    """Job IDs she has dismissed. Lives in user_store so dismissals survive a deploy."""
    return {d["job_id"] for d in user_store.get("dismissed_jobs") if d.get("job_id")}


@st.cache_data(ttl=60)
def _load_jobs_raw(min_score):
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT * FROM jobs
        WHERE score IS NOT NULL AND score >= ?
        AND title IS NOT NULL AND title != ''
        AND company IS NOT NULL AND company != ''
        ORDER BY score DESC
    """, conn, params=(min_score,))
    conn.close()
    if df.empty:
        return df
    # Claude read this job (Pass 2) vs keyword score only (Pass 1)
    df["ai_read"] = df["score_breakdown"].fillna("").str.contains(r'"scorer"\s*:\s*"ai"', regex=True)
    # Posting date when real, else first-seen date
    posted = df["date_posted"].where(df["date_posted"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}"), None)
    df["eff_posted"] = posted.fillna(df["scraped_at"].astype(str).str[:10])
    # Thousands of jobs share a score; within a tie, Claude-read first, then newest.
    # (Without this, ties came back in arbitrary order — effectively alphabetical.)
    return df.sort_values(["score", "ai_read", "eff_posted"], ascending=False,
                          kind="stable").reset_index(drop=True)


def load_jobs(min_score=50):
    """Scored jobs, with dismissals filtered out at read time."""
    df = _load_jobs_raw(min_score)
    dropped = dismissed_ids()
    if dropped and not df.empty:
        df = df[~df["job_id"].isin(dropped)]
    return df


def applications_map():
    """job_id -> application record."""
    return {a["job_id"]: a for a in user_store.get("applications") if a.get("job_id")}


def load_applications():
    """Her applications, enriched with job details from the deploy DB."""
    apps = user_store.get("applications")
    if not apps:
        return pd.DataFrame()
    ids = [a["job_id"] for a in apps if a.get("job_id")]
    if not ids:
        return pd.DataFrame()
    conn = get_db()
    jobs = pd.read_sql_query(
        f"""SELECT job_id, title, company, location, score, job_url FROM jobs
            WHERE job_id IN ({",".join("?" * len(ids))})""",
        conn, params=ids,
    )
    conn.close()
    df = pd.DataFrame(apps).merge(jobs, on="job_id", how="left")
    order = {"interviewing": 1, "applied": 2, "offer": 3}
    df["_rank"] = df["status"].map(lambda s: order.get(s, 4))
    return df.sort_values(["_rank", "score"], ascending=[True, False]).drop(columns=["_rank"])


def dismiss_job(job_id):
    if job_id in dismissed_ids():
        return
    user_store.add("dismissed_jobs", {"job_id": job_id}, message="Job dismissed")
    _load_jobs_raw.clear()


def update_application(job_id, status, notes=None, follow_up_date=None):
    existing = applications_map().get(job_id)
    # Auto-set 7-day follow-up when applying — unless one is already queued
    if status == "applied" and not follow_up_date and not (existing or {}).get("follow_up_date"):
        follow_up_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    # None means "leave unchanged": moving to 'interviewing' must not erase her
    # notes or the queued follow-up.
    fields = {"status": status}
    if notes is not None:
        fields["notes"] = notes
    if follow_up_date is not None:
        fields["follow_up_date"] = follow_up_date
    if status == "applied" and not (existing or {}).get("applied_date"):
        fields["applied_date"] = datetime.now().isoformat()
    if existing:
        user_store.update("applications", existing["id"], fields,
                          message=f"Marked {status}")
    else:
        user_store.add("applications", {"job_id": job_id, **fields},
                       message=f"Marked {status}")


def get_application_status(job_id):
    """Current application status for a job, or None."""
    app = applications_map().get(job_id)
    return app.get("status") if app else None


def get_todays_top_jobs(limit=5):
    """Composite priority: score × freshness × not-applied."""
    df = load_jobs(min_score=70)
    if df.empty:
        return df
    acted = {jid for jid, a in applications_map().items() if a.get("status") not in (None, "new")}
    if acted:
        df = df[~df["job_id"].isin(acted)]
    return df.head(limit)  # load_jobs already ranks: score, Claude-read, newest


def get_comparable_jobs(current_job, limit=3):
    """Find similar roles to the currently selected job."""
    conn = get_db()
    title = str(current_job.get("title", "") or "")
    job_id = current_job.get("job_id", "")

    # Extract key tokens (skip generic words)
    skip_words = {"sr.", "sr", "senior", "jr.", "junior", "ii", "iii", "i", "the", "of", "and", "for", "in"}
    tokens = [t for t in title.lower().split() if t not in skip_words and len(t) > 2][:3]

    if not tokens:
        return pd.DataFrame()

    # Build LIKE clauses for each token
    where_clauses = " AND ".join([f"LOWER(title) LIKE ?" for _ in tokens])
    params = [f"%{t}%" for t in tokens]
    params.append(job_id)
    # Over-fetch so dismissed rows can be dropped below and still leave `limit`
    params.append(limit + len(dismissed_ids()))

    try:
        df = pd.read_sql_query(f"""
            SELECT job_id, title, company, location, score, salary_min, salary_max, job_url
            FROM jobs
            WHERE {where_clauses}
            AND job_id != ?
            AND score >= 60
            ORDER BY score DESC
            LIMIT ?
        """, conn, params=params)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    dropped = dismissed_ids()
    if dropped and not df.empty:
        df = df[~df["job_id"].isin(dropped)]
    return df.head(limit)


SKILLS_CHECK = {
    "Python": ["python", "pandas", "numpy"], "Tableau": ["tableau"],
    "Power BI": ["power bi", "powerbi"], "SAP/ERP": ["sap", "s/4hana", "erp"],
    "SQL": ["sql", "mysql", "postgresql"], "Excel Advanced": ["vba", "macros", "power query"],
    "Forecasting": ["forecasting", "demand planning", "s&op"],
    "Procurement": ["procurement", "sourcing", "rfp"],
    "Logistics": ["logistics", "freight", "3pl", "wms"],
    "Six Sigma": ["lean", "six sigma", "kaizen"],
    "Project Management": ["pmp", "agile", "scrum"],
}
HAS_SKILLS = {"SQL", "Six Sigma", "Project Management", "Excel Advanced"}


@st.cache_data(show_spinner=False)
def skills_gap_table(descriptions):
    """% of descriptions requesting each skill. Cached: it used to rescan every
    description on every click (~1.1s of a 2.6s rerun).

    Word boundaries, never substrings — "lean" matched "cleaning", "erp" matched
    "enterprise", "sap" matched "asap".
    """
    import re
    patterns = {
        skill: re.compile("|".join(rf"(?<![\w/]){re.escape(k)}(?![\w])" for k in kws))
        for skill, kws in SKILLS_CHECK.items()
    }
    lowered = [d.lower() for d in descriptions]
    results = []
    for skill, pat in patterns.items():
        count = sum(1 for d in lowered if pat.search(d))
        pct = round(count / len(lowered) * 100, 1) if lowered else 0
        results.append({"Skill": skill, "Requested In": f"{pct}%",
                        "Has It": "✅" if skill in HAS_SKILLS else "❌ GAP", "pct": pct})
    return sorted(results, key=lambda x: x["pct"], reverse=True)


# --- SHARED UI HELPERS ---

# Save confirmations: user_store calls this after every successful write. Queued
# in session state because most saves are followed by st.rerun(), which would
# drop a toast shown immediately.
_QUIET = ("Seed ", "Record ", "Import ")  # background writes she didn't trigger


def _queue_toast(message):
    if message and not message.startswith(_QUIET):
        st.session_state.setdefault("_toasts", []).append(message)


def flush_toasts():
    for m in st.session_state.pop("_toasts", []):
        st.toast(f"Saved — {m}", icon="✅")


user_store.on_write = _queue_toast


@st.cache_data(ttl=600, show_spinner=False)
def jobs_updated_date():
    """Date of the newest scrape in the published jobs DB."""
    conn = get_db()
    try:
        v = conn.execute("SELECT MAX(scraped_at) FROM jobs").fetchone()[0]
    except sqlite3.Error:
        v = None
    conn.close()
    return str(v)[:10] if v else None


def visit_baseline():
    """Her previous visit day, for "new since your last visit".

    Written at most once per day (one small commit). Caveat: opening the
    dashboard locally with the token set counts as her visit too.
    """
    if "visit_baseline" in st.session_state:
        return st.session_state["visit_baseline"]
    today = date.today().isoformat()
    rec = next((m for m in user_store.get("meta") if m.get("key") == "visits"), None)
    baseline = None
    try:
        if rec is None:
            user_store.add("meta", {"key": "visits", "last": today, "prev": None},
                           message="Record first visit")
        elif rec.get("last") != today:
            baseline = rec.get("last")
            user_store.update("meta", rec["id"], {"prev": baseline, "last": today},
                              message="Record visit")
        else:
            baseline = rec.get("prev")
    except user_store.StoreError:
        baseline = (rec or {}).get("prev")  # read-only mode: still show counts
    st.session_state["visit_baseline"] = baseline
    return baseline


def _safe_url(u):
    """Only http(s) links — a scraped `javascript:` URL would run on click."""
    u = str(u or "")
    return u if u.startswith(("http://", "https://")) else ""


def job_row(row, key, apps, selectable=True):
    """One job line with inline actions. Shared by the Today and Jobs pages.

    Scraped text is HTML-escaped: it's rendered with unsafe_allow_html.
    "Open" never tracks anything; only ✓ records an application.
    """
    job_id = row.get("job_id", "")
    score = int(row.get("score") or 0)
    status = (apps.get(job_id) or {}).get("status")
    dot = "🟢" if score >= 90 else "🔵" if score >= 75 else "🟡" if score >= 60 else "⚪"
    c_pick, c_info, c_sal, c_open, c_ok, c_x = st.columns([0.5, 5, 1.3, 0.8, 0.45, 0.45])
    with c_pick:
        if selectable:
            if st.button(dot, key=f"sel_{key}", help=f"Score {score} — show details"):
                st.session_state["selected_job_idx"] = row.get("index")
        else:
            st.markdown(f"<span title='Score {score}'>{dot}</span>", unsafe_allow_html=True)
    with c_info:
        ai = "🤖 " if row.get("ai_read") else ""
        st.markdown(
            f"<span style='font-size:0.9em' title='{'Claude read this posting' if ai else 'Keyword score only'}'>"
            f"{ai}<b>{html.escape(str(row.get('title', '')))}</b> @ {html.escape(str(row.get('company', '')))}"
            f" · {html.escape(str(row.get('location', '')))}</span>", unsafe_allow_html=True)
    with c_sal:
        lo, hi = row.get("salary_min"), row.get("salary_max")
        if pd.notna(lo):
            sal = f"${int(lo/1000)}K-${int(hi/1000)}K" if pd.notna(hi) else f"${int(lo/1000)}K+"
            st.markdown(f"<span style='font-size:0.85em;color:#059669'>{sal}</span>", unsafe_allow_html=True)
    with c_open:
        url = _safe_url(row.get("job_url"))
        if url:
            st.markdown(f"<a href='{html.escape(url, quote=True)}' target='_blank' rel='noopener' "
                        f"style='font-size:0.85em'>Open ↗</a>", unsafe_allow_html=True)
    with c_ok:
        if status in ("applied", "interviewing", "offer"):
            st.markdown(f"<span title='{status}'>✔️</span>", unsafe_allow_html=True)
        elif st.button("✓", key=f"ok_{key}", help="Mark applied (queues a 7-day follow-up)"):
            update_application(job_id, "applied")
            st.rerun()
    with c_x:
        if st.button("✕", key=f"x_{key}", help="Dismiss — hide this job everywhere"):
            dismiss_job(job_id)
            st.rerun()


# --- HEADER ---
st.title("🎯 MSCM Job Search Dashboard")
st.caption("Daily job identification for Bhumika Choudhary — UW Foster MSCM (Jun 2026 – May 2027)")
flush_toasts()  # confirmations queued before the last rerun


@st.cache_data(ttl=600, show_spinner=False)
def _published_jobs_sha():
    """Head of the jobs-data branch, re-checked at most every 10 minutes."""
    return jobs_data.published_sha()


# Must run before anything opens the DB: sqlite3.connect() on a missing file
# silently creates an empty one, and the app would then show zero jobs.
try:
    with st.spinner("Loading latest jobs…"):
        if jobs_data.ensure(_published_jobs_sha()):
            st.cache_data.clear()  # new jobs published — drop cached queries
except jobs_data.JobsDataError as e:
    st.error(f"⚠️ {e}")
    st.stop()

try:
    user_store.load()
except user_store.StoreError as e:
    st.error(f"⚠️ Your saved data can't be read: {e}")
    st.stop()
_updated = jobs_updated_date()
if _updated:
    _age = (date.today() - date.fromisoformat(_updated)).days
    st.caption(f"Jobs updated **{_updated}**" + (f" · ⚠️ {_age} days ago" if _age > 3 else ""))

if user_store.is_degraded():
    st.warning("⚠️ Can't reach GitHub right now — showing your last saved data. "
               "Saving is paused; changes made now would not be kept. Retrying automatically.")

def filter_jobs(df):
    if df.empty:
        return df
    filtered = df.copy()
    if "region" not in filtered.columns:
        filtered["region"] = "seattle"
    else:
        filtered["region"] = filtered["region"].fillna("seattle")
    if "job_type" not in filtered.columns:
        filtered["job_type"] = "fulltime"
    else:
        filtered["job_type"] = filtered["job_type"].fillna("fulltime")
    if region_filter != "All":
        filtered = filtered[filtered["region"] == region_filter]
    if type_filter != "All":
        filtered = filtered[filtered["job_type"] == type_filter]
    if search_query:
        q = search_query.lower()
        mask = (
            filtered["title"].fillna("").str.lower().str.contains(q, na=False) |
            filtered["company"].fillna("").str.lower().str.contains(q, na=False) |
            filtered["location"].fillna("").str.lower().str.contains(q, na=False)
        )
        filtered = filtered[mask]
    if date_filter != "All Time" and "date_posted" in filtered.columns:
        days_map = {"Last 24 hours": 1, "Last 3 days": 3, "Last 7 days": 7, "Last 30 days": 30}
        days = days_map.get(date_filter, 9999)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        # Only real ISO dates count. Undated rows (~9K LinkedIn) fall back to the
        # date we first saw them. A plain string compare used to let the literal
        # "nan" pass every filter, since "nan" > any "2026-..." string.
        posted = filtered["date_posted"].where(
            filtered["date_posted"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}"), None)
        effective = posted.fillna(filtered["scraped_at"].astype(str).str[:10])
        filtered = filtered[effective >= cutoff]
    if company_filter:
        filtered = filtered[filtered["company"].isin(company_filter)]
    if title_filter:
        filtered = filtered[filtered["title"].isin(title_filter)]
    return filtered



# === TAB: JOBS ===
def page_jobs():
    # Sidebar filters live only on this page; filter_jobs() reads them as globals.
    global search_query, min_score, region_filter, type_filter, date_filter, company_filter, title_filter, all_jobs, scored
    # --- SIDEBAR ---
    st.sidebar.header("Filters")
    search_query = st.sidebar.text_input("🔍 Search (title, company, location)", placeholder="e.g. supply chain manager")
    min_score = st.sidebar.slider("Minimum Score", 0, 100, 60)
    region_filter = st.sidebar.selectbox("Region", ["All", "seattle", "national"])
    type_filter = st.sidebar.selectbox("Job Type", ["All", "fulltime", "internship"])
    date_options = ["Last 30 days", "Last 7 days", "Last 3 days", "Last 24 hours", "All Time"]
    date_filter = st.sidebar.selectbox("Posted", date_options, index=0)

    # Company filter
    company_options = ["All Companies"]
    if DB_PATH.exists():
        _conn = get_db()
        top_companies = _conn.execute("""
            SELECT company, COUNT(*) as cnt FROM jobs
            WHERE score >= 60 AND (dismissed IS NULL OR dismissed = 0)
            AND company IS NOT NULL AND company != ''
            GROUP BY company ORDER BY cnt DESC LIMIT 50
        """).fetchall()
        _conn.close()
        company_options += [r[0] for r in top_companies]
    company_filter = st.sidebar.multiselect("Company", company_options[1:], default=[], placeholder="Type to search companies...")
    if not company_filter:
        company_filter = None

    # Job title filter
    title_options = ["All Titles"]
    if DB_PATH.exists():
        _conn2 = get_db()
        top_titles = _conn2.execute("""
            SELECT title, COUNT(*) as cnt FROM jobs
            WHERE score >= 60 AND (dismissed IS NULL OR dismissed = 0)
            AND title IS NOT NULL AND title != ''
            GROUP BY title ORDER BY cnt DESC LIMIT 50
        """).fetchall()
        _conn2.close()
        title_options += [r[0] for r in top_titles]
    title_filter = st.sidebar.multiselect("Job Title", title_options[1:], default=[], placeholder="Type to search titles...")
    if not title_filter:
        title_filter = None

    # --- LOAD DATA ---
    all_jobs = load_jobs(min_score=min_score)
    scored = all_jobs if not all_jobs.empty else pd.DataFrame()

    # --- METRICS ---
    if not scored.empty:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Showing", len(scored))
        col2.metric("Score 75+", len(scored[scored["score"] >= 75]))
        col3.metric("Score 60-74", len(scored[(scored["score"] >= 60) & (scored["score"] < 75)]))
        col4.metric("Avg Salary", f"${scored['salary_min'].dropna().mean()/1000:.0f}K" if scored["salary_min"].notna().any() else "—")

        st.divider()

    if scored.empty:
        st.info("No scored jobs yet. Run `/find-jobs` in Claude Code.")
    else:
        jobs = filter_jobs(scored)
        # Full-time first: internships are a fallback only (UW CPT one-year rule, 2026-09-23).
        sub_tabs = st.tabs(["Seattle FT", "National FT", "Seattle Intern (fallback)",
                            "National Intern (fallback)", "All"])

        def render_table(df, name, key):
            if df.empty:
                st.info(f"No {name} jobs matching filters.")
                return
            display = df.reset_index(drop=False)

            # Paginate — show 25 at a time for fast interaction
            page_size = 25
            page_key = f"page_{key}"
            if page_key not in st.session_state:
                st.session_state[page_key] = 0
            page = st.session_state[page_key]
            total_pages = (len(display) - 1) // page_size + 1
            page_slice = display.iloc[page * page_size:(page + 1) * page_size]

            apps = applications_map()
            with st.container(height=400):
                for i, row in page_slice.iterrows():
                    job_row(row, f"{key}_{i}", apps)

            # Pagination controls
            if total_pages > 1:
                pc1, pc2, pc3 = st.columns([1, 2, 1])
                with pc1:
                    if page > 0 and st.button("← Prev", key=f"prev_{key}"):
                        st.session_state[page_key] = page - 1
                        st.rerun()
                with pc2:
                    st.caption(f"Page {page+1}/{total_pages} ({len(display)} jobs)")
                with pc3:
                    if page < total_pages - 1 and st.button("Next →", key=f"next_{key}"):
                        st.session_state[page_key] = page + 1
                        st.rerun()

        with sub_tabs[0]:
            sea_ft = jobs[(jobs["region"] == "seattle") & (jobs["job_type"] != "internship")]
            render_table(sea_ft, "Seattle full-time", "t_sea_ft")
        with sub_tabs[1]:
            nat_ft = jobs[(jobs["region"] == "national") & (jobs["job_type"] != "internship")]
            render_table(nat_ft, "National full-time", "t_nat_ft")
        with sub_tabs[2]:
            sea_int = jobs[(jobs["region"] == "seattle") & (jobs["job_type"] == "internship")]
            render_table(sea_int, "Seattle internship", "t_sea_int")
        with sub_tabs[3]:
            nat_int = jobs[(jobs["region"] == "national") & (jobs["job_type"] == "internship")]
            render_table(nat_int, "National internship", "t_nat_int")
        with sub_tabs[4]:
            render_table(jobs, "all", "t_all")

        # Job detail panel
        if not jobs.empty:
            st.divider()
            sel_idx = st.session_state.get("selected_job_idx")
            if sel_idx is None or sel_idx not in jobs.index:
                sel_idx = jobs.index[0]
            job = jobs.loc[sel_idx]

            from src.sponsor_data import get_sponsor_badge
            badge_emoji, badge_label, badge_color = get_sponsor_badge(str(job.get("company", "") or ""))

            st.markdown(f"### 📄 {job['title']}")
            st.markdown(f"**{job['company']}** · {job.get('location', '')} · Score: **{int(job['score'])}/100**")
            st.markdown(f"{badge_emoji} **Visa:** {badge_label}")

            c1, c2 = st.columns([2, 1])
            with c1:
                if job.get("job_url"):
                    st.markdown(f"🔗 [Apply Here]({job['job_url']})")
                if job.get("description"):
                    with st.expander("Full Description"):
                        st.markdown(str(job["description"])[:3000])
            with c2:
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
                tc1, tc2 = st.columns(2)
                with tc1:
                    if track_st != "—" and st.button("Update Status"):
                        update_application(job.get("job_id", ""), track_st)
                        st.success(f"Marked as {track_st}!")
                        st.rerun()
                with tc2:
                    if st.button("🗑️ Dismiss"):
                        dismiss_job(job.get("job_id", ""))
                        st.success("Removed!")
                        st.rerun()

            # Referral links for selected job
            import urllib.parse
            company = str(job.get("company", "") or "")
            title = str(job.get("title", "") or "")
            job_id_curr = job.get("job_id", "")

            if company:
                # Comparable roles (B5)
                comparable = get_comparable_jobs(job, limit=3)
                if not comparable.empty:
                    st.markdown("---")
                    st.markdown("#### 🔗 Similar Roles")
                    for _, c in comparable.iterrows():
                        sal = ""
                        if pd.notna(c.get("salary_min")) and pd.notna(c.get("salary_max")):
                            sal = f" · ${int(c['salary_min']/1000)}K-${int(c['salary_max']/1000)}K"
                        c_cols = st.columns([0.3, 5, 1])
                        with c_cols[0]:
                            st.markdown(f"`{int(c['score'])}`")
                        with c_cols[1]:
                            st.markdown(f"**{c['title']}** @ {c['company']} · {c['location']}{sal}")
                        with c_cols[2]:
                            if c.get("job_url"):
                                st.link_button("Apply", c["job_url"], width="stretch")

                st.markdown("---")
                st.markdown("#### ⚡ Quick Actions")
                applied_status = get_application_status(job_id_curr)
                act_cols = st.columns([1.5, 1.5, 3])
                with act_cols[0]:
                    if job.get("job_url"):
                        st.link_button("📝 Open Posting", job["job_url"], width="stretch")
                with act_cols[1]:
                    if applied_status == "applied":
                        st.success("✓ Applied")
                    else:
                        if st.button("✅ Mark Applied", width="stretch", help="Marks applied + queues 7-day follow-up"):
                            update_application(job_id_curr, "applied")
                            st.success("Marked applied + 7-day follow-up queued!")
                            st.rerun()
                with act_cols[2]:
                    connect_msg = f"Hi [Name],\n\nI'm Bhumika — incoming MSCM student at UW Foster with 3 years of operations/risk experience at Uber. I'm very interested in the {title} role at {company} and would really appreciate a referral if you think my background could be a fit. I've attached my resume for reference. Thank you!\n\nBest,\nBhumika"
                    st.code(connect_msg, language=None)
                    st.caption("Copy → replace [Name] → paste into LinkedIn")

                st.markdown("#### 🤝 Find People at " + company)
                role_kw = title.lower().replace("sr.", "").replace("senior", "").strip()
                ref_cols = st.columns(4)
                ref_cols[0].link_button("👥 Same Role", f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(role_kw)}&company={urllib.parse.quote(company)}", width="stretch")
                ref_cols[1].link_button("🎯 Recruiters", f"https://www.linkedin.com/search/results/people/?keywords=recruiter%20talent%20acquisition&company={urllib.parse.quote(company)}", width="stretch")
                ref_cols[2].link_button("📦 SC Team", f"https://www.linkedin.com/search/results/people/?keywords=supply%20chain%20procurement&company={urllib.parse.quote(company)}", width="stretch")
                ref_cols[3].link_button("🎓 UW Alumni", f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(company)}&schoolFilter=%5B%222584%22%5D", width="stretch")

                # Resume tailor (B1+B2)
                desc = job.get("description", "") or ""
                if desc:
                    with st.expander("📝 Tailor Resume for This Job", expanded=False):
                        from src.resume_rephraser import (
                            keyword_match_analysis, rephrase_all_bullets, generate_tailored_docx
                        )

                        matched, missing = keyword_match_analysis(desc)

                        # ATS keyword chips
                        st.markdown("**ATS Keyword Match**")
                        kc1, kc2 = st.columns(2)
                        with kc1:
                            st.markdown("✅ **In your resume:**")
                            if matched:
                                st.markdown(" · ".join([f"`{k}`" for k in matched]))
                            else:
                                st.caption("None of the JD's key terms found")
                        with kc2:
                            st.markdown("❌ **Missing — consider adding:**")
                            if missing:
                                st.markdown(" · ".join([f"`{k}`" for k in missing]))
                            else:
                                st.caption("Resume covers all key terms")

                        st.markdown("---")
                        st.markdown("**Suggested Rephrases**")
                        rephrases = rephrase_all_bullets(desc)
                        any_changes = False
                        for r in rephrases:
                            if r["changed"]:
                                any_changes = True
                                st.markdown(f"- ~~{r['original']}~~")
                                st.markdown(f"  → **{r['rephrased']}**")
                                if r["changes"]:
                                    st.caption(f"  Changes: {', '.join(r['changes'])}")
                        if not any_changes:
                            st.caption("No automatic rephrases suggested — your bullets already match well.")

                        # Download DOCX
                        st.markdown("---")
                        try:
                            docx_buf = generate_tailored_docx(desc)
                            if docx_buf:
                                st.download_button(
                                    "📥 Download Tailored Resume Bullets (DOCX)",
                                    data=docx_buf,
                                    file_name=f"resume-bullets-{company.replace(' ','_')}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                )
                        except Exception as e:
                            st.caption(f"DOCX generation unavailable: {e}")

# === TAB: TRACKER ===
def page_tracker():
    st.subheader("Application Pipeline")
    apps = load_applications()
    if apps.empty:
        st.info("No applications tracked yet. Select a job → Update Status.")
    else:
        statuses = ["applied", "interviewing", "offer", "rejected", "skipped"]
        status_counts = apps["status"].value_counts() if "status" in apps.columns else pd.Series()
        cols = st.columns(5)
        emojis = ["📨", "🎤", "🎉", "❌", "⏭️"]
        for col, status, emoji in zip(cols, statuses, emojis):
            col.metric(f"{emoji} {status.title()}", status_counts.get(status, 0))
        st.divider()
        display_cols = [c for c in ["status", "title", "company", "score", "applied_date", "notes"] if c in apps.columns]
        st.dataframe(apps[display_cols], hide_index=True, width="stretch")

# === TAB: REFERRALS ===
def page_referrals():
    scored = load_jobs(min_score=60)
    st.subheader("🤝 Find People for Referrals")
    if scored.empty:
        st.info("No scored jobs yet.")
    else:
        import urllib.parse
        top_jobs = scored[scored["score"] >= 75].head(20)
        seen_companies = set()
        for _, job in top_jobs.iterrows():
            company = str(job.get("company", "") or "")
            if not company or company in seen_companies:
                continue
            seen_companies.add(company)
            title = str(job.get("title", "") or "")
            role_kw = title.lower().replace("sr.", "").replace("senior", "").strip()
            with st.expander(f"**{company}** — {title} · {job.get('location', '')}"):
                ref_cols = st.columns(4)
                ref_cols[0].link_button("👥 Same Role", f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(role_kw)}&company={urllib.parse.quote(company)}", width="stretch")
                ref_cols[1].link_button("🎯 Recruiters", f"https://www.linkedin.com/search/results/people/?keywords=recruiter%20talent%20acquisition&company={urllib.parse.quote(company)}", width="stretch")
                ref_cols[2].link_button("📦 SC Team", f"https://www.linkedin.com/search/results/people/?keywords=supply%20chain%20procurement&company={urllib.parse.quote(company)}", width="stretch")
                ref_cols[3].link_button("🎓 UW Alumni", f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(company)}&schoolFilter=%5B%222584%22%5D", width="stretch")
                msg = f"Hi [Name], I'm Bhumika — incoming MSCM student at UW Foster with 3 years of operations/risk experience at Uber. I'm very interested in the {title} role at {company} and would really appreciate a referral if you think my background could be a fit. I've attached my resume for reference. Thank you!"
                st.code(msg, language=None)

# === TAB: SPONSORS ===
def page_sponsors():
    st.subheader("🛂 Top H1B / STEM-OPT Sponsors for Supply Chain")
    st.caption("E-Verify enrolled employers that sponsor F1/H1B for SCM/Operations roles. STEM OPT extension (24 months) requires E-Verify.")

    from src.sponsor_data import get_top_sponsors_for_scm

    top_sponsors = get_top_sponsors_for_scm()
    volume_emoji = {"very_high": "🟢", "high": "🟢", "medium": "🟡", "low": "🟡"}

    st.markdown(f"**{len(top_sponsors)} target companies** — apply directly at their careers pages, even if not in our scrape:")
    st.markdown("")

    # 3-column layout
    cols = st.columns(3)
    for i, sponsor in enumerate(top_sponsors):
        with cols[i % 3]:
            emoji = volume_emoji.get(sponsor["h1b_volume"], "⚪")
            careers_url = f"https://www.google.com/search?q={sponsor['company'].replace(' ', '+')}+careers+supply+chain"
            st.markdown(f"{emoji} **[{sponsor['company']}]({careers_url})**")
            st.caption(f"H1B volume: {sponsor['h1b_volume'].replace('_',' ')}")

    # Verified top sponsors from USCIS data
    st.divider()
    try:
        import json as _json
        from pathlib import Path as _P
        vpath = _P(__file__).parent / "config" / "h1b_sponsors_verified.json"
        if vpath.exists():
            vdata = _json.loads(vpath.read_text())
            sponsors = vdata.get("sponsors", {})
            fy = vdata.get("fiscal_year", "")
            st.markdown(f"### 📊 Top 40 H1B Sponsors — USCIS Verified (FY{fy})")
            st.caption(f"Actual petition approval counts from {vdata.get('source','USCIS')}. These are the highest-volume sponsors nationally.")
            top40 = list(sponsors.items())[:40]
            vc = st.columns(2)
            for i, (norm, d) in enumerate(top40):
                with vc[i % 2]:
                    careers = f"https://www.google.com/search?q={d['employer'].replace(' ', '+')}+careers"
                    st.markdown(f"{i+1}. **[{d['employer'].title()}]({careers})** — {d['h1b_approvals']:,} approvals")
            st.caption("Note: Top nationally = mostly tech/consulting. Use the SCM-focused list above for role-relevant targets. Refresh with `python scripts/refresh_h1b_sponsors.py`.")
    except Exception as e:
        st.caption(f"Verified data unavailable: {e}")

    st.divider()
    st.info("""
    **Why this matters for STEM OPT:** Bhumika's MSCM is STEM-designated, giving her 36 months of OPT.
    But the 24-month extension REQUIRES the employer to be E-Verify enrolled. The SCM list above is
    curated for role relevance; the verified list shows actual USCIS approval volume.

    **Strategy:** Apply directly at these companies' careers pages, not just from job board scrapes.
    """)

# === TAB: SKILLS GAP ===
def page_skills():
    scored = load_jobs(min_score=60)
    st.subheader("Skills Gap Analysis")
    if scored.empty or len(scored) < 5:
        st.info("Need at least 5 scored jobs.")
    else:
        results = skills_gap_table(tuple(scored[scored["score"] >= 55]["description"].dropna()))
        st.dataframe(pd.DataFrame(results).drop(columns=["pct"]), hide_index=True, width="stretch")

# === TAB: SKILLS INSIGHTS ===
def page_insights():
    scored = load_jobs(min_score=60)
    st.subheader("📈 Skills & Certifications Demand")
    st.caption("What employers ask for across all relevant job descriptions (score 60+). ✅ = Bhumika already has it, ❌ = gap to build.")

    from src.skills_insights import analyze_skills

    @st.cache_data(ttl=600)
    def _cached_skills():
        return analyze_skills(min_score=60)

    insights = _cached_skills()
    if insights["total"] == 0:
        st.info("No scored jobs to analyze yet.")
    else:
        st.markdown(f"_Analyzed **{insights['total']:,}** job descriptions_")

        def render_skill_table(items, title):
            st.markdown(f"#### {title}")
            df = pd.DataFrame([{
                "Skill": r["skill"],
                "Demand": f"{r['pct']}%",
                "Status": "✅ Have" if r.get("has") else "❌ Gap",
                "_pct": r["pct"],
            } for r in items[:12]])
            st.dataframe(
                df.drop(columns=["_pct"]),
                hide_index=True, width="stretch",
                column_config={"Demand": st.column_config.TextColumn(width="small")},
            )

        c1, c2 = st.columns(2)
        with c1:
            render_skill_table(insights["technical"], "🔧 Top Technical Skills")
        with c2:
            render_skill_table(insights["soft"], "🤝 Top Management / Soft Skills")

        render_skill_table(insights["certs"], "📜 Certifications Mentioned")

        # Highlight top gaps
        tech_gaps = [r for r in insights["technical"] if not r.get("has") and r["pct"] >= 8][:4]
        if tech_gaps:
            st.divider()
            st.markdown("#### 🎯 Highest-ROI Skill Gaps to Close")
            for g in tech_gaps:
                st.markdown(f"- **{g['skill']}** — requested in {g['pct']}% of relevant jobs")

# === TAB: FELLOWSHIPS ===
def page_fellowships():
    st.subheader("🏆 Fellowships, Competitions & Programs")
    st.caption("Curated SCM/Operations opportunities for an F1 MSCM student. Verify live dates each fall — most LDPs recruit Aug-Nov for next year.")

    import json as _json
    opp_path = Path(__file__).parent / "config" / "opportunities.json"
    if opp_path.exists():
        opps = _json.loads(opp_path.read_text())

        section_meta = [
            ("case_competitions", "🎓 Case Competitions"),
            ("hackathons_datathons", "💻 Hackathons & Datathons"),
            ("rotational_ldps", "🔄 Rotational / Leadership Development Programs"),
            ("fellowships", "🎖️ Fellowships & Scholarships"),
            ("associations", "🤝 Professional Associations"),
        ]

        for key, title in section_meta:
            items = opps.get(key, [])
            if not items:
                continue
            st.markdown(f"### {title}")
            for o in items:
                f1 = o.get("f1_ok")
                flag = "🟢" if f1 else "🟡"
                tier = f" · _{o['tier']}_" if o.get("tier") else ""
                with st.expander(f"{flag} **{o['name']}** — {o['org']}{tier}"):
                    st.markdown(f"**Timeline:** {o.get('timeline','—')}")
                    st.markdown(f"**Eligibility:** {o.get('eligibility','—')}")
                    st.markdown(f"**About:** {o.get('desc','')}")
                    if o.get("url"):
                        st.markdown(f"[Official page →]({o['url']})")
            st.markdown("")

        st.divider()
        st.info("🟢 = F1-friendly / no visa barrier · 🟡 = verify sponsorship per posting. "
                "**Tip:** Frame applications around STEM-OPT eligibility (3-yr work authorization, no employer petition) to bypass many 'no sponsorship' filters.")
    else:
        st.info("Opportunities data not found.")

# === TAB: PROJECTS ===
def page_projects():
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

# === TAB: TO-DOS ===
def page_todos():
    st.subheader("✅ To-Dos & Action Items")
    st.caption("Auto-imports action items from coffee chats. Add your own too.")

    from src.todos import get_todos, add_todo, set_status, import_coffee_chat_actions, seed_defaults

    # Sync latest coffee chat actions
    import_coffee_chat_actions()

    todos = get_todos()
    open_todos = [t for t in todos if t["status"] == "open"]
    done_todos = [t for t in todos if t["status"] == "done"]

    c1, c2 = st.columns(2)
    c1.metric("Open", len(open_todos))
    c2.metric("Done", len(done_todos))

    st.markdown("### 📌 Open")
    if not open_todos:
        st.success("All caught up!")
    else:
        # Group by category
        cats = {}
        for t in open_todos:
            cats.setdefault(t.get("category", "general"), []).append(t)
        for cat, items in sorted(cats.items()):
            st.markdown(f"**{cat.replace('-', ' ').title()}**")
            for t in items:
                cols = st.columns([0.5, 6, 1.2])
                with cols[0]:
                    if st.button("✓", key=f"done_{t['id']}", help="Mark done"):
                        set_status(t["id"], "done")
                        st.rerun()
                with cols[1]:
                    pri = t.get("priority", "medium")
                    pri_emoji = "🔴" if pri == "high" else "🟡" if pri == "medium" else "⚪"
                    st.markdown(f"{pri_emoji} {t['item']}")
                    if t.get("source") and t["source"] != "manual":
                        st.caption(f"from {t['source']}")

    if done_todos:
        with st.expander(f"✅ Completed ({len(done_todos)})"):
            for t in done_todos:
                dc = st.columns([6, 1])
                dc[0].markdown(f"~~{t['item']}~~")
                if dc[1].button("↩", key=f"reopen_{t['id']}", help="Reopen"):
                    set_status(t["id"], "open")
                    st.rerun()

    st.divider()
    st.markdown("### ➕ Add To-Do")
    with st.form("add_todo_form"):
        new_item = st.text_input("Task")
        tc1, tc2 = st.columns(2)
        new_cat = tc1.text_input("Category", value="general")
        new_pri = tc2.selectbox("Priority", ["high", "medium", "low"], index=1)
        if st.form_submit_button("Add") and new_item:
            add_todo(new_item, category=new_cat, priority=new_pri)
            st.success("Added!")
            st.rerun()

# === TAB: INTERVIEW PREP ===
def page_interview():
    st.subheader("🎤 Interview Prep")

    from src import prep_content as pc
    from src.interview_prep import (
        get_recommendations, seed_shivam_recommendations,
        get_stories, add_story, delete_story, STORY_THEMES, story_coverage,
        generate_mock_interview, get_interview_experience_sources,
        save_mock_session, get_mock_sessions, delete_mock_session, practice_cadence,
    )
    seed_shivam_recommendations()

    # --- Context bar: domain focus + which company she's prepping for ---
    apps_df = load_applications()
    tracked = []
    if not apps_df.empty and "company" in apps_df.columns:
        tracked = sorted({c for c in apps_df["company"].dropna() if str(c).strip()})

    ctx1, ctx2, ctx3 = st.columns([2, 2, 1.4])
    domain = ctx1.selectbox("Focus domain", ["All"] + pc.DOMAINS, key="prep_domain")
    target = ctx2.selectbox(
        "Prepping for", ["(no specific company)"] + tracked, key="prep_target",
        help="Companies from your Tracker. Pick one to see its loop, values, and relevant cases.",
    )
    cad = practice_cadence()
    if cad["days_since"] is None:
        ctx3.metric("Last mock", "never", delta="overdue", delta_color="inverse")
    else:
        ctx3.metric("Last mock", f"{cad['days_since']}d ago",
                    delta="overdue" if cad["overdue"] else "on track",
                    delta_color="inverse" if cad["overdue"] else "normal")

    company = pc.find_company(target) if target != "(no specific company)" else None
    if target != "(no specific company)" and not company:
        st.caption(f"No curated prep for **{target}** yet — showing generic guidance. "
                   "Company Prep lists who is covered.")

    iv_sub = st.tabs([
        "🗺️ Loop Map", "🧩 Frameworks", "🧪 Case Bank", "⭐ STAR Stories",
        "🎯 Mock", "🏢 Company Prep", "📚 Resources",
    ])

    # ============ 1. LOOP MAP ============
    with iv_sub[0]:
        st.caption("What each round actually screens for, and how to prepare for it. "
                   "Mentor advice is attached to the round where it applies.")

        if company and company.get("interview_format"):
            st.info(f"**{company['name']} loop:** {company['interview_format']}")

        recs = get_recommendations()
        by_cat = {}
        for r in recs:
            by_cat.setdefault(r["category"], []).append(r)

        stages = pc.by_domain(pc.loop_map(), domain)
        if not stages:
            st.warning("Loop map content missing — check content/loop_map.json.")
        for s in stages:
            with st.expander(f"**{s.get('order')}. {s.get('stage')}** · {s.get('typical_duration','')} · {s.get('who','')}"):
                st.markdown(f"**What happens:** {s.get('what_happens','')}")
                st.markdown(f"**What they screen for:** {s.get('what_they_screen_for','')}")
                if s.get("how_to_prepare"):
                    st.markdown("**How to prepare**")
                    for a in s["how_to_prepare"]:
                        st.markdown(f"- {a}")
                if s.get("common_mistakes"):
                    st.markdown("**Common mistakes**")
                    for m in s["common_mistakes"]:
                        st.markdown(f"- {m}")
                if s.get("f1_notes"):
                    st.warning(f"🛂 **F-1 note:** {s['f1_notes']}")

        st.divider()
        st.markdown("### 💡 Mentor recommendations")
        st.caption("From coffee chats. Grouped by theme.")
        for cat, items in by_cat.items():
            st.markdown(f"**{cat}**")
            for r in items:
                st.markdown(f"- {r['recommendation']}")
                who = r.get("recommended_by") or ""
                role = f", {r['person_role']}" if r.get("person_role") else ""
                if who:
                    st.caption(f"— {who}{role}")

    # ============ 2. FRAMEWORKS ============
    with iv_sub[1]:
        st.caption("Named, citable frameworks. Never cite one you cannot define — interviewers probe.")
        fws = pc.by_domain(pc.frameworks(), domain)
        st.markdown(f"**{len(fws)} frameworks** for {domain}")
        for f in fws:
            with st.expander(f"**{f.get('name')}** — {f.get('one_liner','')}"):
                st.markdown(f"**When to use:** {f.get('when_to_use','')}")
                if f.get("steps"):
                    st.markdown("**Steps**")
                    for i, stp in enumerate(f["steps"], 1):
                        st.markdown(f"{i}. **{stp.get('label','')}** — {stp.get('detail','')}")
                if f.get("worked_example"):
                    st.markdown("**Worked example**")
                    st.info(f["worked_example"])
                src_name, src_url = f.get("source_name", ""), f.get("source_url", "")
                if src_url:
                    st.caption(f"Source: [{src_name}]({src_url}) · {f.get('license_note','')}")
                elif src_name:
                    st.caption(f"Source: {src_name} · {f.get('license_note','')}")

    # ============ 3. CASE BANK ============
    with iv_sub[2]:
        st.caption("Worked cases. Read the prompt, answer out loud, THEN open the structure — "
                   "reading the answer first teaches you nothing.")

        cases = pc.by_domain(pc.cases(), domain)
        cb1, cb2 = st.columns([1, 3])
        diff = cb1.selectbox("Difficulty", ["All", "core", "stretch"], key="case_diff")
        if diff != "All":
            cases = [c for c in cases if c.get("difficulty") == diff]
        cb2.markdown(f"### {len(cases)} cases")

        for c in cases:
            badge = "🔴" if c.get("difficulty") == "stretch" else "🟢"
            with st.expander(f"{badge} **{c.get('title')}** · {c.get('domain')}"
                             + (f" · {c['framework']}" if c.get("framework") else "")):
                st.markdown(f"> {c.get('prompt','')}")
                st.caption(f"Screens for: {c.get('why_asked','')}")

                st.text_area("Your answer (practice before revealing)",
                             key=f"case_ans_{c.get('id')}", height=100,
                             placeholder="Structure your answer here first…")

                with st.expander("🔓 Reveal answer structure"):
                    if c.get("framework"):
                        st.markdown(f"**Framework:** {c['framework']}")
                    st.markdown("**How a strong answer walks through it**")
                    for i, s in enumerate(c.get("structure", []), 1):
                        st.markdown(f"{i}. {s}")
                    if c.get("quant_hooks"):
                        st.markdown("**Numbers they may push on**")
                        for q in c["quant_hooks"]:
                            st.markdown(f"- {q}")
                    gs1, gs2 = st.columns(2)
                    with gs1:
                        st.markdown("**✅ Good signals**")
                        for g in c.get("good_signals", []):
                            st.markdown(f"- {g}")
                    with gs2:
                        st.markdown("**❌ Failure modes**")
                        for fm in c.get("failure_modes", []):
                            st.markdown(f"- {fm}")
                    if c.get("followups"):
                        st.markdown("**Follow-ups to expect**")
                        for fu in c["followups"]:
                            st.markdown(f"- {fu}")
                    if c.get("bhumika_angle"):
                        st.success(f"**Your angle:** {c['bhumika_angle']}")

    # ============ 4. STAR STORIES ============
    with iv_sub[3]:
        cov = story_coverage()
        total = len(STORY_THEMES)
        st.progress(len(cov["covered"]) / total if total else 0,
                    text=f"Story coverage: {len(cov['covered'])}/{total} themes")
        if cov["missing"]:
            st.warning("**No story yet for:** " + " · ".join(cov["missing"])
                       + "\n\nA gap here is the most common cause of a blown behavioral round.")
        else:
            st.success("Every behavioral theme has at least one story.")

        st.caption("Say \"I\", not \"we\". Quantify the Result. Expect three layers of follow-up.")
        stories = get_stories()

        if stories:
            by_theme = {}
            for s in stories:
                by_theme.setdefault(s["theme"], []).append(s)
            for theme, items in by_theme.items():
                st.markdown(f"#### {theme} ({len(items)})")
                for s in items:
                    with st.expander(s["title"]):
                        st.markdown(f"**Situation:** {s.get('situation','')}")
                        st.markdown(f"**Task:** {s.get('task','')}")
                        st.markdown(f"**Action:** {s.get('action','')}")
                        st.markdown(f"**Result:** {s.get('result','')}")
                        if s.get("tags"):
                            st.caption(f"Tags: {s['tags']}")
                        if st.button("Delete", key=f"del_story_{s['id']}"):
                            delete_story(s["id"])
                            st.rerun()

            import io, csv
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["Theme", "Title", "Situation", "Task", "Action", "Result", "Tags"])
            for s in stories:
                w.writerow([s.get("theme"), s.get("title"), s.get("situation"),
                            s.get("task"), s.get("action"), s.get("result"), s.get("tags", "")])
            st.download_button("📥 Export All Stories (CSV → open in Excel)",
                               buf.getvalue(), "star_stories.csv", "text/csv")
        else:
            st.info("No stories yet. Add your first below.")

        st.divider()
        st.markdown("### ➕ Add STAR Story")
        default_theme = cov["missing"][0] if cov["missing"] else STORY_THEMES[0]
        with st.form("add_story_form"):
            s_title = st.text_input("Story title (short label)")
            s_theme = st.selectbox("Behavioral theme", STORY_THEMES,
                                   index=STORY_THEMES.index(default_theme))
            s_sit = st.text_area("Situation")
            s_task = st.text_area("Task")
            s_action = st.text_area("Action")
            s_result = st.text_area("Result (with metrics if possible)")
            s_tags = st.text_input("Tags (optional, comma-separated)")
            if st.form_submit_button("Save Story") and s_title:
                add_story(s_title, s_theme, s_sit, s_task, s_action, s_result, s_tags)
                st.success("Saved!")
                st.rerun()

    # ============ 5. MOCK ============
    with iv_sub[4]:
        if cad["overdue"]:
            st.warning("Mock is overdue — the cadence your mentor recommended is one every 2 weeks.")
        st.caption("UW Foster's EY Center for Career Advancement runs free mock interviews in "
                   "functional, behavioral, and case formats. Use this for solo reps between those.")

        if "mock_questions" not in st.session_state:
            st.session_state["mock_questions"] = generate_mock_interview(5)
        mc1, mc2 = st.columns([1, 1])
        if mc1.button("🎲 New mock (5 questions)"):
            st.session_state["mock_questions"] = generate_mock_interview(5)
            st.rerun()
        mock_company = mc2.text_input("Company (optional, saved with the session)",
                                      value="" if not company else company["name"])

        st.markdown("---")
        qs = st.session_state["mock_questions"]
        answers = {}
        for i, q in enumerate(qs, 1):
            st.markdown(f"**Q{i}. [{q['category']}]**")
            st.markdown(f"> {q['question']}")
            answers[i] = st.text_area(f"Answer Q{i}", key=f"mock_ans_{i}", height=80,
                                      label_visibility="collapsed")

        if st.button("💾 Save this session", type="primary"):
            if any(a.strip() for a in answers.values()):
                save_mock_session(qs, answers, company=mock_company)
                st.success("Saved. Strong answers here are your first draft of a STAR story.")
                st.rerun()
            else:
                st.warning("Nothing to save — write at least one answer first.")

        past = get_mock_sessions()
        if past:
            st.divider()
            st.markdown(f"### 📜 Past sessions ({len(past)})")
            for sess in past:
                label = f"{sess.get('date','')}"
                if sess.get("company"):
                    label += f" · {sess['company']}"
                answered = sum(1 for it in sess.get("items", []) if (it.get("answer") or "").strip())
                with st.expander(f"{label} — {answered}/{len(sess.get('items', []))} answered"):
                    for it in sess.get("items", []):
                        st.markdown(f"**[{it.get('category','')}]** {it.get('question','')}")
                        if (it.get("answer") or "").strip():
                            st.markdown(f"> {it['answer']}")
                        else:
                            st.caption("— not answered —")
                    if st.button("Delete session", key=f"del_mock_{sess['id']}"):
                        delete_mock_session(sess["id"])
                        st.rerun()

        pb = pc.playbook()
        proto = pb.get("self_mock_protocol") or {}
        if proto:
            st.divider()
            with st.expander("🤖 Run a rigorous solo mock with an LLM"):
                st.markdown(proto.get("summary", ""))
                for i, s in enumerate(proto.get("steps", []), 1):
                    st.markdown(f"{i}. {s}")
                if proto.get("prompt_template"):
                    st.markdown("**Paste this into Claude or ChatGPT:**")
                    st.code(proto["prompt_template"], language="text")

    # ============ 6. COMPANY PREP ============
    with iv_sub[5]:
        st.caption("Values, loop format, and F-1 posture per company. "
                   "Unverified entries say so — do not treat them as fact.")
        comps = pc.companies()
        names = [c["name"] for c in comps]
        pick = st.selectbox(
            "Company", names,
            index=names.index(company["name"]) if company and company["name"] in names else 0,
        )
        c = next((x for x in comps if x["name"] == pick), None)
        if c:
            if not c.get("verified"):
                st.warning("⚠️ Not verified from an official source this session — "
                           "confirm before relying on it.")
            st.markdown(f"**HQ:** {c.get('hq','—')}")
            st.markdown(f"**Why it matters for you:** {c.get('why_relevant','')}")
            if c.get("interview_format"):
                st.info(f"**Loop:** {c['interview_format']}")
            if c.get("values"):
                st.markdown(f"### {c.get('values_framework') or 'Values'} ({len(c['values'])})")
                for v in c["values"]:
                    st.markdown(f"- **{v.get('name')}** — {v.get('detail','')}")
            if c.get("prep_notes"):
                st.markdown("### Prep notes")
                for n in c["prep_notes"]:
                    st.markdown(f"- {n}")
            if c.get("visa_note"):
                st.markdown(f"🛂 **Visa/sponsorship:** {c['visa_note']}")
            if c.get("links"):
                st.markdown("### Official links")
                for l in c["links"]:
                    st.markdown(f"- [{l.get('label')}]({l.get('url')})")

            stories = get_stories()
            if c.get("values") and stories:
                st.divider()
                st.markdown("### Map your stories to their values")
                st.caption("Tag a story with a value name and it shows up here.")
                for v in c["values"]:
                    matched = [s for s in stories
                               if v.get("name", "").lower() in (s.get("tags", "") or "").lower()]
                    icon = "✅" if matched else "⬜"
                    st.markdown(f"{icon} **{v.get('name')}** — "
                                + (", ".join(s["title"] for s in matched) if matched else "_no story tagged_"))

    # ============ 7. RESOURCES ============
    with iv_sub[6]:
        st.caption("Curated and link-out only — we deliberately do not scrape these. "
                   "Grouped by what you'd reach for.")

        groups = pc.resources()
        total_items = sum(len(g.get("items", [])) for g in groups)
        st.markdown(f"**{total_items} resources** across {len(groups)} groups")

        rc1, rc2 = st.columns(2)
        cost_filter = rc1.multiselect(
            "Cost", ["Free", "Freemium", "Paid", "Free with UW login"], default=[])
        group_names = [g.get("group", "") for g in groups]
        group_filter = rc2.multiselect("Group", group_names, default=[])

        for g in groups:
            if group_filter and g.get("group") not in group_filter:
                continue
            items = g.get("items", [])
            if domain != "All":
                items = [i for i in items
                         if domain in (i.get("domains") or []) or "All" in (i.get("domains") or [])]
            if cost_filter:
                items = [i for i in items if i.get("cost") in cost_filter]
            if not items:
                continue
            st.markdown(f"### {g.get('group')}")
            if g.get("group_blurb"):
                st.caption(g["group_blurb"])
            for i in items:
                cost = i.get("cost", "")
                tag = {"Free": "🟢", "Freemium": "🟡", "Paid": "🔴",
                       "Free with UW login": "🎓"}.get(cost, "")
                st.markdown(f"{tag} **[{i.get('name')}]({i.get('url')})** · {cost}")
                st.caption(i.get("what_it_is", ""))
                if i.get("best_for"):
                    st.caption(f"**Best for:** {i['best_for']}")
                if i.get("meta"):
                    st.caption(f"_{i['meta']}_")
                if i.get("caveat"):
                    st.caption(f"⚠️ {i['caveat']}")

        st.divider()
        st.markdown("### 🔎 Find real interview experiences")
        ie_c1, ie_c2 = st.columns(2)
        ie_company = ie_c1.text_input("Company", value="" if not company else company["name"],
                                      placeholder="e.g. Amazon")
        ie_role = ie_c2.text_input("Role", value="supply chain")
        for s in get_interview_experience_sources(ie_company, ie_role):
            st.markdown(f"**[{s['name']}]({s.get('search_url', s['url'])})**")
            st.caption(s["desc"])
        st.info("Launchers only — we never scrape these. Glassdoor and Blind have the best "
                "coverage for non-software management roles.")

        pb = pc.playbook()
        if pb:
            st.divider()
            st.markdown("### 🗓️ How people actually prepare")
            fm = pb.get("funnel_math") or {}
            if fm:
                st.info(f"**The funnel:** {fm.get('summary','')}")
                for d in fm.get("detail", []):
                    st.markdown(f"- {d}")
            for ph in pb.get("phases", []):
                with st.expander(f"**{ph.get('label')}** — {ph.get('focus','')}"):
                    for a in ph.get("actions", []):
                        st.markdown(f"- {a}")
                    if ph.get("output"):
                        st.success(f"**By the end:** {ph['output']}")
            wc = pb.get("weekly_cadence") or {}
            if wc.get("blocks"):
                st.markdown("#### A sustainable prep week")
                st.caption(wc.get("summary", ""))
                st.dataframe(pd.DataFrame(wc["blocks"]), hide_index=True,
                             width="stretch")
            for key, title in [("story_bank_method", "Story bank method"),
                               ("debrief_protocol", "Debrief every interview")]:
                sec = pb.get(key) or {}
                if sec:
                    with st.expander(f"**{title}**"):
                        st.markdown(sec.get("summary", ""))
                        for s in sec.get("steps", []):
                            st.markdown(f"- {s}")
                        for t in sec.get("coverage_targets", []):
                            st.markdown(f"- {t}")

# === TAB: NETWORKING ===
def page_networking():
    st.subheader("☕ Coffee Chats & Networking Log")
    st.caption("Log conversations, capture takeaways, and track action items from every chat.")

    from src.networking import get_all_chats, get_all_action_items, log_chat

    chats = get_all_chats()

    # Action items rollup across all chats
    action_items = get_all_action_items()
    if action_items:
        with st.expander(f"✅ All Action Items ({len(action_items)})", expanded=True):
            for ai in action_items:
                st.markdown(f"- {ai['item']}  \n  <span style='font-size:0.8em;color:#888'>from {ai['from']} · {ai['date']}</span>", unsafe_allow_html=True)

    st.divider()

    # Show logged chats
    if not chats:
        st.info("No coffee chats logged yet. Add your first one below.")
    else:
        st.markdown(f"### 📇 {len(chats)} Chats Logged")
        for chat in chats:
            with st.expander(f"**{chat['person_name']}** — {chat['person_role']} @ {chat['person_company']} · {chat['chat_date']}"):
                if chat.get("linkedin_url"):
                    st.markdown(f"[LinkedIn]({chat['linkedin_url']})")
                if chat.get("how_connected"):
                    st.caption(f"How connected: {chat['how_connected']}")
                if chat.get("summary"):
                    st.markdown("**Summary**")
                    st.markdown(chat["summary"])
                if chat.get("key_takeaways"):
                    st.markdown("**Key Takeaways**")
                    st.markdown(chat["key_takeaways"])
                if chat.get("action_items"):
                    st.markdown("**Action Items**")
                    st.markdown(chat["action_items"])
                if chat.get("follow_up_date"):
                    st.info(f"Follow up by: {chat['follow_up_date']}")

    # Add new chat form
    st.divider()
    st.markdown("### ➕ Log a New Coffee Chat")
    with st.form("add_chat_form"):
        fc1, fc2 = st.columns(2)
        person_name = fc1.text_input("Name")
        person_role = fc2.text_input("Role")
        fc3, fc4 = st.columns(2)
        person_company = fc3.text_input("Company")
        linkedin_url = fc4.text_input("LinkedIn URL (optional)")
        chat_date = st.text_input("Date (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
        how_connected = st.text_input("How did you connect? (optional)")
        summary = st.text_area("Summary of conversation")
        key_takeaways = st.text_area("Key takeaways (one per line)")
        action_items = st.text_area("Action items (one per line)")
        follow_up_date = st.text_input("Follow-up date (optional)")
        submitted = st.form_submit_button("Save Chat")
        if submitted and person_name:
            log_chat(person_name, person_role, person_company, chat_date, linkedin_url,
                     how_connected, summary, key_takeaways, action_items, follow_up_date)
            st.success(f"Logged chat with {person_name}!")
            st.rerun()

# === TAB: TOOLS ===
def page_tools():
    st.subheader("⚡ Application Tools")

    st.markdown("### 📌 ATS Auto-Fill Bookmarklet")
    st.markdown("""
    A one-click form filler for Workday, Greenhouse, Lever, iCIMS, and similar ATS systems.
    Saves 5-10 minutes per application.

    **How to install (one-time setup):**
    1. Make sure your bookmarks bar is visible (`Cmd+Shift+B` or `Ctrl+Shift+B`)
    2. Click and **drag the link below** to your bookmarks bar
    3. Done!

    **How to use:**
    1. Open any job application form (Workday, Greenhouse, etc.)
    2. Click the bookmark in your bookmarks bar
    3. Common fields auto-fill (name, email, phone, LinkedIn, visa status, salary, start date)
    4. Review and complete any custom questions, then submit
    """)

    from src.bookmarklet import generate_bookmarklet_js, get_profile_data
    encoded, raw_js = generate_bookmarklet_js()

    st.markdown(f'<a href="{encoded}" style="display:inline-block; padding:10px 20px; background:#1a73e8; color:white; text-decoration:none; border-radius:8px; font-weight:bold;">📌 MSCM Auto-Fill (drag to bookmarks)</a>', unsafe_allow_html=True)
    st.caption("👆 Drag this button to your bookmarks bar — clicking here won't do anything useful")

    with st.expander("What data will it fill in?"):
        data = get_profile_data()
        st.json(data)
        st.caption("Edit these in `config/profile.json`")

    with st.expander("View the JavaScript code"):
        st.code(raw_js, language="javascript")

# === TAB: EXPORT ===
def page_export():
    scored = load_jobs(min_score=60)
    st.subheader("Export Data")
    if not scored.empty:
        csv = scored[["title", "company", "location", "job_url", "score", "job_type", "region", "salary_min", "salary_max"]].to_csv(index=False)
        st.download_button("📥 Download Jobs (CSV)", csv, "jobs.csv", "text/csv")
    apps_exp = load_applications()
    if not apps_exp.empty:
        st.download_button("📥 Download Applications (CSV)", apps_exp.to_csv(index=False), "applications.csv", "text/csv")

def page_today():
    from src.interview_prep import practice_cadence, story_coverage
    from src.todos import get_todos, set_status

    st.subheader("☀️ Today")
    jobs = load_jobs(min_score=70)
    apps = applications_map()
    today = date.today()
    baseline = visit_baseline()

    acted = {j for j, a in apps.items() if a.get("status") not in (None, "new")}
    due = [(jid, a) for jid, a in apps.items()
           if a.get("status") in ("applied", "interviewing")
           and str(a.get("follow_up_date") or "")[:10]
           and str(a["follow_up_date"])[:10] <= today.isoformat()]
    high = [t for t in get_todos("open") if t.get("priority") == "high"]
    cad = practice_cadence()

    m1, m2, m3, m4 = st.columns(4)
    if baseline and not jobs.empty:
        m1.metric("New since your last visit", int((jobs["scraped_at"].astype(str).str[:10] > baseline).sum()))
    else:
        m1.metric("New since your last visit", "—", help="Counts start from your next visit.")
    m2.metric("Follow-ups due", len(due))
    m3.metric("High-priority to-dos", len(high))
    m4.metric("Last mock interview", "never" if cad["days_since"] is None else f"{cad['days_since']}d ago",
              delta="overdue" if cad["overdue"] else None, delta_color="inverse")

    # --- Shortlist: full-time, not yet acted on, fresh, max 2 per company ---
    st.markdown("### 🎯 Your shortlist")
    if jobs.empty:
        st.info("No jobs published yet.")
    else:
        ft = jobs[(jobs["job_type"] != "internship") & (~jobs["job_id"].isin(acted))]
        fresh = ft[ft["eff_posted"] >= (today - timedelta(days=14)).isoformat()]
        pool = fresh if not fresh.empty else ft
        pool = pool.groupby("company", sort=False).head(2)  # keeps the list varied; order preserved
        if fresh.empty:
            st.caption("Nothing posted in the last 14 days — showing the best older postings.")
        st.caption("🤖 = Claude read the posting." if pool["ai_read"].any() else
                   "Ranked by keyword score (Claude hasn't read these yet); ties go to the newest posting.")
        for label, region, n in (("Seattle & area", "seattle", 8), ("Rest of USA", "national", 4)):
            rows = pool[pool["region"] == region].head(n)
            st.markdown(f"**{label}**")
            if rows.empty:
                st.caption("Nothing new here.")
            for i, row in rows.iterrows():
                job_row(row, f"today_{region}_{i}", apps, selectable=False)
        st.page_link(JOBS_PAGE, label="Browse and filter all jobs", icon="📋")

    # --- Follow-ups ---
    if due:
        st.markdown("### 📬 Follow-ups due")
        conn = get_db()
        ids = [jid for jid, _ in due]
        info = {r[0]: r[1:] for r in conn.execute(
            f"SELECT job_id, title, company, job_url FROM jobs WHERE job_id IN ({','.join('?' * len(ids))})", ids)}
        conn.close()
        for jid, a in sorted(due, key=lambda x: str(x[1].get("follow_up_date"))):
            title, company, url = info.get(jid, ("(posting no longer listed)", "", ""))
            link = f" · [open ↗]({_safe_url(url)})" if _safe_url(url) else ""
            st.markdown(f"- **{title}** @ {company} — {a.get('status')}, follow up by "
                        f"{str(a['follow_up_date'])[:10]}{link}")

    # --- To-dos ---
    if high:
        st.markdown("### ✅ High-priority to-dos")
        for t_ in high[:5]:
            c1, c2 = st.columns([8, 1])
            c1.markdown(t_.get("item", ""))
            if c2.button("Done", key=f"today_todo_{t_['id']}"):
                set_status(t_["id"], "done")
                st.rerun()
        if len(high) > 5:
            st.page_link(TODOS_PAGE, label=f"All {len(high)} high-priority to-dos", icon="✅")

    # --- Prep nudges ---
    cov = story_coverage()
    if cad["overdue"] or cov["missing"]:
        st.markdown("### 🎤 Interview prep")
        if cad["overdue"]:
            st.warning("A mock interview is due — your mentor's cadence is one every 2 weeks.")
        if cov["missing"]:
            st.info(f"{len(cov['missing'])} behavioral themes have no STAR story yet "
                    f"(e.g. {', '.join(cov['missing'][:3])}).")
        st.page_link(INTERVIEW_PAGE, label="Open Interview Prep", icon="🎤")


# --- NAVIGATION ---
# Pages, not st.tabs: st.tabs executes EVERY tab's code on every click (3,871
# elements per rerun). With st.navigation only the open page runs.
JOBS_PAGE = st.Page(page_jobs, title="Jobs", icon="📋", url_path="jobs")
TODOS_PAGE = st.Page(page_todos, title="To-Dos", icon="✅", url_path="todos")
INTERVIEW_PAGE = st.Page(page_interview, title="Interview Prep", icon="🎤", url_path="interview")
pg = st.navigation({
    "": [st.Page(page_today, title="Today", icon="☀️", url_path="today", default=True)],
    "Find": [
        JOBS_PAGE,
        st.Page(page_referrals, title="Referrals", icon="🤝", url_path="referrals"),
        st.Page(page_sponsors, title="Sponsors", icon="🛂", url_path="sponsors"),
    ],
    "Apply & Track": [
        st.Page(page_tracker, title="Tracker", icon="📊", url_path="tracker"),
        TODOS_PAGE,
        st.Page(page_networking, title="Networking", icon="☕", url_path="networking"),
    ],
    "Prepare": [
        INTERVIEW_PAGE,
        st.Page(page_skills, title="Skills Gap", icon="🎓", url_path="skills"),
        st.Page(page_insights, title="Skills Insights", icon="📈", url_path="insights"),
        st.Page(page_projects, title="Projects", icon="🛠️", url_path="projects"),
        st.Page(page_fellowships, title="Fellowships", icon="🏆", url_path="fellowships"),
    ],
    "Tools": [
        st.Page(page_tools, title="Tools", icon="⚡", url_path="tools"),
        st.Page(page_export, title="Export", icon="📤", url_path="export"),
    ],
})
pg.run()

# --- FOOTER ---
flush_toasts()  # confirmations from saves this run that weren't followed by a rerun
