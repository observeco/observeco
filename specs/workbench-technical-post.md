# I built a personal benchmark, and the benchmarkable tasks didn't discriminate

**The one-sentence finding:** I built a system to turn my real agent sessions into
re-runnable benchmark tasks, and the tasks that were *benchmarkable* turned out
not to *discriminate* between the models I was actually choosing between. The
cheap model passed everything the expensive one did. The routing answer wrote
itself — and it wasn't the one I'd spent the effort to find.

This is a post about why that happened, the seventeen ways my measurement lied
to me before it was trustworthy, and the four things I correctly didn't build.
Every number is scoped to my workload and my sample sizes. I am not claiming a
law. I'm claiming a case study with its instruments attached.

---

## The setup

I work with Hermes, a personal coding agent. Every real session is captured
passively — tool calls, trajectories, full transcripts. I wanted to turn that
captured history into benchmark tasks: take a real session where the agent
successfully did something concrete, pin the repository to the state it started
from, replay it with a model, and check whether the model produced the same
artifact.

The pitch was the usual one: an empirical model card, a grid that routes each
task to the model that can actually do it, measured on real work instead of
README claims.

The reality: of roughly 16 sessions a week, **29% were objective enough to even
be candidates** (had a named deliverable and a write target). The honest funnel
chain is: **98 sessions → 42 with a write target → 29% objective → 8 drafts
emitted → 2 reviewable after manual triage.** And that narrowing was a precision
failure, not a strictness win — the 8 drafts were emitted by a buggy screen, and
only 2 were actually reviewable. Three of the 8 leaked through because the
source column lied (they were cron output, not user requests); two were an
entangled pair (the same commit state split across two sessions); one was
mislabeled. Fixing the screen's bugs shrank the *emitted* set — it did not grow
the reviewable one.

Those two denominators — 29% objective and 2 reviewable drafts — are the honest
ones. I state them first so nobody reads the results table without knowing how
thin the funnel was.

---

## The environment-lie taxonomy: seventeen ways the summary lied

The most useful thing in this project isn't the model comparison. It's the
taxonomy of how a measurement environment can lie while the summary looks fine.
Seventeen separate bugs were closed, every one found by reading the trajectory
rather than trusting the summary row. In every case where summary and trajectory
disagreed, the trajectory was right — but I only investigated cases that already
looked wrong, so this is a biased sample, not a base rate. Five families are
illustrated below; the other twelve were instances of the same class at other
layers.

The families:

- **The wrong-column bug.** A tool-result field was read from the wrong column.
- **The inherited-cwd bug.** The replay agent inherited the parent process's
  working directory instead of the pinned worktree, so it edited the real repo
  while the containment gate — auditing by a *different* session id — false-
  flagged every replay. Right data, wrong entity.
- **The wrong-subject bug (same family, one level down).** The containment
  gate audited the candidate session's history instead of the replay session's,
  because the session id wasn't captured and the fallback silently reused the
  candidate's. Fixed by refusing to audit what you can't identify: a missing id
  means *unmeasurable*, never *pass* and never *fail*.
- **The absent-vs-negative bug.** A missing replay-session field became a
  `FAIL` because "no evidence" was read as "negative evidence." Absence is not
  zero.
- **The drift-artifact bug.** A current-state comparison said the fix would
  false-fire 79% of the time — until we read the tool's source and found a
  successful patch *requires* a unique anchor, so every current-state "fire" on
  a successful patch was file-state drift since the patch. The true false-fire
  rate is ~0% by construction.

That last one is the whole project in miniature. A 79% false-fire rate would
have killed a good fix on bad evidence. It was caught the same way everything
was caught: by checking what actually happened against what was reported.

The through-line across all seventeen: **a measurement environment is something
you have to hold still while you take the picture.** The hard part was never the
comparison. It was making the world not move, and noticing every way it moved.

---

## The finding that costs something

Three tasks reached a clean k=3 under the model under test — a scorer addition,
a migration, a timezone refactor. (The path to those three wasn't tidy: the
migration candidate timed out, was adjudicated as a task-defect — its task text
referenced a spec that didn't exist — then was revised and re-run; and one
clean batch was discarded entirely when a containment bug invalidated its
verdicts. The three k=3s came together across several re-runs.)
Then I ran the weak baseline:

- an 8B local model passed all three, 3/3
- the cheap frontier model passed all three, 3/3, identically to the expensive
  one

