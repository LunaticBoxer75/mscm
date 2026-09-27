"""Job scoring engine. Provides the scoring prompt and logic.

Scoring is designed to run within Claude Code — the /find-jobs command
reads unscored jobs and has Claude score them inline using the corporate
Bedrock access that Claude Code already has.

This module can also be called programmatically if Bedrock access is
available directly (e.g., via ada credentials with bedrock:InvokeModel).
"""

import json
from pathlib import Path

from .scraper import get_unscored_jobs, update_job_score

CONFIG_DIR = Path(__file__).parent.parent / "config"

SCORING_PROMPT = """You are a career advisor scoring job listings for a candidate.

## Candidate Profile
{profile_summary}

## Scoring Criteria (weights in parentheses)
1. **Role Relevance** (25%): How well does the job title and responsibilities align with target roles?
2. **Skills Match** (20%): How many of the candidate's skills (fraud detection, risk analysis, process optimization, data analysis, project management, SQL, automation) are relevant?
3. **Experience Fit** (15%): Is the experience level appropriate? (Candidate has 4 years. Entry-level to mid-level roles are ideal. Senior/Director roles should score lower.)
4. **Location Match** (15%): Is it in Seattle/Bellevue/Redmond/Kirkland/WA area or remote?
5. **Company Tier** (10%): Is this a well-known company or one aligned with supply chain (Amazon, Boeing, Costco, etc.)?
6. **Growth Potential** (10%): Does this role offer career growth into supply chain leadership?
7. **Visa Friendliness** (5%): Large companies and those known for H1B/OPT sponsorship score higher.

## Job Listing
**Title:** {title}
**Company:** {company}
**Location:** {location}
**Type:** {job_type}
**Salary:** {salary}
**Description:**
{description}

## Instructions
Score this job 0-100. Return ONLY valid JSON:
{{
  "score": <0-100>,
  "role_relevance": <0-100>,
  "skills_match": <0-100>,
  "experience_fit": <0-100>,
  "location_match": <0-100>,
  "company_tier": <0-100>,
  "growth_potential": <0-100>,
  "visa_friendliness": <0-100>,
  "reasoning": "<2-3 sentence explanation>",
  "red_flags": ["<any concerns>"],
  "highlights": ["<why this is a good match>"]
}}"""


def get_profile_summary():
    with open(CONFIG_DIR / "profile.json") as f:
        profile = json.load(f)

    candidate = profile["candidate"]
    exp = profile["experience_summary"]
    targets = profile["target_roles"]

    return f"""- Name: {candidate['name']}
- Current: {exp['current_role']} at {exp['current_company']} ({exp['years']} years)
- Education: {exp['education']['bachelors']}; Incoming MSCM at {candidate['university']}
- Target Location: {candidate['target_location']}
- Visa: {candidate['work_authorization']}
- Core Skills: {', '.join(exp['domain_expertise'][:6])}
- Tools: {', '.join(exp['tools'])}
- Certifications: {', '.join(exp['certifications'])}
- Target Roles (Primary): {', '.join(targets['primary'][:5])}
- Target Roles (Secondary): {', '.join(targets['secondary'][:4])}"""


def build_scoring_prompt(job):
    """Build the scoring prompt for a single job. Used by Claude Code inline scoring."""
    salary_str = "Not specified"
    if job.get("salary_min") and job.get("salary_max"):
        salary_str = f"${job['salary_min']:,.0f} - ${job['salary_max']:,.0f}"
    elif job.get("salary_min"):
        salary_str = f"${job['salary_min']:,.0f}+"

    description = job.get("description", "No description available")
    if len(description) > 4000:
        description = description[:4000] + "\n...[truncated]"

    return SCORING_PROMPT.format(
        profile_summary=get_profile_summary(),
        title=job.get("title", "Unknown"),
        company=job.get("company", "Unknown"),
        location=job.get("location", "Unknown"),
        job_type=job.get("job_type", "Unknown"),
        salary=salary_str,
        description=description,
    )


