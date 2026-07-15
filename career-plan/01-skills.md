# Skills — What to Build, How Deep, and When

[← Index](INDEX.md)

*The five-skill build plan, ordered by your own job data. Companion pages: [Projects](02-projects.md) · [Networking](03-networking.md) · [Reading](04-reading-list.md) · [Consulting](05-consulting.md) · [Edge](06-edge.md).*

---

## Read this first — why this order, and what these skills are actually for

I mined the full text of **3,576 real Program/Project Manager job descriptions** from your own scraped database. Here's what those roles actually demand:

| Rank | Skill | % of PM JDs |
|---|---|---|
| 1 | Cross-functional | **88%** |
| 2 | Communication | **74%** |
| 3 | **Risk** | **72%** |
| 4 | Stakeholder management | **66%** |
| 5 | **Excel** | **62%** |
| — | SQL | **8%** |
| — | Power BI / Python | **4% / 2%** |

**The takeaway that shapes this whole page:** the top of the demand list *is your Uber background* — risk, stakeholders, cross-functional work. You already clear those. So the tech skills below (SQL, Power BI, Python, vibe-coding) are **not** here to get you past keyword filters. Your résumé already passes those.

They exist for exactly two reasons:

1. **Portfolio proof** — so "strategic problem-solver" is *shown with a number*, not just claimed.
2. **Interview credibility** — so you can hold a data conversation and say *"I built this."*

**Your depth bar (say it out loud before every study session):**
> *Fluent — can build a prototype, understand the data, and turn it into a storyline. Not an engineer. Not a heavy business analyst.*

Excel comes first because it's 62% of JDs and gives you the fastest credibility. Everything after Excel is about turning your strategy into provable [projects](02-projects.md).

---

## The protective rule (don't skip this)

> **Understand every line for: SQL (all of it) + your FIRST Python project.**
> **Ship-fast for: everything after that.**

Why: SQL and your first real Python analysis are your *interview insurance*. If someone asks "walk me through how you got this number," you must be able to answer without hand-waving. Once you've earned that once, you're allowed to move fast — lean on AI, copy patterns, ship the thing. Depth first, speed second.

---

## The five skills, in order

### 1. Advanced Excel — *blended with SQL from Week 1*

| | |
|---|---|
| **Depth target** | Pivot tables, XLOOKUP, Power Query, clean dashboards |
| **Learn mode** | **Deep** (builds on your existing pivot/trend base) |
| **Why first** | 62% of PM JDs; fastest credibility; you're already partway there |
| **Scheduled** | **Weeks 1–3** ([schedule](MASTER-SCHEDULE.md)) |

