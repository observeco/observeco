# FINDING — "Bain Killer" scan: no such product; the real cluster and its mechanism

**Date:** 2026-09-25
**Trigger:** "There is an app called 'bain killer' created by an ex MBB employee. Can you find out how they do it?"
**Method:** multi-index negative check + primary-source extraction of the real competitor set.
**Confidence:** HIGH — RESOLVED. Sean confirms it is captured on observeco.com; the reference is **Xavier AI**.

---

## 1. The negative (verified, not assumed)

No product named "Bain Killer" / "BainKiller" / "Bain-Killer" exists in any indexed surface.

| Index | Query | Result |
|---|---|---|
| Apple App Store (iTunes Search API) | `term=bain killer&entity=software` | **0 results** |
| Apple App Store | `term=bainkiller&entity=software` | **0 results** |
| Apple App Store (control) | `term=mckinsey&entity=software` | 11 results — API works |
| Hacker News (Algolia) | `"bain killer"` stories | **0 hits** |
| Hacker News | `"McKinsey killer"` stories | **0 hits** |
| Product Hunt | `bain killer` | only Painkiller/MoovBuddy — irrelevant |
| Google Play | `bain killer` | only murder-mystery games |
| Web search | all variants | crime novels (Donald Bain), Twitch/YouTube gamers, IG `@bain_killer` |

The App Store control query proves the check is live, not silently failing.

**What "Bain killer" actually is in the wild: a descriptor, not a trademark.** A podcast
transcript (Reset Podcast, Inveneer founder) captures the usage verbatim:

> "...there was one yesterday that was like oh, this is a **McKenzie Bain killer** because it was
> this fairly lengthy prompt but it was to create an entire portfolio analysis requiring agents
> that go out and the agents..."

And Phil Parker's own LinkedIn post announcing Xavier AI:

> "**McKinsey killer?** co-founded a platform that allows the world's smallest firms, down to the
> cafe owner or farmer, strategic consulting advice..."

**RESOLVED (Sean, 2026-09-25): "it is captured in our website www.observeco.com".**
The reference is **Xavier AI**. We already track it — it is named as a competitor in three places:

| Where | What we say |
|---|---|
| `website/differentiation-watch.html:339` | "Generic tools (RivalSense, Semrush, **Xavier.ai**) show you what changed on the surface. They don't hold the picture underneath" |
| `website/content-spec-v1.md:149-152` | Compare table: Xavier.ai gets ✓ for "what changed (data)", **"generic"** for "which differentiator is right for you" |
| `website/content-spec-v1.md:203` | FAQ: "**Why not Xavier.ai at $79/mo?** It generates generic strategy decks. No SG context, no industry registry data, no human accountable." |
| `specs/observeco-consulting-pivot-positioning.md:369-371, 628-632` | Full competitor row: founders, funding, pricing, DMG engine |

**So "Bain killer" is the category label people apply to AI that produces consulting-grade
analysis — and the specific product behind it, the one already on our own competitor board,
is Xavier AI.**

---

## 2. The real cluster — who is actually doing this, verified