def batch_score_prompt(jobs):
    """Build a batch scoring prompt for multiple jobs at once (more efficient)."""
    profile_summary = get_profile_summary()

    jobs_text = []
    for i, job in enumerate(jobs, 1):
        salary_str = "Not specified"
        if job.get("salary_min") and job.get("salary_max"):
            salary_str = f"${job['salary_min']:,.0f} - ${job['salary_max']:,.0f}"
        elif job.get("salary_min"):
            salary_str = f"${job['salary_min']:,.0f}+"

        description = job.get("description", "No description available")
        # The whole stored description (the scraper keeps 10,000 chars). At 2,000 the
        # requirements and legal sections — years, citizenship, sponsorship — were
        # usually cut off, so the hard rules couldn't fire.
        if len(description) > 10000:
            description = description[:10000] + "...[truncated]"

        jobs_text.append(f"""### Job {i} (ID: {job['job_id']})
**Title:** {job.get('title', 'Unknown')}
**Company:** {job.get('company', 'Unknown')}
**Location:** {job.get('location', 'Unknown')}
**Type:** {job.get('job_type', 'Unknown')}
**Salary:** {salary_str}
**Description:** {description}
""")

    return f"""You are a career advisor scoring job listings for a candidate.

## Candidate Profile
{profile_summary}

## Scoring Criteria (weights)
1. Role Relevance (25%): risk / compliance / trust & safety / fraud / operations roles rank HIGHEST
   (her direct Uber background), then supply chain (procurement, sourcing, planning, logistics,
   inventory), then program / product management.
2. Skills Match (20%): overlap with the skills in her profile.
3. Experience Fit (15%): 4 years (Global SME, Uber Risk & Compliance) plus an MSCM (UW Foster,
   June 2026 - June 2027). Entry-to-mid level.
4. Location Match (15%): Seattle & Eastside > remote > rest of WA > rest of USA.
5. Company Tier (10%): established employers, especially ones that sponsor visas.
6. Growth Potential (10%): career trajectory.
7. Visa Friendliness (5%): F-1 student -> OPT (STEM, 3 years) -> H-1B.

## Hard rules — read the description for these; they override the weights
- Requires U.S. citizenship, a security clearance, or "U.S. person" status (ITAR/EAR): score <= 15,
  red flag "not F-1 eligible". She cannot legally take these.
- States it will not sponsor now or in the future, or won't support STEM OPT / doesn't use E-Verify:
  score <= 40 and say which in red_flags.
- REQUIRED experience (not "preferred"), vs her 4 years + master's: 7+ years -> <= 40;
  6 years -> <= 65; 5 years -> NO cap (one year short is routinely accepted with a master's; note
  "one year short" in red_flags). "2+ required, 5+ preferred" is fine.
- Clinical, retail-store, food-service, driving/CDL, warehouse-associate, trades, or engineering
  roles that merely contain words like "operations" or "program manager": <= 20.
- Full-time is her priority; internships are a fallback. A title filed as an internship that is
  really a senior full-time role: say so in red_flags.
- Only if the posting STATES a start date before her June 2027 graduation, add red flag "start date
  before June 2027" (don't lower the score for this alone). Don't infer it from an open posting.

Score anchors: 90+ apply today · 75-89 strong fit · 60-74 plausible stretch · <60 not worth her time.

## Jobs to Score

{"".join(jobs_text)}

## Instructions
Score ALL jobs above. Return a JSON array with one entry per job:
[
  {{
    "job_id": "<from above>",
    "score": <0-100>,
    "reasoning": "<1-2 sentences>",
    "highlights": ["<key strengths>"],
    "red_flags": ["<concerns if any>"]
  }},
  ...
]

Return ONLY the JSON array, no other text."""


def parse_batch_scores(response_text, jobs):
    """Parse batch scoring response and update database."""
    try:
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]
        scores = json.loads(response_text)
    except json.JSONDecodeError:
        return []

    results = []
    for score_entry in scores:
        job_id = score_entry.get("job_id")
        score = score_entry.get("score", 0)
        if job_id:
            update_job_score(job_id, score, score_entry)
            results.append(score_entry)
    return results


def score_all_pending(limit=50):
    """Get unscored jobs for manual/inline scoring. Returns jobs + prompts."""
    jobs = get_unscored_jobs(limit=limit)
    return jobs


if __name__ == "__main__":
    from rich.console import Console
    console = Console()
    jobs = score_all_pending()
    console.print(f"[bold]{len(jobs)} jobs awaiting scoring[/bold]")
    if jobs:
        console.print("\nTo score, run /find-jobs in Claude Code (uses inline Claude scoring)")
