"""Fast rule-based scorer for bulk job scoring.

Scores jobs based on title keywords, seniority signals, experience requirements
in the description, and location. Used to quickly score hundreds of jobs without
needing Claude inline scoring for obvious matches/mismatches.

The inline Claude scorer is better for borderline cases, but this handles the
80% of jobs that are clearly relevant or clearly irrelevant.
"""

import re
from .scraper import get_db, update_job_score


# Bhumika has 3 years of experience
CANDIDATE_YEARS = 3

# Title-based relevance scoring
HIGH_RELEVANCE_TITLES = [
    'supply chain analyst', 'procurement analyst', 'demand planning',
    'logistics analyst', 'operations analyst', 'inventory analyst',
    'supply chain coordinator', 'buyer', 'purchasing',
    'supply chain planner', 'sourcing analyst',
    'procurement agent', 'procurement specialist', 'procurement manager',
    'supply chain manager', 'commodity manager', 'category manager',
    'supply chain', 'procurement',
    'program manager', 'technical program manager',
]
MEDIUM_RELEVANCE_TITLES = [
    'project manager', 'business analyst',
    'data analyst', 'process improvement', 'operations',
    'logistics', 'planner', 'analyst',
]
IRRELEVANT_TITLES = [
    'nurse', 'nursing', 'pharmacy', 'pharmacist', 'physician', 'therapist',
    'dental', 'medical assistant', 'rn ', 'lpn',
    'retail sales', 'cashier', 'barista', 'server', 'cook', 'chef',
    'janitor', 'custodian', 'housekeeper', 'landscap',
    'driver', 'cdl', 'trucker',
    'teacher', 'professor', 'tutor',
    'mechanic', 'technician hvac', 'electrician', 'plumber',
    'hair stylist', 'salon', 'barber', 'grooming',
    'security guard', 'lifeguard',
    'pastor', 'minister',
]

# Seniority indicators
EXECUTIVE_TITLES = ['director', 'vp ', 'vice president', 'principal', 'head of', 'chief', 'c-suite']
SENIOR_TITLES = ['senior manager', 'sr. director', 'senior director']
# These are NOT necessarily too senior (senior analyst = 3-5yr often):
NOT_SENIOR = ['senior analyst', 'sr. analyst', 'senior associate', 'sr. associate']


def _extract_years_required(description):
    """Extract minimum years of experience from job description."""
    if not description:
        return 0

    desc_lower = description.lower()

    # Patterns like "5+ years", "5\+ years" (markdown escaped), "7-10 years", "minimum 8 years"
    patterns = [
        r'(\d+)\s*\\?\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)',
        r'(?:minimum|min|at least|requires?)\s*(\d+)\s*(?:years?|yrs?)',
        r'(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*(?:relevant|related|professional|work)',
    ]

    years_found = []
    for pattern in patterns:
        matches = re.findall(pattern, desc_lower)
        years_found.extend(int(m) for m in matches)

    return min(years_found) if years_found else 0


def _title_relevance(title):
    """Score title relevance 0-100."""
    title_lower = title.lower()

    if any(kw in title_lower for kw in IRRELEVANT_TITLES):
        return 5

    if any(kw in title_lower for kw in HIGH_RELEVANCE_TITLES):
        return 90

    if any(kw in title_lower for kw in MEDIUM_RELEVANCE_TITLES):
        return 65

    return 30


def _seniority_penalty(title, description):
    """Return score cap based on seniority. Returns 100 if no penalty."""
    title_lower = title.lower()

    # Check if it's explicitly NOT senior (e.g., "Senior Analyst" is fine)
    if any(kw in title_lower for kw in NOT_SENIOR):
        return 100  # No penalty

    # Executive level — hard cap
    if any(kw in title_lower for kw in EXECUTIVE_TITLES):
        return 35

    # Senior manager — softer cap
    if any(kw in title_lower for kw in SENIOR_TITLES):
        return 55

    # Check years in description
    years_req = _extract_years_required(description)
    if years_req >= 10:
        return 35
    elif years_req >= 7:
        return 50
    elif years_req >= 5:
        return 75  # Stretch but doable with 3yr + MSCM degree
    # 3-4 years required = perfect fit, no penalty

    return 100  # No penalty


def _location_score(location):
    """Score location match 0-100."""
    if not location:
        return 50

    loc_lower = location.lower()

    # Seattle area = highest
    seattle_area = ['seattle', 'bellevue', 'kirkland', 'redmond', 'tacoma', 'everett', 'kent', 'renton']
    if any(city in loc_lower for city in seattle_area):
        return 100

    # WA state
    if ', wa' in loc_lower or 'washington' in loc_lower:
        return 90

    # Remote
    if 'remote' in loc_lower:
        return 80

    # Other major tech metros
    major_metros = ['san francisco', 'san jose', 'new york', 'chicago', 'austin', 'boston', 'denver']
    if any(city in loc_lower for city in major_metros):
        return 60

    # Any US location
    if ', us' in loc_lower or 'united states' in loc_lower:
        return 50

    return 40


def score_job_quick(title, company, location, description):
    """Score a single job using rules. Returns (score, reasoning, highlights, red_flags)."""
    title_rel = _title_relevance(title)
    seniority_cap = _seniority_penalty(title, description)
    loc_score = _location_score(location)

    # Base score: weighted combination (title is strongest signal)
    base_score = int(title_rel * 0.6 + loc_score * 0.3 + 50 * 0.1)

    # Bonus for high-relevance + Seattle combo
    if title_rel >= 90 and loc_score >= 90:
        base_score = min(base_score + 10, 95)

    # Apply seniority cap
    final_score = min(base_score, seniority_cap)

    # Generate reasoning
    reasons = []
    highlights = []
    red_flags = []

    if title_rel >= 90:
        highlights.append('Title directly matches target roles')
    elif title_rel >= 65:
        highlights.append('Title partially relevant')
    elif title_rel <= 10:
        red_flags.append('Not relevant to SCM/operations career')

    if loc_score >= 90:
        highlights.append('Seattle/WA area')
    elif loc_score >= 60:
        highlights.append(f'Good metro: {location}')

    if seniority_cap < 100:
        years_req = _extract_years_required(description)
        if years_req > 0:
            red_flags.append(f'Requires {years_req}+ years experience (Bhumika has {CANDIDATE_YEARS})')
        else:
            red_flags.append('Title indicates senior/executive level')

    reasoning = f'{title} at {company}. '
    if highlights:
        reasoning += ' '.join(highlights) + '. '
    if red_flags:
        reasoning += ' '.join(red_flags) + '.'

    return final_score, reasoning.strip(), highlights, red_flags


def score_all_unscored():
    """Score all unscored jobs using quick rules."""
    conn = get_db()
    results = conn.execute('SELECT job_id, title, company, location, description FROM jobs WHERE score IS NULL').fetchall()
    conn.close()

    if not results:
        return 0

    scored = 0
    for job_id, title, company, location, description in results:
        if not title:
            continue
        score, reasoning, highlights, red_flags = score_job_quick(title or "", company or "", location or "", description or "")
        update_job_score(job_id, score, {
            'score': score,
            'reasoning': reasoning,
            'highlights': highlights,
            'red_flags': red_flags,
        })
        scored += 1

    return scored


if __name__ == "__main__":
    from rich.console import Console
    console = Console()
    count = score_all_unscored()
    console.print(f"[green]Quick-scored {count} jobs[/green]")
