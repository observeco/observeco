# UX Issues Ledger

**Purpose:** batch-collect UX feedback so it's fixed in one pass, not one-at-a-time round-trips.

## How a batch works

1. **Dump** every UX issue below — free-form, loose phrasing is fine.
2. **I translate to fixture→output rows and SHOW YOU THE TABLE BEFORE ANY CODE.**
   You approve (or correct) the rows. This is the cheapest place to catch a
   misread — a batch wrong in forty places is worse than N round-trips, not better.
3. **Fix the approved batch.**
4. **Verify** — screenshots for VISUAL rows, click-through for BEHAVIOURAL rows.
   A screenshot can't prove a behavioural row (fold animation, empty-state copy,
   interaction feel) works; those need your hands on it.
5. **You review once**, per batch.

## Row types

Every row is marked **[V]** visual or **[B]** behavioural — they have different
verification and cost. Behavioural rows are NEVER declared done by a screenshot.

## Screenshot states (data density — NOT component lifecycle)

Screenshot at **N=0 / N=1 / N=max**. N=1 (healthy, boring, one agent) is the
state users see most and the one nobody draws — check it hardest. Loading/empty/
data is a different axis (single component lifecycle) and not what bit us.

## Columns

- **Status:** open → approved → fixed → deferred → **won't-fix**
- **won't-fix** exists because some dumped items are the mockup being wrong, not
  the build. "Actually the mockup's version is worse" has a home and stops the
  ledger becoming an obligation list.
- Deferred rows stay here; fixed rows move to `## Fixed` with the commit.

## Batch discipline

- Split visual rows and behavioural rows into separate passes. Visual rows are
  near-mechanical and verify fast; behavioural ones need real thought + click-through.
- A pass is done when every row is fixed or explicitly deferred/won't-fix.
- No new issue enters mid-pass — it waits for the next batch (prevents thrash).

---

## Open — Batch 1

<!-- Format: `- [V|B] [tab] issue — dump as loosely as you like` -->

## Fixed

<!-- `- [V|B] [tab] issue — fixed in <commit>` -->
