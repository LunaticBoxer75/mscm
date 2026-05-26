"""AI-powered job scoring using Claude to match jobs against candidate profile."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
import anthropic

from .scraper import get_unscored_jobs, update_job_score

load_dotenv(Path(__file__).parent.parent / ".env")

CONFIG_DIR = Path(__file__).parent.parent / "config"

SCORING_PROMPT = """You are a career advisor scoring job listings for a candidate.

## Candidate Profile
{profile_summary}

## Scoring Criteria (weights in parentheses)
1. **Role Relevance** (25%): How well does the job title and responsibilities align with target roles?
2. **Skills Match** (20%): How many of the candidate's skills (fraud detection, risk analysis, process optimization, data analysis, project management, SQL, automation) are relevant?
3. **Experience Fit** (15%): Is the experience level appropriate? (Candidate has 3 years. Entry-level to mid-level roles are ideal. Senior/Director roles should score lower.)
4. **Location Match** (15%): Is it in Seattle/Bellevue/Redmond/WA area or remote?
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


def score_job(client, job, profile_summary):
    """Score a single job using Claude."""
    salary_str = "Not specified"
    if job.get("salary_min") and job.get("salary_max"):
        salary_str = f"${job['salary_min']:,.0f} - ${job['salary_max']:,.0f}"
    elif job.get("salary_min"):
        salary_str = f"${job['salary_min']:,.0f}+"

    description = job.get("description", "No description available")
    if len(description) > 4000:
        description = description[:4000] + "\n...[truncated]"

    prompt = SCORING_PROMPT.format(
        profile_summary=profile_summary,
        title=job.get("title", "Unknown"),
        company=job.get("company", "Unknown"),
        location=job.get("location", "Unknown"),
        job_type=job.get("job_type", "Unknown"),
        salary=salary_str,
        description=description,
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        result_text = response.content[0].text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result_text)
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        return {"score": 0, "reasoning": f"Scoring failed: {e}", "red_flags": ["parse_error"], "highlights": []}
    except anthropic.APIError as e:
        return {"score": 0, "reasoning": f"API error: {e}", "red_flags": ["api_error"], "highlights": []}


def score_all_pending(limit=50):
    """Score all unscored jobs."""
    jobs = get_unscored_jobs(limit=limit)
    if not jobs:
        return []

    client = anthropic.Anthropic()
    profile_summary = get_profile_summary()
    scored = []

    for job in jobs:
        result = score_job(client, job, profile_summary)
        score = result.get("score", 0)
        update_job_score(job["job_id"], score, result)
        scored.append({**job, "score": score, "score_breakdown": result})

    return scored


if __name__ == "__main__":
    from rich.console import Console
    console = Console()
    console.print("[bold]Scoring pending jobs...[/bold]")
    results = score_all_pending()
    console.print(f"[green]Scored {len(results)} jobs[/green]")
    for r in sorted(results, key=lambda x: x["score"], reverse=True)[:5]:
        console.print(f"  [{r['score']}] {r['title']} @ {r['company']}")