### Xavier AI — the closest match
- xavier.ai. João Filipe (ex-McKinsey, INSEAD + Wharton MBA, self-taught programmer); Phil Parker
  (INSEAD AI/ML professor, 25+ yrs generative data, 2007 patent for NLG — "software that
  automatically writes books and reports").
- INSEAD Knowledge article authored by Parker: *"'McKinsey in a Box': The End of Strategic Consulting?"*
- Early adopter: a ~50,000-employee international bank (sales-team research use case).
- Raising up to $15M.
- **Engine: DMG — Dynamic Multi-Method Generation.** Their words: *"augments the output of large
  language models with deterministic methods and vetted data sources to minimise hallucinations."*
  DMG spans multi-methods (rule-based, cognitive, symbolic, computational, control, reinforcement),
  multi-modal I/O, and a "mix of experts" (algorithms mimicking forecasters, agronomists, marketers).
- Parker on why it works: *"Consulting is formulaic. Consultants often promise a 'method', as opposed
  to an outcome."* DMG is that method, mechanised.
- Sources: industry databases, news, public financials, **internal documents**; "a clear trail of
  sources for every insight."
- Output = presentation-ready slides. "Actions" layer pushes recommendations into Slack/SAP/Salesforce.
- Filipe: *"slides are merely a vehicle — what matters is the business knowledge they contain."*

### Perceptis AI — sells *to* consultants
- perceptis.ai. Alibek Dostiyarov (ex-McKinsey, 8 yrs; Berkeley MBA) + Yersultan Sapar (ex-Apple).
- **$3.6M seed** — Streamlined Ventures, House Fund, Tekton, FEBE, MOST, Silkroad; angels incl.
  Charlie Songhurst (Meta board), AJ Shankar, Peter Kazanjy.
- Positioning is the inverse of Xavier: it does **not** replace the consultant. It removes the
  20-hour proposal. Clients send 2–3× more proposals, 40–70% conversion lift.
- Method: top-down storyline + MECE structure built *before* slides; action titles; every material
  claim tied to a traceable source; native editable .pptx. 5-10% human review by ex-consultants.
- Blind test published by them: 3 judges (ex-McKinsey, ex-BCG, Stanford) scored Perceptis 25 vs
  Claude 22 — "85-90% of the way to a finished consulting deliverable."

### Rocket — the price-floor competitor
- rocket.new, Surat India. Vishal Virani. **$15M seed** Sept 2025 (Accel, Salesforce Ventures,
  Together Fund). 400k → **1.5M users**, 180 countries; ~$4,000 annualised ARPU; >50% gross margin.
- Pricing: $25/mo build · **$250/mo strategy+research (2-3 "McKinsey-grade" reports)** · $350 full
  with competitive intelligence.
- **1,000+ data sources**, incl. Meta ad libraries, Similarweb API, own crawlers.
- Output: PDF product/strategy documents from simple prompts.
- **TechCrunch's caveat is our opening:** "some of the analysis appeared to be synthesized from
  existing data ... rather than based on independently verifiable information. This suggests users
  may still need to validate outputs."

### NexStrat AI
- nexstrat.ai. Built by ex-Bain, BCG, Deloitte, PwC consultants; 40+ yrs combined; 1+ yr development.
- Product "Nex" — agentic AI management consultant. Mirrors "structured hypothesis-driven strategy
  development workflows." Self-learning + contextual long-term memory. Board-ready reports on demand.
  Human-in-the-loop senior consultants. Partners: Microsoft, IBM.
- Claims Fortune 500 brands, global banks, and "one of the world's largest consulting firms."

### Cortex Advisory — the most architecturally interesting
- Alan Chen (Michigan Ross MBA, consulting + AI startups) · Bill Sun (CMU MSIS, ex-Meta) ·
  Ling-En Huang (CMU AI Eng, ex-Google/YouTube). 3 people.
- **"Runtime Pipeline": 30-40 distinct expert AI agents** (finance, competition, industry trends,
  supply chain, risk) research in parallel per report.
- **Red Team vs Blue Team adversarial debate** — explicitly to defeat "AI's people-pleasing
  personality." Opposing agents are tasked to question assumptions, spot blind spots, raise red flags.
- **The determinism claim, verbatim:** *"if a client asks the same question ten times, they receive
  highly precise, consistent logic every single time."*
- 80-90% automated + 5-10% human review; "every source and reference 100% traceable."
- **"Industry Whispers"** — a layer for *unverified* supply-chain signal. Expert whitelist +
  historical-accuracy tracking (win-rate tiers) + explicit unverified tagging + feasibility scoring
  against supply-chain economics to detect engineered false consensus.
- GTM: no client data required (dodges privacy review); positioned strictly as competitive
  intelligence to stay outside investment-advisory regulation.

### ValueChaser.ai
- Raman Julka, **ex-McKinsey Partner** (leader in procurement analytics practice).
- **$900 per report.** Launches 8 Apr 2026. Private beta with consultancies, PE funds, independent
  advisors. White-label + subscription. "Raw business data → consulting-grade insights in under 10
  minutes" vs 1-3 weeks. Building a proposal-development + client-intelligence module.

### Others in the set
- **Foaster.ai** — YC P26 (Dabadie + Combes). Agents run 30-45 min interviews across a company →
  rebuild an "operational graph"; humans prioritise. Claims $500B target market.
- **Operand** — "Palantir for Strategy." Connect once to all enterprise data, agents learn
  continuously, analysis→action. Started with pricing/discount optimisation.
- **SignalPattern** (Inevitable, David Thomson) — 1,000+ specialised agents, 86+ signal engines,
  a *belief engine* (how evidence supports/contradicts hypotheses) and a *causal engine*
  (how changes propagate). Licensed by consulting firms under their own brand.
  Thesis: *"encoding the judgment into the system, not hiring more people to apply it."*
- **Emergence Capital "AI-Native Services" playbook** — you don't sell software, you own the outcome;
  50%+ gross margins vs 20% for legacy services. This is the funding thesis behind the whole cluster.

---

## 3. The free-diagnostic lead-magnet cluster (directly = OBS-SPEC-095's shape)

| Product | Shape | Notably |
|---|---|---|
| **ElevateOne / ElevateScore** | free outside-in business audit → score + benchmark + 3 prioritised actions + 30-day plan, <60s | pure funnel into a subscription |
| **BizHealth.ai** | 12-area health assessment, 9 report types | benchmarks against **McKinsey 7S, Balanced Scorecard, Lean/Six Sigma, EOS/Traction**; 90 min vs weeks; sells **white-label to consultants** |
| **Cashowa** | free website audit → financials → BRD, process maps, costed business case, auto-QBR every 90 days | 75 credits (~$15)/audit; **"every number is computed and inspectable"** |
| **gialyze** | "Free Business Review" | self-described "Truth-Seeking Business Diagnostic Engine" |
| **Sova** (AU) | 9 elements × 4 stages, maturity score | 350+ research findings, 400+ tools; free tier |
| **FoundersChecker** | idea → honest analysis <1 min | hard verdict: **Proceed / Pivot / Kill It** |
| IdeaAudit · preuve.ai · foundra.ai · ScribeAI | idea validators | "viability score out of 10", "60+ live sources" |
| CEO Scorecard · ExEss Growth Diagnostic | quiz → personalised report | classic lead magnet |

**None of them derives the competitive set.** They all benchmark against either (a) the owner's own
inputs, (b) a self-selected peer group, or (c) an industry bucket. `preuve.ai` claims "60+ live
sources"; none describes a **derived** Tier 1-7. That is the gap OBS-SPEC-095 is aimed at.

---

## 4. So how do they actually do it — the recurring mechanism

Across the serious players, seven moves repeat:

1. **Multi-agent decomposition by domain expertise** — 30 (Cortex) to 1,000+ (SignalPattern)
   specialist agents researching in parallel. Not one model, one prompt.
2. **A grounding layer that is not the LLM** — deterministic algorithms + paid/vetted data sources
   (Similarweb, Meta ad library, industry DBs, public financials, client internals). Xavier's DMG is
   the most explicit statement of this.
3. **Adversarial structuring to break sycophancy** — Cortex's Red Team vs Blue Team. This is the
   same instinct as our gate and falsification test, implemented as a product feature.
4. **A determinism claim** — "same question ten times → same answer" (Cortex). They know
   non-reproducibility is the objection and they answer it in marketing.
5. **Human-in-the-loop at 5-10%** — ex-consultant review as a quality and credibility layer.
6. **Output shaped as the artifact the buyer already accepts** — a deck (Xavier, Perceptis) or a PDF
   report (Rocket, ValueChaser). Never a chat answer.
7. **Provenance on every number** — traceable sources, stated as a feature (Xavier, Cortex, Cashowa).

**Business models, three distinct shapes:**
- sell *to* consultants (Perceptis, BizHealth white-label, ValueChaser) — higher ACV, no
  disintermediation
- self-serve bottom-up at $250/mo (Rocket) — volume, low touch
- free score → paid funnel (ElevateScore, gialyze, FoundersChecker) — exactly our model

---

## 5. Read for OBS-SPEC-095

**Good news on differentiation.** Every serious player claims determinism, provenance and
"no hallucinations." **None of them shows its work.** Not one publishes a flip rate, a distance-to-
boundary, an uncertainty interval, or a re-run comparison. They assert consistency; we can *measure*
it. That is the same conclusion reached in `FINDING-robustness-vs-gartner.md`, now confirmed against
the actual competitive set rather than against Gartner.

**The specific soft spot.** Rocket ships "McKinsey-grade" reports at $250/mo and TechCrunch
independently flagged the output as synthesised from existing data and not independently verifiable.
Xavier grounds in *internal documents* the client supplies. Cortex explicitly requires **no client
data at all** and only does competitive intelligence. **Nobody in this set reconstructs the
competitive set from the outside for a business that cannot describe its own market.** That is
precisely the thing we said only a derived Tier 1-7 can do.

**Two competitive facts to carry forward:**
1. The price anchor for a "McKinsey-grade" report in this market is **$250/month** (Rocket) or
   **$900/report** (ValueChaser), not $0. Our free report is generous, not market-rate — which
   argues for using it purely as a lead gate with an explicit paid next step.
2. **Xavier AI is the named competitor to watch.** Ex-McKinsey founder, INSEAD-authored launch
   article, a bank as early adopter, raising $15M, and a proprietary engine with a name (DMG).
   If the user saw "bain killer," this is almost certainly what he saw.

---

## 6. What this does NOT establish

- No evidence any of these actually *works* as claimed. Every mechanism claim above is vendor
  self-report or a friendly press write-up. The only independent test found is TechCrunch's, and
  its finding was negative.
- No revenue, retention or churn data for any of them except Rocket's self-reported ARPU.
- Unable to inspect Xavier's DMG, Cortex's Runtime Pipeline, or NexStrat's agentic architecture
  directly — they are closed. Everything about *how* is from founder statements.
- The exact app the user saw is still unidentified. The Xavier AI attribution is an inference from
  the descriptor + the founder's own public "McKinsey killer?" framing, not a confirmed sighting.
