"""MSCM Job Search Dashboard — Streamlit web UI.

Reads from SQLite database (bundled in repo via git). Same file locally and deployed.
No external database needed.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECTS_DIR = Path(__file__).parent / "projects"
DB_PATH = Path(__file__).parent / "data" / "jobs_deploy.db"

st.set_page_config(page_title="MSCM Job Search", page_icon="🎯", layout="wide")


def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data(ttl=60)
def load_jobs(min_score=50):
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT * FROM jobs
        WHERE score IS NOT NULL AND score >= ?
        AND title IS NOT NULL AND title != ''
        AND company IS NOT NULL AND company != ''
        AND (dismissed IS NULL OR dismissed = 0)
        ORDER BY score DESC
    """, conn, params=(min_score,))
    conn.close()
    return df


def load_applications():
    conn = get_db()
    try:
        df = pd.read_sql_query("""
            SELECT a.*, j.title, j.company, j.location, j.score, j.job_url
            FROM applications a JOIN jobs j ON a.job_id = j.job_id
            ORDER BY CASE a.status WHEN 'interviewing' THEN 1 WHEN 'applied' THEN 2
                WHEN 'offer' THEN 3 ELSE 4 END, j.score DESC
        """, conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def dismiss_job(job_id):
    conn = get_db()
    conn.execute("UPDATE jobs SET dismissed = 1 WHERE job_id = ?", (job_id,))
    conn.commit()
    conn.close()
    load_jobs.clear()


def update_application(job_id, status, notes=None, follow_up_date=None):
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS applications (
        job_id TEXT PRIMARY KEY, status TEXT, applied_date TEXT,
        notes TEXT, follow_up_date TEXT, updated_at TEXT)""")
    now = datetime.now().isoformat()
    # Auto-set 7-day follow-up when applying
    if status == "applied" and not follow_up_date:
        follow_up_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    conn.execute("""
        INSERT INTO applications (job_id, status, applied_date, notes, follow_up_date, updated_at)
        VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(job_id) DO UPDATE SET
        status=excluded.status, notes=excluded.notes,
        follow_up_date=excluded.follow_up_date, updated_at=excluded.updated_at
    """, (job_id, status, now if status == "applied" else None, notes, follow_up_date, now))
    conn.commit()
    conn.close()


def get_application_status(job_id):
    """Get current application status for a job."""
    conn = get_db()
    try:
        row = conn.execute("SELECT status FROM applications WHERE job_id = ?", (job_id,)).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        conn.close()
        return None


def get_todays_top_jobs(limit=5):
    """Composite priority: score × freshness × not-applied."""
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT j.*, a.status as applied_status
        FROM jobs j
        LEFT JOIN applications a ON j.job_id = a.job_id
        WHERE j.score IS NOT NULL AND j.score >= 70
        AND j.title IS NOT NULL AND j.title != ''
        AND j.company IS NOT NULL AND j.company != ''
        AND (j.dismissed IS NULL OR j.dismissed = 0)
        AND (a.status IS NULL OR a.status = 'new')
        ORDER BY j.score DESC, j.scraped_at DESC
        LIMIT ?
    """, conn, params=(limit,))
    conn.close()
    return df


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
    params.append(limit)

    try:
        df = pd.read_sql_query(f"""
            SELECT job_id, title, company, location, score, salary_min, salary_max, job_url
            FROM jobs
            WHERE {where_clauses}
            AND job_id != ?
            AND score >= 60
            AND (dismissed IS NULL OR dismissed = 0)
            ORDER BY score DESC
            LIMIT ?
        """, conn, params=params)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# --- HEADER ---