The tasks did not discriminate between any two models I would actually route
between. Diagnosis was **B, not A** — and the way I told them apart is worth
showing, because it's the discipline in action. The plausible read was A: the
markers are too weak, satisfiable by a stub, so a weak model clears them. To
check, I read the code the 8B model actually wrote in the nine replays. It was
not stubs — a real `_semantic_similarity` assertion type with real weight
vectors and dispatch logic, a real `SCHEMA_VERSION = 63` migration with the three
tables defined, a genuine timezone utility module. An 8B model can add a method,
a migration, and a helper, because these are well-specified single-artifact
changes. That's what makes it **B**: the tasks are easy, not the markers weak.

The structural reason is uncomfortable:

> The properties that make a task benchmarkable — single artifact, well
> specified, pinnable, objective outcome — correlate with the properties that
> make it easy.

A selection screen optimized for scoreability selects below the discrimination
band. The subset of real work that is *benchmarkable* is not the subset that
*discriminates models*.

And yet this is not a null result. The routing question was answered anyway:
for this task class, **use the cheap model**. Equal accuracy at lower cost,
measured. The grid stayed empty and that emptiness was the answer. A grid that
discriminates nothing is a routing statement — the cheap model is on the
frontier and nothing is above it.

Scope: n=3 tasks, one workload, one model pair (frontier vs 8B, then frontier vs
cheap-frontier). The mechanism is structural; the numbers are n=3.

---

## The honest numbers, as measured

- **2 reviewable drafts** out of 8 emitted by a buggy screen (from 98 sessions → 42 write-target → 29% objective).
- **3 tasks** reached a clean k=3 (each a distinct shape: scorer, migration, tz refactor).
- **3/3 on each** under the weak 8B, the cheap frontier, and the expensive frontier model.
- **~20% base rate** of genuine struggle in screened-out sessions, hand-classified, n=20, CI ≈ 6–44%. The first base rate in the project that isn't disagreement-sampled.
- **12 failure sessions** produced **41 not-found episodes** backing the one edit I shipped — not 41 independent observations (two sessions accounted for 26 of the episodes; the concentration is the signal).

Each of those has a sample size attached. None is a law. They're measurements
of one workload, stated so a reader can see how thin each one is.

---

## The four things I correctly didn't build

The process's main output was prevented work:

1. **A uniqueness precheck for the patch tool** — read the tool's source, found it already fails loudly on non-unique anchors. Building it would have duplicated existing mechanism.
2. **A matcher-tolerance change** — would have traded silent failures for loud ones and corrupted files. Not built.
3. **Abandoning the fix on a drift artifact** — a 79% false-fire rate that turned out to be current-state noise. A good fix was nearly killed by a bad number.
4. **Replay infrastructure for a population that can't pin** — the failure class is exactly the non-pinnable working-copy population; the replay lab test was infeasible by design, and I found that before building it.

The one thing that did ship: a one-line change to the not-found error message
in the patch tool, making it actionable ("re-read the file and pass the exact
current text"). Backed by twelve real sessions. That's the whole deliverable.

---

## If you're building this, do these three things

The post is more useful if it ends on what transfers. Three concrete checks,
each of which cost me a real mistake when I skipped it:

1. **Run a weak baseline before you trust any benchmark you built.** The cheap
   model passing everything the expensive one does is not a failure of your
   models — it's the signal that your tasks don't discriminate. I spent
   twenty-plus rounds building an instrument and got the routing answer only
   when I ran an 8B against it. The weak baseline is the cheapest external
   validity check you have; run it first, not last.

2. **Check pinnability before you design a lab test.** A "replay with and
   without the fix" experiment assumes you can pin the starting state. The
   failure class that most needed testing turned out to be exactly the
   non-pinnable working-copy population — there was no starting SHA to replay
   from. Find that out before you build the replay harness, not after.

3. **Verify tool invariants at the source before you infer rates from
   behavior.** A 79% false-fire rate nearly killed a good fix. Reading the
   patch tool's source showed a successful patch *requires* a unique anchor —
   so every current-state "fire" on a successful patch was drift, and the true
   rate was ~0%. When a measured rate depends on how a tool behaves, read the
   tool's code; behavior is an assumption, source is a fact.

---

## The discipline, stated plainly

The thread's real claim isn't "we built less." It's:

> The discipline that makes a benchmark trustworthy — checking what actually
> happened, not what was reported — is the same discipline that stops you
> building the wrong thing.

Same technique, two wins. Seventeen times it caught a lying measurement. Four
times it stopped a wrong build. If you're building evaluation infrastructure,
the environment-lie taxonomy is the part worth taking — because your summaries
will lie too, and you'll need to read the trajectories to find out.

---

*Appendix: the repo, scripts, and decision logs this post is checkable against
are in the associated repository under `scripts/workbench/`. Every claim above
traces to a defect log entry, a run record, or a decision log with its reasons
recorded. Nothing here is an anecdote; it's a case study with its instruments
attached. Scoped to one workload. Yours will differ — that's the point of
publishing the method, not the number.*
