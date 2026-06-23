"""Skills & certification insights — analyze what's demanded across all scored job descriptions.

Categorizes into technical skills, management/soft skills, and certifications,
returning frequency counts. Used by the dashboard Skills Insights tab.
"""

import sqlite3
from pathlib import Path

# Prefer the deploy DB (bundled on Streamlit Cloud), fall back to full local DB
_DATA_DIR = Path(__file__).parent.parent / "data"


def get_db():
    deploy = _DATA_DIR / "jobs_deploy.db"
    full = _DATA_DIR / "jobs.db"
    return sqlite3.connect(deploy if deploy.exists() else full)

TECHNICAL_SKILLS = {
    "Excel / Spreadsheets": ["excel", "spreadsheet", "pivot table", "vlookup"],
    "ERP systems (SAP/Oracle)": ["erp", "oracle", "netsuite", "sap"],
    "Data analysis / analytics": ["data analysis", "data analytics", "analytics"],
    "Data visualization": ["data visualization", "dashboard", "visualization"],
    "SQL": ["sql", "mysql", "postgresql"],
    "Forecasting / Demand planning": ["forecasting", "demand planning"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "Statistical analysis": ["statistical analysis", "statistics", "regression"],
    "Python": ["python", "pandas"],
    "Salesforce": ["salesforce"],
    "WMS / TMS": ["wms", "tms", "warehouse management system", "transportation management"],
    "VBA / Macros": ["vba", "macros"],
    "Machine Learning": ["machine learning", "predictive model"],
    "MRP": ["mrp ", "material requirements planning"],
}

SOFT_SKILLS = {
    "Communication": ["communication skills", "verbal communication", "written communication", "communicate"],
    "Stakeholder management": ["stakeholder"],
    "Leadership": ["leadership", "lead a team", "team lead"],
    "Analytical / critical thinking": ["analytical", "critical thinking"],
    "Process improvement": ["process improvement", "continuous improvement", "process optimization"],
    "Strategic thinking / planning": ["strategic thinking", "strategic planning", "strategy"],
    "Collaboration / teamwork": ["teamwork", "team player", "collaborative", "collaboration"],
    "Time management / prioritization": ["time management", "prioritization", "prioritize"],
    "Project management": ["project management", "project manage"],
    "Attention to detail": ["attention to detail", "detail-oriented", "detail oriented"],
    "Risk management": ["risk management", "risk assessment", "risk mitigation"],
    "Negotiation": ["negotiation", "negotiate"],
    "Problem solving": ["problem solving", "problem-solving"],
    "Vendor / supplier management": ["vendor management", "supplier management", "supplier relationship"],
    "Change management": ["change management"],
}

CERTIFICATIONS = {
    "Lean Six Sigma": ["six sigma", "lean six sigma", "green belt", "black belt", "yellow belt"],
    "PMP": ["pmp", "project management professional"],
    "APICS / CSCP": ["apics", "cscp"],
    "CPIM": ["cpim"],
    "CLTD": ["cltd"],
    "CPSM (Supply Mgmt)": ["cpsm"],
    "CSCMP / SCPro": ["cscmp", "scpro"],
    "Lean / Kaizen": ["lean manufacturing", "kaizen"],
    "ISO 9001": ["iso 9001", "iso certification"],
    "Scrum / Agile (CSM)": ["scrum master", "pmi-acp", "safe agile"],
    "CPA": ["cpa"],
    "CFA": ["cfa"],
}

# Skills Bhumika already has (to flag gaps)
HAS_SKILLS = {
    "Excel / Spreadsheets", "SQL", "Data analysis / analytics", "Data visualization",
    "Communication", "Stakeholder management", "Process improvement", "Project management",
    "Analytical / critical thinking", "Risk management", "Attention to detail",
    "Collaboration / teamwork", "Time management / prioritization",
}
HAS_CERTS = {"Lean Six Sigma", "PMP"}


def analyze_skills(min_score=60, limit=8000):
    """Analyze job descriptions and return skill frequency breakdowns."""
    conn = get_db()
    rows = conn.execute("""
        SELECT description FROM jobs
        WHERE score >= ? AND description IS NOT NULL AND description != ''
        AND (dismissed IS NULL OR dismissed = 0)
        LIMIT ?
    """, (min_score, limit)).fetchall()
    conn.close()

    descs = [r[0].lower() for r in rows]
    n = len(descs)
    if n == 0:
        return {"total": 0, "technical": [], "soft": [], "certs": []}

    def count_category(category):
        results = []
        for name, variants in category.items():
            cnt = sum(1 for d in descs if any(v in d for v in variants))
            results.append({
                "skill": name,
                "count": cnt,
                "pct": round(cnt / n * 100, 1),
            })
        results.sort(key=lambda x: -x["count"])
        return results

    tech = count_category(TECHNICAL_SKILLS)
    soft = count_category(SOFT_SKILLS)
    certs = count_category(CERTIFICATIONS)

    # Tag has/gap
    for r in tech + soft:
        r["has"] = r["skill"] in HAS_SKILLS
    for r in certs:
        r["has"] = r["skill"] in HAS_CERTS

    return {"total": n, "technical": tech, "soft": soft, "certs": certs}