st.title("🎯 MSCM Job Search Dashboard")
st.caption("Daily job identification for Bhumika Choudhary — UW Foster MSCM (Jun 2026 – May 2027)")

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

    # Today's Top 5 (A4)
    todays_top = get_todays_top_jobs(5)
    if not todays_top.empty:
        st.markdown("### 🔥 Today's Top 5 — Apply to These Now")
        for _, j in todays_top.iterrows():
            sal = ""
            if pd.notna(j.get("salary_min")) and pd.notna(j.get("salary_max")):
                sal = f" · ${int(j['salary_min']/1000)}K-${int(j['salary_max']/1000)}K"
            cols = st.columns([0.3, 5, 1.2])
            with cols[0]:
                st.markdown(f"**{int(j['score'])}**")
            with cols[1]:
                st.markdown(f"**{j['title']}** @ {j['company']} · {j['location']}{sal}")
            with cols[2]:
                if j.get("job_url"):
                    st.link_button("Apply →", j["job_url"], use_container_width=True)
    st.divider()


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
        filtered = filtered[filtered["date_posted"].fillna("") >= cutoff]
    if company_filter:
        filtered = filtered[filtered["company"].isin(company_filter)]
    if title_filter:
        filtered = filtered[filtered["title"].isin(title_filter)]
    return filtered


# --- TABS ---
tab_jobs, tab_tracker, tab_referrals, tab_sponsors, tab_skills, tab_projects, tab_tools, tab_export = st.tabs([
    "📋 Jobs", "📊 Tracker", "🤝 Referrals", "🛂 Sponsors", "🎓 Skills Gap", "🛠️ Projects", "⚡ Tools", "📤 Export"
])

# === TAB: JOBS ===
with tab_jobs:
    if scored.empty:
        st.info("No scored jobs yet. Run `/find-jobs` in Claude Code.")
    else:
        jobs = filter_jobs(scored)
        sub_tabs = st.tabs(["Seattle FT", "Seattle Intern", "National FT", "National Intern", "All"])

        def render_table(df, name, key):
            if df.empty:
                st.info(f"No {name} jobs matching filters.")
                return
            display = df[["score", "title", "company", "location", "job_url", "salary_min", "salary_max"]].copy().reset_index(drop=False)
            display["score"] = display["score"].astype(int)

            # Paginate — show 25 at a time for fast interaction
            page_size = 25
            page_key = f"page_{key}"
            if page_key not in st.session_state:
                st.session_state[page_key] = 0
            page = st.session_state[page_key]
            total_pages = (len(display) - 1) // page_size + 1
            page_slice = display.iloc[page * page_size:(page + 1) * page_size]

            with st.container(height=400):
                for i, row in page_slice.iterrows():
                    col_btn, col_info, col_salary, col_link = st.columns([0.4, 5, 1.5, 1])
                    score = row["score"]
                    color = "🟢" if score >= 90 else "🔵" if score >= 75 else "🟡" if score >= 60 else "⚪"
                    with col_btn:
                        if st.button(f"{color}", key=f"{key}_{i}", help=f"Score: {score}"):
                            st.session_state["selected_job_idx"] = row["index"]
                    with col_info:
                        st.markdown(f"<span style='font-size:0.9em'><b>{row['title']}</b> @ {row['company']} · {row['location']}</span>", unsafe_allow_html=True)
                    with col_salary:
                        sal_min, sal_max = row.get("salary_min"), row.get("salary_max")
                        if pd.notna(sal_min) and pd.notna(sal_max):
                            st.markdown(f"<span style='font-size:0.85em;color:#059669'>${int(sal_min/1000)}K-${int(sal_max/1000)}K</span>", unsafe_allow_html=True)
                        elif pd.notna(sal_min):
                            st.markdown(f"<span style='font-size:0.85em;color:#059669'>${int(sal_min/1000)}K+</span>", unsafe_allow_html=True)
                    with col_link:
                        if row.get("job_url"):
                            st.markdown(f"<a href='{row['job_url']}' target='_blank' style='font-size:0.85em'>Apply→</a>", unsafe_allow_html=True)

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
            sea_int = jobs[(jobs["region"] == "seattle") & (jobs["job_type"] == "internship")]
            render_table(sea_int, "Seattle internship", "t_sea_int")
        with sub_tabs[2]:
            nat_ft = jobs[(jobs["region"] == "national") & (jobs["job_type"] != "internship")]
            render_table(nat_ft, "National full-time", "t_nat_ft")
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
                                st.link_button("Apply", c["job_url"], use_container_width=True)

                st.markdown("---")
                st.markdown("#### ⚡ Quick Actions")
                applied_status = get_application_status(job_id_curr)
                act_cols = st.columns([1.5, 1.5, 3])
                with act_cols[0]:
                    if job.get("job_url"):
                        st.link_button("📝 Open Posting", job["job_url"], use_container_width=True)
                with act_cols[1]:
                    if applied_status == "applied":
                        st.success("✓ Applied")
                    else:
                        if st.button("✅ Mark Applied", use_container_width=True, help="Marks applied + queues 7-day follow-up"):
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
                ref_cols[0].link_button("👥 Same Role", f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(role_kw)}&company={urllib.parse.quote(company)}", use_container_width=True)
                ref_cols[1].link_button("🎯 Recruiters", f"https://www.linkedin.com/search/results/people/?keywords=recruiter%20talent%20acquisition&company={urllib.parse.quote(company)}", use_container_width=True)
                ref_cols[2].link_button("📦 SC Team", f"https://www.linkedin.com/search/results/people/?keywords=supply%20chain%20procurement&company={urllib.parse.quote(company)}", use_container_width=True)
                ref_cols[3].link_button("🎓 UW Alumni", f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(company)}&schoolFilter=%5B%222584%22%5D", use_container_width=True)

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
with tab_tracker:
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
        st.dataframe(apps[display_cols], hide_index=True, use_container_width=True)

