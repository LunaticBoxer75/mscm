# Portfolio — Your Proof Engine

[← Index](INDEX.md)

Your edge is **strategy and framing**, not the query. So every project here exists to make one sentence *provable* instead of *claimed*:

> *"Strategic problem-solver who turns messy situations into clear solutions — and brings risk, compliance & governance discipline into operations and into how teams adopt AI safely."*

The tech (SQL/Python/BI) is only there to (1) **prove** the insight and (2) buy you **interview credibility** so you can say *"I built this."* Depth bar: **fluent, can build a prototype, understand the data, tell the story — not an engineer.** Every project ends in a **recommendation**, because that's where you win.

Related: [Skills](01-skills.md) · [Networking](03-networking.md) · [Reading](04-reading-list.md) · [Consulting](05-consulting.md) · [Edge](06-edge.md)

---

## 1. The 4-Step Sourcing Method

This is a reusable skill, not a one-time exercise. Find a *real* problem a *real* company has, then solve a slice of it with public data. Four ways in:

| Step | What you're hunting | Where to look |
|---|---|---|
| **1. Public pain points** | A problem a company has *said out loud* | **Earnings-call transcripts** (they name their own bottlenecks), **Glassdoor** (employees describe broken processes), **App Store / Play reviews**, **Reddit** (r/uberdrivers, r/starbucksbaristas), news headlines |
| **2. Public data** | Numbers to actually analyze | **Kaggle** (search the company/industry), **10-K / annual reports** (inventory turns, margins, risk factors), **CFPB complaints DB** (consumer-finance risk patterns), **Yelp** & App reviews (voice-of-customer), gov/health open data (data.gov, CDC, HHS) |
| **3. The JD mirror** | What your target roles need *solved* | Pull 5 real Program/Ops JDs → list the verbs ("reduce cost," "improve throughput," "manage risk") → build the project that demonstrates that verb |
| **4. Your own scar tissue** | Problems you already lived at Uber | Appeals queue, fraud triage, SOP gaps, escalation design — recreate with public or synthetic data. **This is your unfair advantage** — you already know the real problem |

**Rule of thumb:** the strongest projects stack two of these — a *named* pain point (Step 1) + *real* data (Step 2). "Starbucks said in their earnings call that mobile-order throughput is a problem" + a public QSR wait-time dataset = a project nobody can wave away.

---

## 2. The Case-Study Format (use the SAME one every time)

Consistency is a signal. Six beats, always in this order:

1. **Problem** — 1–2 sentences, real and public. *Cite where you found it* (the earnings call, the review, the news).
2. **Approach** — how you framed it and what you'd measure. (Your framing = your edge — spend words here.)
3. **Key finding** — one sentence, **with a number.** ("38% of returns flagged came from 6% of accounts.")
4. **What I built** — the SQL / Python / dashboard. Screenshot + link. Keep it short; the build serves the finding.
5. **Recommendation** — **your differentiator.** The specific action you'd take and the projected impact. This is the part hiring managers remember.
6. **What I'd do next** — one honest line on the limitation and the next iteration. Shows maturity, not gaps.

> Print this six-line skeleton and fill it in *before* you write a single query. If you can't state the Problem and the Recommendation-shape up front, you're not ready to build yet.

---

## 3. Portfolio Layout — One Clean Notion Page

One page. Scannable in 30 seconds. A hiring manager should see the numbers before they scroll.

```
┌─────────────────────────────────────────────┐
│  ABOUT — 3 lines: brand line + risk→AI thesis │
│         + "here's what these projects prove"  │
├─────────────────────────────────────────────┤
│  ★ 3 FLAGSHIPS — big impact NUMBER each       │
│    [Starbucks]   [Amazon fraud]  [Rideshare]  │
│     "-22% wait"   "3x caught/hr"  "-15% cxl"   │
├─────────────────────────────────────────────┤
│  7 LIGHT PROJECTS — tidy grid, 1 line each    │
│    ▢ ▢ ▢ ▢                                    │
│    ▢ ▢ ▢                                      │
├─────────────────────────────────────────────┤
│  Resume (PDF)   ·   LinkedIn                   │
└─────────────────────────────────────────────┘
```

- **About** — your [brand line](00-career-map-spec.md), the risk→AI thesis, one line on what the work proves.
- **3 flagships up top**, each with a **big number** (the Key finding). These are your interview centerpieces.
- **7 light projects in a grid** — one line + one link each. Breadth and "I ship."
- **Resume + LinkedIn** at the bottom, always linked. Also add this page to LinkedIn **Featured** (Polish, [Week 17](weekly/week-17.md)).

---

## 4. Your 10 Projects

**8 locked + 2 open.** Flagships marked ★. Two projects (marked **🎯 risk→AI**) carry your differentiator thesis — they end in a *governance* recommendation, showing you can bring risk discipline into how a team automates a decision with a model.

