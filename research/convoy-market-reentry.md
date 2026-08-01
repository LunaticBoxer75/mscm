# US Freight Brokerage / Freight-Tech — Market Re-Entry Analysis

**Buyer lens:** entrant re-entering with a differentiated value proposition (a "Convoy 2.0") · **Geography:** US (with US–Mexico cross-border) · **Compiled:** 2026-07-21

*A forward-looking strategy deliverable, structured as a Senior Engagement Manager brief. This is the market case for re-entry — it does not repeat the company teardown, failure post-mortem, network-effects flywheel, or SWOT already covered in the companion document [`convoy-seattle-freight-logistics.md`](convoy-seattle-freight-logistics.md). Confidence caveats and assumption flags are noted inline.*

---

## 1. Executive Summary & Market Sizing

- **The re-entry question is not "can software beat the phone" (settled) but "is there a defensible wedge a pure digital broker lacked."** The 2015–2023 thesis died on commoditization, not technology; a credible return must attack a *structurally* stickier segment or sell the *software layer*, not the freight spread.
- **The window is cyclically attractive.** After the 2022–2024 down-cycle, US truckload is in early recovery in 2026 — capacity has exited and spot rates are firming. Re-entering *into* a tightening market (the opposite of Convoy's 2022 peak-entry) inverts the original timing error.

**Market sizing (top-down; all figures flagged — see assumptions):**

| Layer | Definition | Estimate (2025–26) | Basis / assumption |
|---|---|---|---|
| **TAM** | Total US freight-brokerage gross revenue (all modes) | **~$70–90B** | Down-cycle normalization from the ~$88B 2022 peak; definitional variance between gross-brokered-revenue vs. net |
| **SAM** | Truckload (dry van + reefer, spot + contract) brokerage amenable to automated matching | **~$28–36B** | Assumes ~40% of brokerage is digitizable FTL; excludes LTL, project, white-glove |
| **SOM (3–5 yr)** | Realistic capture for a well-funded, differentiated #3+ entrant | **~$0.6–1.2B gross / ~$90–180M net revenue** | 2–4% of SAM at a ~15% blended take rate |

- **Growth:** Overall brokerage is **low-single-digit CAGR (2–4%)** and cycle-bound; the *digital-penetration* sub-segment grows **~25–30% CAGR** off a small base (~$3–6B in 2024). **The growth is in the mix-shift to digital + AI-native ops, not in market expansion.**
- **Key growth drivers:** (1) AI/agentic automation collapsing brokerage opex; (2) **US–Mexico nearshoring** inflating cross-border truckload volume; (3) shipper demand for API/embedded freight and real-time visibility; (4) generational digitization of small carriers.

> **Assumption flags:** Brokerage TAM figures diverge 40–60% across sources depending on gross-vs-net and mode inclusion. Digital-brokerage sizing is analyst-estimated with wide bands.
> **Next step:** commission a bottoms-up build from ATA / Armstrong & Associates 3PL data + FMCSA carrier counts; validate take-rate assumptions via 8–10 shipper procurement interviews.

## 2. Value Chain & Ecosystem Dynamics

**Chain:** Shipper (BCO) → **[TMS / procurement software]** → **[Broker / digital broker / load board]** → Carrier (fleet or owner-operator) → Receiver. Adjacent: factoring, insurance, ELD/telematics, freight-payment/audit.

| Stage | Players | Margin / value capture |
|---|---|---|
| Shipper procurement software (TMS) | SAP, Oracle, e2open, project44 (visibility) | **High, sticky** — system-of-record lock-in |
| **Data / load-board layer** | **DAT, Truckstop** | **Highest-quality margin** — asset-light SaaS + data network, ~duopoly, took no freight risk (and ended up owning Convoy's tech) |
| Brokerage / matching | C.H. Robinson, RXO, TQL, Echo, Uber Freight | **Thin & cyclical** — 12–18% gross, near-zero net in down-cycles |
| Carriers | ~90%+ have <6 trucks | **Lowest & most volatile** — price-takers |

- **So what:** Value concentrates at the **data/software layer (DAT-style) and the system-of-record (TMS)** — *not* in the brokerage spread. The single most important strategic read for re-entry: **Convoy's technology had durable value (resold twice, ~$16M → ~$250M); its brokerage book had none.** A re-entrant should aim to *own or embed into* the data/software layer, not re-fight the spread.

## 3. Competitive Landscape (MECE Segmentation)

- **Incumbent scale brokers:** C.H. Robinson, TQL, RXO, Echo — profitable, relationship + scale moats, now AI-enabled.
- **Platform-backed digital brokers:** Uber Freight — survives on parent balance sheet, chronically unprofitable.
- **Data/software layer:** DAT, Truckstop — asset-light, high-margin, structurally advantaged.
- **Niche / specialist:** reefer specialists, drayage/intermodal, cross-border (Nuvocargo, Redwood), flatbed.
- **Casualties (cautionary):** Convoy (shut 2023), Transfix (SPAC collapse), Emerge, NEXT.

| Dimension | C.H. Robinson | Uber Freight | DAT (data layer) | Cross-border specialist (e.g., Nuvocargo) |
|---|---|---|---|---|
| **Core value prop** | Scale + service + capacity assurance | App-based matching + Uber brand | Neutral load/rate data network | Digitized US–Mexico freight + customs/compliance |
| **Pricing model** | Brokerage spread (12–18%) | Spread, subsidized | SaaS subscription + data | Spread + FX/customs services |
| **Key strengths** | Profitability, relationships, data depth | Capital access, UX | Network-effect data monopoly, no freight risk | Regulatory moat, nearshoring tailwind, sticky |
| **Vulnerabilities** | Legacy cost base, disruptable ops | No path to profit, no moat | Not a freight P&L (by design) | Sub-scale, geography-concentrated |

## 4. Customer Needs & Friction Points (KPCs)

**Shippers (buyers)** — Key Purchasing Criteria, ranked: (1) **capacity assurance** in tight markets (no tender rejections); (2) price predictability; (3) real-time visibility / API into their TMS; (4) service reliability; (5) sustainability reporting.
- *Under-served:* guaranteed contract capacity in specialized modes (reefer, cross-border) — where incumbents are weakest and digital coverage thinnest.

**Carriers (supply)** — KPCs: fast/guaranteed pay, load density, low deadhead, transparent pricing, self-serve booking.
- *Friction:* multi-homing is frictionless → **retention requires continuous subsidy** (the wound that killed Convoy). Any re-entry UVP must reduce carrier *acquisition/retention cost*, not just improve carrier UX.

- **Switching costs / adoption barriers:** Near-zero on both sides in generic dry-van — the core structural problem. **Higher** in (a) integrated TMS/embedded-API relationships, (b) compliance-heavy cross-border, (c) dedicated/contract reefer capacity. **Re-entry must manufacture the switching costs it previously lacked.**

## 5. Industry Trends & Regulatory Tailwinds / Headwinds

**Top 3 macro trends (3–5 yr):**

1. **Agentic AI in brokerage ops** — LLM agents now automate quoting, track-and-trace, appointment scheduling, and exception handling. This compresses the opex that made brokerage unprofitable — but it is available to *everyone*, so it is table stakes, not a moat, unless owned as software sold to other brokers.
2. **Nearshoring / US–Mexico cross-border** — the highest-growth truckload corridor; regulatory + FX + customs complexity creates genuine switching costs. Structural tailwind through the decade.
3. **Freight-cycle recovery + capacity rationalization** — the 2022–24 washout removed marginal carriers; 2026 is early up-cycle, favorable for a spread business's unit economics.

**Regulatory:**

- **Tailwinds:** FMCSA broker-transparency rulemaking (margin disclosure) pressures opaque incumbents — favors a transparent-by-design entrant.
- **Headwinds / burdens:** broker bond & authority requirements; cross-border customs (CBP/ACE); USMCA compliance; and rising cargo-theft / **double-brokering fraud** liability (a 2024–26 epidemic requiring identity/verification investment).

> **Flag:** The USMCA review (2026) is a live geopolitical variable — tariff / trade-policy shifts could amplify *or* disrupt the nearshoring thesis.
> **Next step:** scenario-model cross-border volumes against 2–3 trade-policy outcomes.

## 6. Strategic Synthesis & High-Leverage Risks

**Three re-entry opportunities (differentiated UVP — "Convoy 2.0"):**

1. **Sell the software, not the spread (asset-light SaaS / AI-agent layer).** License an AI-native brokerage OS to the thousands of mid-size traditional brokers — the DAT-validated model, and literally where Convoy's own tech landed value. *Escapes the commodity spread entirely.* **Highest-defensibility play.**
2. **Own a switching-cost-rich vertical: cross-border (US–Mexico) reefer / dry-van.** Combine the nearshoring tailwind + a customs/compliance moat + specialized capacity. Smaller TAM, far deeper moat than generic dry-van.
3. **Capacity-as-a-service + fraud-proof carrier identity.** Monetize verified, vetted carrier identity (against the double-brokering epidemic) as a trust layer — a need incumbents are failing to meet, and one that *creates* the switching cost Convoy never had.

**Critical risks to stress-test (deal-breakers):**

- **Moat re-test:** Does the wedge create real switching costs, or is it another copyable feature? (Convoy's fatal flaw — do not repeat.)
- **Capital discipline:** Can it reach net-revenue profitability *within* one freight cycle without subsidy-buying volume? Underwrite to the trough, not the boom.
- **Incumbent AI catch-up:** C.H. Robinson / RXO are deploying the same agentic AI with more data — a pure automation edge erodes in 18–24 months.
- **Brand liability:** Does the "Convoy" name carry more equity than baggage with carriers left unpaid in 2023? Test directly.

> **Primary-research next steps:**
> 1. 8–10 shipper procurement-lead interviews on cross-border + capacity-assurance willingness-to-pay.
> 2. Carrier survey (n ≥ 300) on identity/trust and multi-homing behavior.
> 3. 3–4 mid-market broker interviews to size the software-licensing SAM.
> 4. Expert calls with ex-DAT / ex-Convoy operators on software-layer economics.
> 5. Bottoms-up TAM rebuild from Armstrong & Associates + ATA data.