# === TAB: REFERRALS ===
with tab_referrals:
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
                ref_cols[0].link_button("👥 Same Role", f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(role_kw)}&company={urllib.parse.quote(company)}", use_container_width=True)
                ref_cols[1].link_button("🎯 Recruiters", f"https://www.linkedin.com/search/results/people/?keywords=recruiter%20talent%20acquisition&company={urllib.parse.quote(company)}", use_container_width=True)
                ref_cols[2].link_button("📦 SC Team", f"https://www.linkedin.com/search/results/people/?keywords=supply%20chain%20procurement&company={urllib.parse.quote(company)}", use_container_width=True)
                ref_cols[3].link_button("🎓 UW Alumni", f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(company)}&schoolFilter=%5B%222584%22%5D", use_container_width=True)
                msg = f"Hi [Name], I'm Bhumika — incoming MSCM student at UW Foster with 3 years of operations/risk experience at Uber. I'm very interested in the {title} role at {company} and would really appreciate a referral if you think my background could be a fit. I've attached my resume for reference. Thank you!"
                st.code(msg, language=None)

# === TAB: SPONSORS ===
with tab_sponsors:
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

    st.divider()
    st.info("""
    **Why this matters for STEM OPT:** Bhumika's MSCM is STEM-designated, giving her 36 months of OPT.
    But the 24-month extension REQUIRES the employer to be E-Verify enrolled. Companies on this list are
    confirmed E-Verify and have a history of sponsoring H1B for SCM/Ops roles.

    **Strategy:** Apply directly at these companies' careers pages, not just from job board scrapes.
    """)

# === TAB: SKILLS GAP ===
with tab_skills:
    st.subheader("Skills Gap Analysis")
    if scored.empty or len(scored) < 5:
        st.info("Need at least 5 scored jobs.")
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

# === TAB: PROJECTS ===
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

# === TAB: TOOLS ===
with tab_tools:
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
with tab_export:
    st.subheader("Export Data")
    if not scored.empty:
        csv = scored[["title", "company", "location", "job_url", "score", "job_type", "region", "salary_min", "salary_max"]].to_csv(index=False)
        st.download_button("📥 Download Jobs (CSV)", csv, "jobs.csv", "text/csv")
    apps_exp = load_applications()
    if not apps_exp.empty:
        st.download_button("📥 Download Applications (CSV)", apps_exp.to_csv(index=False), "applications.csv", "text/csv")

# --- FOOTER ---
st.divider()
st.caption(f"Source: SQLite ({DB_PATH.name}) | Last loaded: {datetime.now().strftime('%H:%M')}")