**Resources:** [ExcelJet](https://exceljet.net) (formula reference + quick lessons) · [Microsoft Learn — Excel](https://learn.microsoft.com/training/) (Power Query, dashboards)

**Week-by-week:**
- [ ] **Wk 1** — Pivot tables refresher + XLOOKUP (ExcelJet)
- [ ] **Wk 2** — Power Query intro (import + shape data)
- [ ] **Wk 3** — Dashboard basics (turn a table into a one-glance view)

---

### 2. SQL — *the every-line skill*

| | |
|---|---|
| **Depth target** | JOINs, subqueries, CTEs, window functions |
| **Learn mode** | **Every line** — your explicit ask + interview insurance |
| **Why** | Only 8% of JDs list it, but it's the backbone of every data project and the thing interviewers probe |
| **Scheduled** | **Weeks 1–6** (blended with Excel, then deepened) |

**Resources:** [mode.com/sql-tutorial](https://mode.com/sql-tutorial/) (primary path) · [Kaggle Learn — Advanced SQL](https://www.kaggle.com/learn/advanced-sql) (CTEs, window functions) · [StrataScratch](https://www.stratascratch.com) (real interview-style practice)

**Week-by-week:**
- [ ] **Wk 1** — SELECT / WHERE / ORDER BY (mode Basics 1–3)
- [ ] **Wk 2** — COUNT / SUM / GROUP BY + JOINs start (mode 4)
- [ ] **Wk 3** — JOINs deep + subqueries (mode 5) + StrataScratch easy ×3
- [ ] **Wk 4** — Window functions intro (~1 light session — August deload)
- [ ] **Wk 5** — CTEs + window functions (Kaggle Advanced SQL)
- [ ] **Wk 6** — Apply SQL to real Starbucks project queries

> After Week 6, SQL becomes a *tool you use* on projects, not a subject you study. You keep it sharp by writing queries for [Amazon fraud](02-projects.md), rideshare, and the capstone.

---

### 3. Power BI — *working, for visual proof*

| | |
|---|---|
| **Depth target** | One real, end-to-end dashboard |
| **Learn mode** | **Working** (build one well — you don't need mastery) |
| **Why** | Low JD % (4%), but *high portfolio payoff* — a live dashboard is visual proof of insight generation, your edge |
| **Scheduled** | **Weeks 5–8** |

**Resources:** [Microsoft Learn — Power BI](https://learn.microsoft.com/power-bi/) (free, official, project-based)

**Week-by-week:**
- [ ] **Wk 5** — Power BI intro (Microsoft Learn), start alongside SQL
- [ ] **Wk 6** — Import data, build 2 visuals (on the Starbucks project)
- [ ] **Wk 7** — Dashboard formatting, KPI cards, slicers
- [ ] **Wk 8** — DAX basics (measures, calculated columns) — deload ends here

---

### 4. Python — *every line for project #1, then ship-fast*

| | |
|---|---|
| **Depth target** | pandas — read, clean, analyze, summarize data |
| **Learn mode** | **Every line for your first project**, then **ship-fast** |
| **Why** | Only 2% of JDs, but lets you hold a BA-level Python conversation and say "I built this" |
| **Scheduled** | **Weeks 9–12** |

**Resources:** [Udemy — "100 Days of Code: Python" (Angela Yu)](https://www.udemy.com/course/100-days-of-code/) (Days 1–17 is plenty) · [Kaggle Learn — Python](https://www.kaggle.com/learn/python) + [Pandas](https://www.kaggle.com/learn/pandas)

**Week-by-week:**
- [ ] **Wk 9** — Days 1–10: variables, loops, functions *(every line)*
- [ ] **Wk 10** — Days 11–17: file I/O + pandas + Kaggle Pandas 1–3 *(every line)* — this feeds your first Python flagship, **Amazon return-fraud**
- [ ] **Wk 11** — pandas deep: groupby, filtering, cleaning *(every line — interview insurance)*
- [ ] **Wk 12** — finish pandas; optional light intro to a model

> The **Amazon return-fraud** flagship (starts Wk 10) is your designated *understand-every-line* Python project. Once it's shipped, you've earned ship-fast mode for all later Python work.

---

### 5. Vibe-coding — *ship-fast, "I build things"*

| | |
|---|---|
| **Depth target** | Build small working apps with AI |
| **Learn mode** | **Ship-fast** (understand the shape, not every line) |
| **Why** | Breadth + an "I shipped a working app" story; pairs with light projects and hackathons |
| **Scheduled** | **Weeks 13–14** (then consolidation Wk 15) |

**Resources:** AI coding tools (Claude, Cursor, v0, Replit) — describe what you want, iterate, ship. No formal course; learn by building.

**Week-by-week:**
- [ ] **Wk 13** — Build a small app with AI; reuse it for a light project
- [ ] **Wk 14** — Polish the app; connect the pieces
- [ ] **Wk 15** — Consolidation — no new skill; apply everything to the rideshare capstone

---

## At-a-glance calendar

| Weeks | Aug deload? | Excel | SQL | Power BI | Python | Vibe |
|---|---|:---:|:---:|:---:|:---:|:---:|
| 1–3 | — | ● | ● | | | |
| 4 | 🟡 | | ○ | | | |
| 5–6 | 🟡 | | ● | ● | | |
| 7–8 | 🟡→ | | | ● | | |
| 9–12 | — | | (use) | | ● | |
| 13–15 | — | | (use) | (use) | (use) | ● |

● = actively learning · ○ = light session · (use) = applying it on projects

---

## Skill → interview talking point

When an interviewer asks about each skill, don't recite a syllabus — tell them what you *built* and what you *found*. Lead with the insight, mention the tool second.

| Skill | What to say when asked |
|---|---|
| **Excel** | *"It's my daily driver — pivots, XLOOKUP, Power Query. I built the Costco inventory-turn model and every project dashboard starts in Excel before it graduates to Power BI."* |
| **SQL** | *"Comfortable end-to-end — JOINs, CTEs, window functions. On the Starbucks throughput project I wrote the queries myself to find the peak-hour bottleneck; happy to walk through the logic."* |
| **Power BI** | *"I build dashboards that a stakeholder can read in one glance — KPI cards, slicers, the story on top. The point isn't the chart, it's the decision it drives."* |
| **Python** | *"I use pandas to clean and analyze data — I recreated my Uber fraud-triage work on public e-commerce data and can explain every step. I'm fluent, not an engineer, and that's exactly the level the role needs."* |
| **Vibe-coding** | *"I ship small tools fast with AI — I built a working app for [project] in a weekend. I care more about solving the problem than writing perfect code, and AI lets me move at the speed of the idea."* |

**The through-line for all five:** *"Tech is how I prove the insight. My edge is framing the real problem and recommending the fix — the code just makes it undeniable."*

---

*Next: turn these skills into proof → [Projects](02-projects.md). Timeline source of truth → [Master Schedule](MASTER-SCHEDULE.md).*