| # | Project | Type | Skills | Weeks | Thesis |
|---|---|---|---|---|---|
| 17 | Lean Six Sigma DMAIC case | Light | Excel + process | **2–3** | |
| 4 | Costco inventory-turn strategy memo | Non-tech | Strategy + Excel | **3–4** | |
| 1 | ★ Starbucks mobile-order throughput | **Flagship** | Excel/SQL + Power BI | **5–8** | |
| 2 | IKEA stockout & last-mile delay | Light | SQL + Power BI | **7–8** | |
| 15 | 🏥 Hospital PPE stockout | Light | SQL + Power BI | **9–10** | |
| 3 | ★ Amazon return-fraud triage | **Flagship** | SQL + Python | **10–12** | 🎯 |
| 13 | Fraud-pattern detection | Light | SQL + Python | **12–13** | 🎯 |
| 5 | ★ Rideshare cancellation (capstone) | **Flagship** | SQL + Python + BI | **13–15** | |
| A | OPEN slot — your idea | Light | your call | **15** | |
| B | OPEN slot — your idea | Light | your call | **16** | |

Full week-by-week: [MASTER-SCHEDULE](MASTER-SCHEDULE.md). Skill build order: [Skills](01-skills.md).

---

### Project Cards

Each card: **Problem → Data → Skills → Weeks → What the Recommendation must demonstrate.**

---

#### #17 · Lean Six Sigma DMAIC case · Light · Weeks 2–3
- **Problem:** Take one documented, real, public process that has waste or defects (e.g., a clinic check-in, a drive-thru line, a returns-handling process) and run a full **Define-Measure-Analyze-Improve-Control** cycle on it.
- **Data:** A publicly documented process (company blog, ASQ / Six Sigma case libraries) + a realistic synthetic cycle-time/defect dataset you build, or a Kaggle call-center / manufacturing-defect dataset.
- **Skills:** Excel (control charts, Pareto), light SQL, DMAIC method.
- **Recommendation must demonstrate:** you can run a **rigorous improvement method end-to-end** and quantify the win — "this change cuts cycle time X%." Cashes in your **Lean Six Sigma Yellow Belt** as your very first published proof (project 1 of 10).

#### #4 · Costco inventory-turn strategy memo · Non-tech · Weeks 3–4 (deload-friendly)
- **Problem:** Why does Costco's low-SKU, membership model beat competitors on inventory turnover? Strategic teardown vs. Walmart / Target / BJ's.
- **Data:** **10-Ks and annual reports** (compute inventory turns and days-inventory yourself from the filings), investor decks, earnings calls.
- **Skills:** Strategy + light Excel (ratios from filings). Almost no code — perfect for the August exam-crunch deload.
- **Recommendation must demonstrate:** business & financial literacy plus **strategic framing** — a crisp recommendation *for a competitor*. This is your core edge (insight, not queries) on full display, and it warms you up for the *Financial Intelligence* book later.

#### #1 · ★ Starbucks mobile-order throughput · FLAGSHIP · Weeks 5–8
- **Problem:** Mobile-order surges create peak-hour bottlenecks and in-store congestion — a problem **Starbucks has named in its own earnings calls**. Model the peak-hour bottleneck and staffing, then recommend a fix.
- **Data:** Starbucks **earnings-call transcripts** (the pain point in their own words) + a public QSR/restaurant wait-time or foot-traffic dataset (Kaggle) + a synthetic peak-hour order-arrival curve you model.
- **Skills:** Excel/SQL for the analysis, **Power BI** for a peak-hour throughput dashboard.
- **Recommendation must demonstrate:** a concrete **operational lever** (e.g., a dedicated mobile-order handoff station, staggered barista scheduling at peak) with a **projected throughput gain / wait-time cut**. Your first flagship on a dream company — the interview centerpiece that proves you frame a real problem and land a quantified fix (project 3 of 10).

#### #2 · IKEA stockout & last-mile delay · Light · Weeks 7–8
- **Problem:** Stockouts and last-mile delivery delays erode sales and customer experience — well-documented for IKEA and loud in **App Store / Trustpilot reviews**.
- **Data:** Public retail inventory/demand datasets (Kaggle), IKEA **App Store & Trustpilot reviews**, news; synthetic inventory data where needed.
- **Skills:** SQL + Power BI (deliberately reuses your Starbucks dashboard skills — faster second lap).
- **Recommendation must demonstrate:** *where* inventory breaks and a specific fix — a reorder-point / safety-stock adjustment or a last-mile lever. Shows supply-chain diagnosis on a second dream company.

