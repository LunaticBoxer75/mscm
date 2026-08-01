"""Interview prep — recommendations from mentors, STAR stories, mock question bank."""

import random
from datetime import datetime
from .scraper import get_db


# ============ RECOMMENDATIONS ============
def _ensure_rec_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interview_recs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            recommended_by TEXT,
            person_role TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    return conn


def add_recommendation(recommendation, category, recommended_by, person_role=""):
    conn = _ensure_rec_table()
    existing = conn.execute("SELECT id FROM interview_recs WHERE recommendation = ?", (recommendation,)).fetchone()
    if existing:
        conn.close()
        return
    conn.execute("""
        INSERT INTO interview_recs (recommendation, category, recommended_by, person_role, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (recommendation, category, recommended_by, person_role, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_recommendations():
    conn = _ensure_rec_table()
    cursor = conn.execute("SELECT * FROM interview_recs ORDER BY category, created_at DESC")
    columns = [d[0] for d in cursor.description]
    rows = [dict(zip(columns, r)) for r in cursor.fetchall()]
    conn.close()
    return rows


def seed_shivam_recommendations():
    """Seed recommendations from the Shivam Suru coffee chat."""
    recs = [
        ("Stories should be so clear and transitional the interviewer can easily take notes and discuss with their team — structured, impactful, not complicated", "Story Craft", "Shivam Suru", "AI Product Manager, Amazon"),
        ("Apply STAR method to every story, categorized by behavioral theme (conflict, prioritization, etc.)", "Story Craft", "Shivam Suru", "AI Product Manager, Amazon"),
        ("Interviews dive progressively deeper — be ready for follow-up layers on every story", "Interview Dynamics", "Shivam Suru", "AI Product Manager, Amazon"),
        ("Interview math: ~150 applications → ~5 interviews → aim to convert 4 of 5. Getting the interview is half the battle; converting is the skill", "Strategy", "Shivam Suru", "AI Product Manager, Amazon"),
        ("Start interview prep VERY early — don't wait", "Timing", "Shivam Suru", "AI Product Manager, Amazon"),
        ("Understand your portfolio projects deeply: how built, how AI was used, real impact — depth matters as much as having the project", "Portfolio", "Shivam Suru", "AI Product Manager, Amazon"),
        ("Tailor resume + portfolio to each company's cultural values (e.g., Amazon Leadership Principles)", "Company Fit", "Shivam Suru", "AI Product Manager, Amazon"),
        ("Leverage unique background (Microbiology + Uber policy/risk + SCM + AI) — companies like Google value it", "Positioning", "Shivam Suru", "AI Product Manager, Amazon"),
        ("Broaden target roles: Product, Program, Vendor, and general Management — not just SCM", "Role Targeting", "Shivam Suru", "AI Product Manager, Amazon"),
        ("Do a mock interview every 2 weeks to keep stories sharp and learn current top questions", "Practice", "Shivam Suru", "AI Product Manager, Amazon"),
    ]
    for rec, cat, by, role in recs:
        add_recommendation(rec, cat, by, role)


# ============ STAR STORIES ============
def _ensure_story_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS star_stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            theme TEXT DEFAULT 'general',
            situation TEXT, task TEXT, action TEXT, result TEXT,
            tags TEXT,
            created_at TEXT, updated_at TEXT
        )
    """)
    conn.commit()
    return conn


STORY_THEMES = [
    "Leadership", "Conflict Management", "Prioritization", "Dealing with Ambiguity",
    "Failure / Learning", "Data-Driven Decision", "Cross-Functional Collaboration",
    "Process Improvement", "Customer Obsession", "Ownership", "Stakeholder Management",
    "Handling Pressure / Tight Deadline", "Influencing Without Authority", "Innovation",
]


def add_story(title, theme, situation, task, action, result, tags=""):
    conn = _ensure_story_table()
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO star_stories (title, theme, situation, task, action, result, tags, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, theme, situation, task, action, result, tags, now, now))
    conn.commit()
    conn.close()


def get_stories(theme=None):
    conn = _ensure_story_table()
    if theme:
        cursor = conn.execute("SELECT * FROM star_stories WHERE theme = ? ORDER BY updated_at DESC", (theme,))
    else:
        cursor = conn.execute("SELECT * FROM star_stories ORDER BY theme, updated_at DESC")
    columns = [d[0] for d in cursor.description]
    rows = [dict(zip(columns, r)) for r in cursor.fetchall()]
    conn.close()
    return rows


def delete_story(story_id):
    conn = _ensure_story_table()
    conn.execute("DELETE FROM star_stories WHERE id = ?", (story_id,))
    conn.commit()
    conn.close()


