# Assumptions

Documented assumptions made while building this system (user was unavailable for Q&A).

## Candidate Assumptions

1. **Target location is Seattle, WA** — Based on UW Foster being in Seattle and MSCM target companies being Seattle-based (Amazon, Boeing, Costco, Starbucks, Microsoft).

2. **Work authorization will be OPT/CPT** — Assumed F1 student visa since she's currently in India and joining a US graduate program. STEM-designated MSCM gives 3-year OPT.

3. **Job timing is post-graduation (2027)** — But starting the search now to understand the market, build target lists, and be ready for internship/CPT opportunities during the program.

4. **Experience level targeting: entry-to-mid** — With 3 years at Uber, she's beyond pure entry-level but shouldn't target Senior/Director roles yet. Post-MSCM she'll be competitive for mid-level SCM roles.

5. **Broad role targeting is correct** — The user confirmed "all of the above" — SCM pure plays, Risk/Compliance in SCM contexts, and Program Management roles.

## Technical Assumptions

6. **JobSpy is the best scraping tool** — After researching 10+ options, JobSpy (3.5k stars, MIT, actively maintained, covers 8 boards) is the clear winner. Alternatives considered: Find-Me-Job (n8n-based, heavier), anandanair/job-scraper (GitHub Actions, less flexible), debytesio/claude-plugin-jobhunter (UK/France focused).

7. **Claude Sonnet for scoring** — Balances quality with cost. At ~$0.01-0.03 per job, scoring 50 jobs/day costs <$1.50/day. Could switch to Haiku if cost is a concern.

8. **Local SQLite is sufficient** — No need for Supabase/Postgres for a single-user personal tool. SQLite handles deduplication, history, and querying fine.

9. **No auto-apply** — This system identifies and ranks jobs only. Applying is manual and intentional.

10. **Daily cadence** — Running once per day with `hours_old=24` catches most new postings without excessive API usage or rate limit risk.

11. **No proxy needed initially** — Indeed has no rate limiting. LinkedIn may rate-limit after ~10 pages, but with 12 search queries × 4 locations, we're well within limits for 25 results each.

## Search Strategy Assumptions

12. **Seattle metro = Seattle + Bellevue + Redmond + Tacoma** — These are the main employment centers in the Puget Sound area accessible from UW.

13. **50-mile radius** — Covers the entire metro area without pulling in Portland or other distant cities.

14. **Exclude senior titles** — "Senior Director", "VP", "Principal", "15+ years" are filtered out as unrealistic targets.

15. **Include internships** — MSCM students often do summer internships via CPT. Including `internship` job type.

## What Might Need Adjusting

- **Search queries** — May need refinement after seeing initial results (too broad? too narrow?)
- **Scoring weights** — May need rebalancing once we see how scores distribute
- **Company tiers** — May want to add/remove companies based on actual hiring patterns
- **Salary floor ($70k)** — May be too high for internships, too low for some roles
- **Location preferences** — She might also consider Bay Area, NYC, or other SCM hubs
