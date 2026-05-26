# External Resources & Tools Researched

Tools and repos evaluated for this project. Some are integrated, others are documented for future reference.

## Integrated (What We Use)

### JobSpy — Core Scraping Engine
- **Repo:** https://github.com/Bunsly/JobSpy (3.5k stars, MIT)
- **Install:** `pip install -U python-jobspy`
- **Covers:** LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter, Bayt, Naukri, BDJobs
- **Why chosen:** Most popular, actively maintained, simple API, returns pandas DataFrame, covers all major US boards.
- **Limitations:** LinkedIn rate-limits after ~10 pages (proxies needed for heavy use). Indeed is unlimited.

### Claude API — AI Scoring
- **SDK:** `pip install anthropic`
- **Model:** claude-sonnet-4-20250514 (cost-effective for structured scoring)
- **Cost:** ~$0.01-0.03 per job scored

---

## Alternatives Evaluated (Not Integrated, But Worth Knowing)

### Full Pipeline Solutions

| Tool | Stars | Approach | Why Not Chosen |
|------|-------|----------|----------------|
| [findajob](https://github.com/brockamer/findajob) | 7 (but 810 commits, 68 releases) | Docker + Fly.io, LLM via OpenRouter, 22% interview rate | Heavier infra, designed for self-hosted deployment |
| [Find-Me-Job](https://github.com/MohamedMamdouh18/Find-Me-Job) | 15 | Docker + n8n + Streamlit, any LLM | Requires Docker orchestration, overkill for our use case |
| [anandanair/job-scraper](https://github.com/anandanair/job-scraper) | 23 | GitHub Actions + Supabase + LiteLLM | Good zero-infra option; LinkedIn + CareersFuture only |
| [ai-job-scraper](https://github.com/BjornMelin/ai-job-scraper) | 32 | Local LLM (vLLM) + Streamlit | Requires GPU, privacy-focused |

### Claude Code Plugins

| Tool | Stars | What It Does | Why Not Chosen |
|------|-------|--------------|----------------|
| [claude-plugin-jobhunter](https://github.com/debytesio/claude-plugin-jobhunter) | 12 | 14 UK/France boards, 8-dim scoring, tax analysis, Excel export | UK/France focused, requires DEB Cloud auth |
| [jobgpt-mcp-server](https://github.com/6figr-com/jobgpt-mcp-server) | 8 | MCP server with 34 tools, auto-apply | Paid credit system, hosted service |

### Auto-Apply Agents (NOT recommended for initial job search)

| Tool | Stars | What It Does |
|------|-------|--------------|
| [Job_search_agent](https://github.com/surapuramakhil-org/Job_search_agent) | 149 | CrewAI + Selenium auto-apply |
| [job-application-bot-by-ollama-ai](https://github.com/lookr-fyi/job-application-bot-by-ollama-ai) | 441 | Desktop agent, Ollama, auto-applies on multiple boards |

### APIs Worth Knowing

| API | Access | Coverage |
|-----|--------|----------|
| RapidAPI JSearch | REST (200 free/month) | LinkedIn, Indeed, Glassdoor aggregation |
| USAJobs API | Free (API key) | US government jobs |
| Adzuna API | Free tier | 16 countries |
| RemoteOK | JSON feed (free) | Remote-only jobs |
| Greenhouse Board API | Free per-company | `boards-api.greenhouse.io/v1/boards/{company}/jobs` |
| Lever Postings API | Free per-company | `api.lever.co/v0/postings/{company}` |

---

## Future Enhancements to Consider

1. **Add company-specific ATS scraping** — Greenhouse/Lever/Workday APIs for target companies (Amazon, Boeing, etc.)
2. **Telegram/Slack notifications** — Push top matches to phone
3. **Resume tailoring** — Auto-generate role-specific resume versions
4. **Cover letter generation** — AI-generated cover letters per job
5. **Application tracker** — Track what's been applied to, interview status
6. **Proxy rotation** — For heavier LinkedIn scraping if needed
7. **findajob integration** — If we want the full pipeline with proven 22% interview rate approach