# ============ MOCK INTERVIEW QUESTION BANK ============
# Behavioral + role-specific questions for SCM/Ops/PM/Risk roles
MOCK_QUESTION_BANK = {
    "Behavioral (Leadership Principles style)": [
        "Tell me about a time you had to make a decision with incomplete data.",
        "Describe a situation where you disagreed with a stakeholder. How did you handle it?",
        "Tell me about a time you failed. What did you learn?",
        "Give an example of when you had to prioritize competing deadlines.",
        "Describe a time you influenced a decision without having formal authority.",
        "Tell me about a time you improved a process. What was the impact?",
        "Describe the most complex problem you've solved. Walk me through your approach.",
        "Tell me about a time you had to deliver bad news to a stakeholder.",
        "Give an example of when you went above and beyond your role.",
        "Tell me about a time you had to manage a conflict within a team.",
        "Describe a time you had to learn something quickly to complete a task.",
        "Tell me about a time you used data to change someone's mind.",
    ],
    "Supply Chain / Operations": [
        "How would you reduce lead time in a supply chain that's consistently late?",
        "Walk me through how you'd analyze why on-time delivery dropped 10% last quarter.",
        "How do you balance inventory costs against stockout risk?",
        "A key supplier just failed an audit. What are your next steps?",
        "How would you set up KPIs for a new distribution center?",
        "Explain a time you optimized a process end-to-end. What levers did you pull?",
        "How do you approach demand forecasting for a product with no history?",
        "Describe how you'd run a supplier negotiation for a critical component.",
    ],
    "Program / Product Management": [
        "How do you prioritize features when engineering capacity is limited?",
        "Walk me through how you'd launch a new program from scratch.",
        "How do you measure the success of a program you own?",
        "A project is behind schedule. How do you get it back on track?",
        "How do you align multiple stakeholders with conflicting goals?",
        "Tell me how you'd write a one-pager for a new initiative.",
        "How do you decide what NOT to build?",
    ],
    "Risk / Compliance": [
        "How would you build a risk framework for a new business line?",
        "Describe how you'd detect fraud in a high-volume transaction system.",
        "How do you balance compliance requirements against operational speed?",
        "Tell me about a time you identified a risk others missed.",
        "How would you design an audit process for a new vendor?",
    ],
}


def generate_mock_interview(n=5):
    """Generate a mixed mock interview of n questions across categories."""
    all_q = []
    for category, questions in MOCK_QUESTION_BANK.items():
        for q in questions:
            all_q.append({"category": category, "question": q})
    # Weighted: ensure at least 2 behavioral, then mix
    behavioral = [q for q in all_q if "Behavioral" in q["category"]]
    others = [q for q in all_q if "Behavioral" not in q["category"]]
    # Deterministic-ish shuffle using current second so repeated clicks vary
    seed = int(datetime.now().timestamp())
    rng = random.Random(seed)
    rng.shuffle(behavioral)
    rng.shuffle(others)
    n_behavioral = min(2, len(behavioral))
    picked = behavioral[:n_behavioral] + others[:(n - n_behavioral)]
    rng.shuffle(picked)
    return picked[:n]


# ============ INTERVIEW EXPERIENCE SOURCES ============
# Concrete, real sources for interview experiences (management/SCM/PM/ops roles)
# These are curated resource sites, NOT scraped content (ToS-safe).
def get_interview_experience_sources(company="", role=""):
    """Return concrete resource links for finding interview experiences."""
    import urllib.parse
    c = urllib.parse.quote(company) if company else ""
    r = urllib.parse.quote(role) if role else "supply chain"

    sources = [
        {
            "name": "Glassdoor Interviews",
            "desc": "Real interview questions & experiences by company + role. Best coverage for non-technical roles.",
            "url": f"https://www.glassdoor.com/Interview/{c.replace('%20','-')}-interview-questions-SRCH_KE0,{len(company)}.htm" if company else "https://www.glassdoor.com/Interview/index.htm",
            "search_url": f"https://www.glassdoor.com/Interview/index.htm?keyword={c}%20{r}",
        },
        {
            "name": "LeetCode Discuss (Interview Experiences)",
            "desc": "Has PM, Ops, and some management interview experiences — not just software. Search by company.",
            "url": f"https://leetcode.com/discuss/interview-experience?currentPage=1&query={c}%20{r}",
        },
        {
            "name": "Blind (teamblind.com)",
            "desc": "Anonymous professional network — search interview threads by company. Strong for tech company non-eng roles.",
            "url": f"https://www.teamblind.com/search/{c}%20interview" if company else "https://www.teamblind.com/",
        },
        {
            "name": "Reddit (r/supplychain, r/prodmgmt, r/ITCareerQuestions)",
            "desc": "Community interview debriefs. Search 'interview' + company.",
            "url": f"https://www.reddit.com/search/?q={c}%20{r}%20interview",
        },
        {
            "name": "Prepfully",
            "desc": "Interview questions + guides for PM, Ops, and management roles at top companies.",
            "url": f"https://prepfully.com/interview-questions?q={c}",
        },
        {
            "name": "Exponent (tryexponent.com)",
            "desc": "PM, TPM, and management interview prep with real question sets and mock interview practice.",
            "url": "https://www.tryexponent.com/questions",
        },
    ]
    return sources