#### #15 · 🏥 Hospital PPE stockout · Light · Weeks 9–10
- **Problem:** Hospitals ran out of PPE (masks, gowns) during demand surges. Apply a supply-chain lens to health data and prevent the next stockout.
- **Data:** Public hospital-supply / PPE datasets (data.gov, HHS, CDC), the **CDC PPE Burn-Rate** methodology (public), CMS data; synthetic burn-rate model.
- **Skills:** SQL + Power BI.
- **Recommendation must demonstrate:** a **par-level / buffer-stock or demand-forecast** recommendation that prevents stockout. Doubles as your **healthcare (B.Sc) tie-in** — a differentiated angle most PM candidates can't offer (project 5 of 10, halfway ✅).

#### #3 · ★ Amazon return-fraud triage · FLAGSHIP · Weeks 10–12 · 🎯 risk→AI
- **Problem:** E-commerce return fraud (wardrobing, empty-box, receipt fraud) costs retailers billions. Amazon must decide *which* returns to investigate. **Recreate your Uber fraud-triage prioritization** on public returns/e-commerce data.
- **Data:** Kaggle e-commerce transactions / returns datasets, public fraud datasets (IEEE-CIS Fraud Detection, credit-card fraud), NRF return-fraud statistics (public), synthetic returns.
- **Skills:** SQL + Python (pandas + a light risk-scoring model).
- **Recommendation must demonstrate — TWO layers:**
  1. **Ops:** a triage rule that maximizes **caught-fraud per investigator-hour.**
  2. **🎯 Governance (the thesis):** guardrails for *safely automating* this with a model — false-positive/customer-friction thresholds, bias checks, human-in-the-loop, an audit trail. **This is where "I bring risk & governance discipline into how teams adopt AI safely" is shown, not claimed.** Your scar-tissue flagship (project 6 of 10).

#### #13 · Fraud-pattern detection · Light · Weeks 12–13 · 🎯 risk→AI
- **Problem:** Detect fraud patterns in transaction data with rules + a light model. A fast spin-off of the Amazon flagship that leans on your fraud background.
- **Data:** Kaggle credit-card fraud dataset, IEEE-CIS, synthetic transactions.
- **Skills:** SQL + Python.
- **Recommendation must demonstrate:** a **rules-plus-model** detection approach **and where to draw the automation line** — precision/recall tradeoff, what to auto-block vs. flag-for-review, model monitoring. **Second project carrying the risk→AI thesis** (project 7 of 10).

#### #5 · ★ Rideshare cancellation · FLAGSHIP / capstone · Weeks 13–15
- **Problem:** Rider and driver cancellations hurt marketplace liquidity and CX. Why do they cancel, and which ops levers reduce it? **Your own Uber scar tissue** — the most authentic story you have.
- **Data:** Kaggle rideshare/trip datasets (Uber/Lyft/Ola cancellation data), App Store reviews and **Reddit** (r/uberdrivers) for the qualitative "why," synthetic where needed.
- **Skills:** SQL → Python → Power BI, **connected into one end-to-end pipeline** (this is the capstone — it shows the full stack works together).
- **Recommendation must demonstrate:** ops levers to reduce cancellation rate (ETA accuracy, matching radius, surge communication) with a **projected reduction %.** The capstone that proves the whole toolkit + your strategic recommendation in one artifact (project 8 of 10).

---

### OPEN Slots A & B (your own ideas) · Weeks 15–16

Two slots are deliberately yours — pick problems *you* care about (reviews/voice-of-customer, subscription churn, a menstrual-health program design, the meta "analyze this job-search repo" idea — see [spec §6a](00-career-map-spec.md) for the full menu). Before you commit a slot, run it through this checklist:

- [ ] **Real, nameable problem.** Can I point to an earnings call, a review thread, or a news story that says this is broken?
- [ ] **Public data exists.** Kaggle / 10-K / CFPB / reviews / gov data — or a defensible synthetic set. (Don't pick a problem you can't get numbers for.)
- [ ] **One number.** Will this produce a single Key-finding number I can put on the portfolio card?
- [ ] **Ends in a recommendation.** Is there a clear action + projected impact — the part that's *my* edge?
- [ ] **Right size.** Buildable in ~1 week at ship-fast depth (these are Light, not flagships).
- [ ] **Adds something new.** A skill, an industry, or the risk→AI thesis I haven't already shown.

If a slot idea checks all six, it's a good project. If it misses "one number" or "ends in a recommendation," reshape it before you start.

---

**Cadence reminder:** publish each project the week it finishes, in the [six-beat format](#2-the-case-study-format-use-the-same-one-every-time), to the [Notion layout](#3-portfolio-layout--one-clean-notion-page). By [Week 16](MASTER-SCHEDULE.md) all 10 are live and the portfolio is ready for Polish. Networking runs the whole time ([Networking](03-networking.md)) so December isn't a cold start.
