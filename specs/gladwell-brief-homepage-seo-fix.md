# Gladwell brief — Homepage hero reads as SEO; needs spec-grounded rework

**From:** Spectrum (design) → **To:** Gladwell (copy)
**Route:** via Sean (you're not on the signal bus — this is your copy domain)
**Files:** `website/draft/index-v2.html` (my reframed mockup — react to the pixels), `specs/observeco-consulting-pivot-positioning.md` (the source of truth)

---

## The problem (why Sean flagged it)

The home page hero currently reads as an **SEO / lead-gen company**, not a differentiation-strategy consultancy:

> ❌ H1: "We find where your customers are, how to reach them, and the one way you can win."

That's the diagnosis presented as the product — exactly an SEO agency's promise. And the offer section's cost table compounds it with a literal **"SEO retainer 12 months"** line.

**Two framing errors to avoid (both are traps I already hit):**

1. **Don't lead with the diagnosis** ("where customers are / how to reach them") → reads as SEO / traffic / lead-gen.
2. **Don't collapse it to "the one sentence"** — that diminishes the under-the-hood competitor analysis that IS the product, and it contradicts your own position. Your spec (`observeco-consulting-pivot-positioning.md`) is explicit: *"Not even 'positioning analysis' — positioning is one lens; the customer's real question is 'there are so many ways to differentiate — which is best for MY business?'"* And the spec flags: SG buyers don't know the "positioning" vocabulary, so outward copy must speak in pains, not methods.

## The correct position to express (from the spec)

- ObserveCo owns the **"differentiation"** category — *the way to win, from your real competitors*.
- The deliverable is the **competitive analysis**: who you're really up against, what they've already claimed, the open slot, the differentiator recommendation + 90-day plan.
- The under-the-hood work (Module 1: Analyze Competition — competitive set, mind map, pricing landscape, adversarial verification) is the **moat** and the reason it's worth paying for. Don't hide it behind "a sentence."
- **No superlatives in outward copy** (spec rule): "best" is reserved for the market leader. Use "the differentiator that wins for *your* market," not "the best."

## The reframed structure (my v2 — yours to rewrite in voice)

**H1 (outcome + the work, differentiation-led):**
> "There's one way you can win. It's hiding in your competitors' blind spots — we find it and hand it to you."

**Sub** (names the work in SG-pain language, no SEO flavor):
> "Every competitor leaves an opening: a customer they ignore, a message they can't honestly claim. We study your real competitive set — who you're actually up against, what they've already claimed, where the open slot is — and deliver the one differentiator that wins for *your* market, with the 90-day road to claim it. The same analysis a big firm bills six figures for, in days."

**Three-step flow** (leads with the work, ends on the deliverable):

| Step | Now (SEO-flavored) | Reframed |
|---|---|---|
| 1 | Where your customers are | **Your real competitors** — who you're up against, mapped |
| 2 | How to reach them | **The opening** — the one slot they can't claim |
| 3 | The one way you can win | **Your differentiator** — the position + 90-day plan |

**Cost-table line** (remove the SEO keyword):
> ❌ "SEO retainer 12 months S$9.6–36K sunk"
> ✅ "marketing on a message that misses S$9.6–36K sunk"

## Deliverable I'm handing you

`website/draft/index-v2.html` — full page, same shell + design system, only these three blocks changed. All new copy is **flagged DRAFT COPY — Gladwell to finalize** inline. It's not live; `index.html` is untouched.

## What I need from you

1. Approve / revise the **H1 + sub** in your voice (mine is structural, not final).
2. Confirm the **three-step flow** labels land in SG-pain language.
3. Check the whole page for any residual "sentence"/"SEO" drift I missed (e.g. the education section still says "the one sentence that decides your revenue" — that's your call whether it stays).

Note: `website/draft/index-v2.html` has no `node --check`-clean inline script; the pre-existing nav-toggle script is what it is — flag to me if you want it cleaned.

---

## Addenda — verification pass (Main, 2026-08-22) — three misses in the above

1. **Meta description still carries the old H1 verbatim** (`index-v2.html` line 14): "We find where your customers are, how to reach them, and the one way you can win — from your real competitors, not guesswork." That is the SEO misread this brief exists to fix — and it's the copy Google renders first. Reframe it alongside the hero (outcome + the work, no diagnosis-first).

2. **The Services scale row still names SEO** (`index-v2.html` ~line 376): "website, SEO, ads." Defensible as a waste category in the cost-of-wrong section — but make the call explicitly: keep it as a named waste category, or swap to a neutral label (e.g. "website, ads, packaging"). Don't leave it to drift.

3. **The "one sentence" framing is on TWO pages**: `index.html#education` AND `differentiation-strategy.html` line 63 ("Why this matters: the one sentence that decides your revenue"). Your call on the sentence framing covers both pages — decide once, apply twice.

**Position on the sentence tension (Main's read, for your decision):** the case cards' before/after *are* positioning statements — that's the method's visible proof. The trap was the HERO collapsing the whole offer into a sentence, not the deliverable being a statement. Hero leads with the work; education uses the statement as the lever. Coherent funnel. Soften "sentence" → "positioning statement" (already used at line 64 of the education lead) rather than reworking the section.
