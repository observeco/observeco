# Coding Best Practices & Spec-Fidelity Playbook

**Product:** ObserveCo (and all future software projects)
**Version:** 3.12 — 2026-06-10 (UI Testing + Pipeline Learnings)

**Version History:**
| Version | Date | What changed |
|---------|------|-------------|
| 2.0 | 2026-05-30 | Initial tracked version — 5 Pillars, 16 bug patterns, SCOPE header, 100x Workflow, expert prompts, agent priming |
| 3.1 | 2026-05-31 | Standardization pass: all 7 playbooks bumped to v3.1. Fixed stale playbook-count references. Confirmed cross-references to Playbook Inventory (requirements-fidelity-playbook.md §Playbook Inventory) and Layer F First-Run Audit (master-fidelity-gate.md §2 Layer F). Removed stray empty FILE tags. |
| 2.1 | 2026-05-31 | Standardization pass: uniform versioning, cross-ref to Playbook Inventory, Golden Gate naming normalization |
| 3.11 | 2026-06-01 | Windows + Telemetry Hardening: added `_start_windows()`, `_windows_kill()`, signal handler guards, graceful degradation. Telemetry client now requires local opt-in file before sending. Three new dashboard endpoints for opt-in prompt. CI audit searches `<body>` content for F2/F9 keywords. Cross-platform matrix updated. |
| 3.12 | 2026-06-10 | Added Pattern 17 (Webhook State Transition Coverage), Pattern 18 (Encryption Key Integrity on Load), Pattern 19 (Payment URL Template Variables). Updated Golden Gate with payment-pipeline integration check. |

**Source:** Real coding sessions — all bugs traced back to spec-to-implementation gaps, inline-style over-reliance, missing verification layers, and graph visualization blind spots

---

## 1. Thesis

**The code must match the spec. The diff must match what the human expects.**

Every coding failure in this project traces to one root: the code passed compile-time checks but failed runtime expectations. The spec described 4-section modals; the code rendered 2 rows. The mockup showed colored dots with legend; the code showed raw emoji without context.

This document is not a style guide. It is a **coding process** — a repeatable way to catch the class of problem, not the instance.

---

## 2. The Five Coding-Fidelity Pillars

| Pillar | What it prevents | Core question |
|--------|-----------------|---------------|
| **Spec Grounding** | Building from memory, not from the spec | "Did I re-read the exact spec section before writing code?" |
| **Implementation Fidelity** | Section count mismatch, visual drift, graph node/edge misalignment | "Does every section the spec describes exist in the output? Do every DB column in the graph schema have a corresponding visual element?" |
| **Verification Autonomy** | False confidence from passing compile-only checks | "Did I run the automated spec-fidelity audit, or did I just trust it?" |
| **Agent Priming & Anti-Hallucination** | Hallucinated functions, wrong libraries, invented APIs, fake graph rendering APIs | "Did I prove every referenced function exists before calling it? Did I verify the graph library's actual API, not what I assumed?" |
| **Evolution & Regression Resilience** | Stale status markers, forgotten spec updates | "Does the master plan now show ✅ Live for what I built?" |

### 2.1 Spec Grounding

**Rule:** Before touching any file, read the relevant spec/mockup. If the feature is described with section-by-section detail, that's the contract.

**Force yourself:** Quote the exact spec paragraph you're implementing. Then enumerate every noun in that quote — each one should have a matching code element.

**Cross-reference mockups and spec:** When spec and mockup both describe a feature, the most detailed version wins. If the mockup shows a 4-section modal with pulse timeline, annotated timeline, summary, and latest check — those 4 sections must exist in the rendered modal. Not "similar" sections. The exact sections.

### 2.2 Implementation Fidelity

**The 4-Question Audit (every change):**
1. **Exists?** Does the element/section render in the DOM?
2. **Correct?** Does it show real data (not placeholders)?
3. **Complete?** Does it have ALL the sections the spec describes (not just some)?
4. **Matches mockup?** Does the structure/sections match the mockup's section layout?

**Verify spec language is "Built" not "Spec'd":**
The master plan uses these status markers:
- ✅ **Live** = exists and matches spec. Changes to this must preserve feature parity.
- 🟡 **Live (partial)** = exists but missing elements. Must be brought to full spec before considered done.
- 🔴 **Not built (mocked)** = only exists in mockup HTML, not in server code. Must be built from scratch.
- 🔴 **Planned** = spec only, no mockups yet.

### 2.3 Verification Autonomy

The agent must self-audit. Never trust "it compiles, it must be right."

**Self-audit protocol:**
1. Run TestClient spec-fidelity assertions — every section must render
2. Run f-string leak regex across all API responses
3. Run `py_compile` on all modified `.py` files
4. Run dependency grep (`pip list | grep`) before calling any external library
5. Only then: declare done for your part

**Two-agent verification (critic + implementer):**
After building, spawn a second agent whose only job is to run the spec-fidelity checks. Require consensus before marking done.

### 2.4 Agent Priming & Anti-Hallucination

**Before every coding session, load the priming files:**
- `AGENTS.md` / `CLAUDEMD` — exact style rules, forbidden patterns, must-use f-strings, CSS-first rule
- `spec-fidelity-checklist.md` — the 4-question audit as executable markdown
- `mockup-translation-template.md` — structured template for translating mockup to code

**Anti-hallucination rules (hard enforced):**
1. Every new function call must first be grepped in the codebase. If it doesn't exist, create stub + test first.
2. Every import or dependency reference must be verified with `pip list | grep` or `npm ls`.
3. No comment that says "your logic goes here" or "// TODO: implement" is allowed. If it's a stub, it must raise `NotImplementedError`.
4. When implementing, force output of SCOPE header before writing code.

### 2.5 Evolution & Regression Resilience

After every completed change:
1. Propose the exact markdown diff for `observeco-master-plan.md` in the same response as the code change
2. Update status marker from 🔴/🟡 → ✅ Live
3. Update deep-dive section: remove "see kanban tasks" language
4. If a gap was discovered: create `specs/experience-gaps-YYYY-MM-DD.md`

**Regression detection:** After any multi-file patch or any change that touches more than one file, run full `pytest` + TestClient suite.

---

## 3. The Coding Workflow

### 3.1 The 100x Workflow

```
1. PRIME agent with HOUND.md + exact spec quote + mockup link
2. FORCE agent to output SCOPE header + enumerated sections checklist
3. BUILD (one section at a time)
4. SELF-AUDIT (run TestClient + py_compile + DOM assert + f-string check)
5. HUMAN VISUAL GATE (you confirm screenshot matches mockup)
6. INDEPENDENT CRITIC AGENT reviews
7. UPDATE master plan + log gap if any
```

### 3.2 The Section Checklist Pattern

For any complex UI element (detail modal, card, panel, dashboard section), enumerate ALL states and verify each:

```python
# Example from _detail_health_tab audit
sections = [
    ("Pulse timeline", "48 coloured dots with legend"),
    ("Annotated timeline", "Time · Status · What happened table"),
    ("Categorized summary", "5-category classification + plain-English verdict"),
    ("Latest check", "Time · Result · Latency table"),
]
for name, description in sections:
    assert expected_content in response, f"Missing: {name}"
```

### 3.3 The Mockup Translation Pattern

When the mockup is a static HTML/JS file with hardcoded data:

1. Identify each **section** in the mockup (look for headings like `<h4>`, section dividers)
2. Identify each **data element** per section (tables, status indicators, summary text)
3. Check that the live API endpoint returns each data element, not just "similar" data
4. Check that the structure matches — same section order, same labels, same visual hierarchy

---

## 4. Known Bug Patterns (12+)

### 4.1 f-string leak (critical)

**Pattern:** `"""..."""` multi-line string without `f` prefix passes `py_compile` but leaks `{variable_name}` as literal text. This kills ALL onclick handlers in the affected HTML.

**Detection:**
```python
import re
fstring_leaks = re.findall(r'\{[a-z_][a-z0-9_]*\}', response_text)
if fstring_leaks:
    print(f"FSTRING LEAK: {len(fstring_leaks)} occurrences of {set(fstring_leaks)}")
```

**Fix:** Always use `f"""..."""` for HTML-generating strings. Never use `"""..."""` for content with placeholders.

**Prevention:** Add f-string leak detection to every API endpoint's test output.

### 4.2 document.write() DOM nuke (critical)

**Pattern:** `document.write('<script src="...">')` called after page finishes parsing destroys the entire DOM and replaces it with just the script tag. Common in htmx CDN fallback patterns.

**Fix:** Replace with:
```javascript
if (!window.htmx) {
    var s = document.createElement('script');
    s.src = 'https://unpkg.com/htmx.org@1.9.11/dist/htmx.min.js';
    document.head.appendChild(s);
}
```

### 4.3 Spec-to-implementation gap (critical)

**Pattern:** Spec describes 4 sections, code implements 2. The 2 that exist work perfectly. The human is still disappointed because they read the spec and expected 4.

**Root cause:** Code was written from memory of the spec, not by re-reading the spec. "I know what this does" is dangerous when building from a detailed specification.

**Prevention:** Re-read the spec section before implementing. Check off every subsection. If the spec says "The Health modal has 4 sections" and you're implementing Health, your code must have 4 identifiable sections.

### 4.4 Framework label hardcoding

**Pattern:** `"Hermes" if framework == "hermes" else "OpenClaw"` — only handles 2 framework values. A LangChain user's agent displays as "OpenClaw" (wrong).

**Fix:** Always use `capitalize()` on the actual DB value. Default to empty string, not "Hermes".

### 4.5 Empty state omission

**Pattern:** Data section renders with zero records but no explanation. The DOM is correct (empty list). The experience is broken ("why is this blank?").

**Every data section must answer:** WHY it's empty, WHEN it will populate, and WHAT to do if it doesn't.

### 4.6 Stale status contradiction

**Pattern:** 🟢 "Running" status dot next to "5d ago" timestamp. These come from different queries — pulse status vs last pulse timestamp. They can disagree when pulses are stale.

**Fix:** Derive status and timestamp from the same query. Or append "(stale)" when the timestamp exceeds a threshold.

### 4.7 Unicode corruption in batch edits

**Pattern:** Regex-based find-and-replace across source files can corrupt multi-byte Unicode characters (emoji, special quotes) inside f-strings, causing `SyntaxError: invalid character` at runtime.

**Prevention:** After any batch find-and-replace on source files, always run `python3 -m py_compile` AND start the server. py_compile catches syntax errors; server start catches runtime errors.

### 4.8 git revert loses uncommitted fixes

**Pattern:** A `git checkout -- file` revert intended to undo a broken change also erases all uncommitted functional fixes in that file.

**Prevention:** Atomic fix scripts (one Python file per fix scope) survive git revert. Run them again after any revert.

### 4.9 Spec misinterpretation (2026 agent killer #1)

**Pattern:** Agent reads "same characters" and implements anagram instead of set equality. Or implements 2 sections when spec says 4. The agent's semantic understanding of the spec text diverges from the author's intent.

**Detection:** Force agent to quote the exact spec sentence it is implementing, then assert every noun in the sentence has a matching code element.

**Fix:** Require SCOPE header in every task (Structure, Constraints, Outcomes, Priming Rules, Edge Cases):

```
SCOPE:
Structure: [list sections in order]
Constraints: [list constraints — exact counts, exact labels]
Outcomes: [what must render for this to be done]
Priming Rules: [exact spec quote being implemented]
Edge Cases: [empty state, error state, loading state]
```

### 4.10 Hallucinated objects / non-existent functions

**Pattern:** Agent calls `agent.get_trim_data()` that never existed. The LLM invented the function name.

**Prevention:** Every new function call must first be grepped in the codebase. If not found, the agent must create a stub + test BEFORE writing the calling code.

**Detection in review:** Scan for any function call that is not resolvable via `codegraph_search` or `grep -r`.

### 4.11 Visual-to-code drift (your exact dashboard pain)

**Pattern:** Mockup has 48 colored dots with legend; code renders `<div class="dots">` with no legend and wrong count. The mockup and code describe the same feature at different fidelity levels.

**Remedy:** Before marking done, the agent must output a DOM snapshot of each section + side-by-side diff against mockup HTML structure.

### 4.12 False-negative verification

**Pattern:** LLM says "this correct code is wrong" and rewrites working logic, OR misses its own mistakes because it doesn't re-check after changes.

**Fix:** Run two independent verifier agents (one "Critic", one "Implementer") and require consensus. The critic does NOT see the builder's code — it only has the spec and mockup, and must list what sections should exist. The implementer then checks those against the actual code.

### 4.20 Payment pipeline — success ≠ done (3 sub-states)

**Pattern:** Payment flow completes at Stripe level but Pro is not activated. Three independent failure points: wrong session ID (Stripe Checkout session not matched to user), encryption key mismatch (key stored in one format, decrypted in another), missing start_trial() call (payment success handler doesn't trigger trial activation).

**Prevention:** Payment pipeline spec must enumerate all 3 sub-states: (1) Stripe Checkout session creation + ID mapping, (2) encryption key generation + storage + retrieval, (3) trial/Pro activation call. Each sub-state must have its own test.

### 4.21 Cross-tab DOM access without null guard

**Pattern:** A JS function like `loadLicenseStatus()` works on the Settings tab where the DOM element exists, but crashes silently on 4 other tabs where the element is null. The crash is silent because it happens in a callback or async context with no error handler.

**Prevention:** Every cross-tab JS function must null-guard every DOM access. Pattern: `const el = document.getElementById('x'); if (!el) return;`. Add to code review checklist.

### 4.22 Badge/state refresh missing after state change

**Pattern:** License deactivation updates the backend, but the UI badge still shows the old state until manual page reload. The state change handler updates the data model but doesn't trigger a UI refresh.

**Prevention:** Every state-changing operation (modal close, form submit, deactivation) must call the relevant refresh function. Add to PR checklist: "Does this state change trigger a UI refresh?"

**Pattern:** Agent suggests `pip install mcp>=1.0` when `mcp` doesn't exist on PyPI yet, or calls `pandas.DataFrame.merge` with parameters from a newer version than installed.

**Prevention:** Before every patch that introduces a new dependency:
```bash
pip list | grep <package>  # or npm ls <package>
# If not found: propose the exact version, verify it exists, pin it
```

**Detection in review:** Every new import must have a corresponding entry in `pyproject.toml` or be verified as already installed.

### 4.14 Over-defensive / lazy boilerplate

**Pattern:** Agent adds 17 guard clauses to fix a simple issue, or leaves `# TODO: implement logic` markers that defer the actual work.

**Rule:** No comment that says "your logic goes here" or equivalent is allowed. If the code is a stub, it must raise `NotImplementedError`. Guard clauses that check for conditions that can never fail under the current architecture must be removed.

### 4.15 Context break in multi-file edits

**Pattern:** Agent fixes one file but breaks an import in another. Or changes a function signature but misses 2 of 3 call sites.

**Prevention:** After any multi-file patch:
```bash
pytest  # unit tests
# AND
browser full-page reload + screenshot of every interactive element
# AND
check all call sites of the modified function
```

### 4.16 Master plan status drift

**Pattern:** Human (or agent) forgets to update `observeco-master-plan.md` after a feature is built → feature row stays 🔴 forever → next human reads the plan and thinks the feature doesn't exist.

**Automation:** Agent must propose the exact markdown diff for the master plan status line in the same response as the code change. If the diff is not proposed, the task is not complete.

### 4.17 Webhook State Transition Coverage

**Pattern:** A webhook handler records an event (Stripe payment received, customer created) but never propagates the state change to the downstream system (license activation, feature unlock). The handler was built against "record the event" not "activate the downstream effect."

**Real example (ObserveCo, 2026-06-09):** Stripe `checkout.session.completed` webhook recorded the customer in the CRM but never called `start_trial()`. Payment succeeded. Pro never activated. Three independent bugs in the same pipeline.

**Detection:**
1. Every webhook handler must have a **state transition map**: event received → what changes → what propagates → what follows
2. If a webhook stores data but doesn't trigger a downstream effect, it's half-implemented
3. After the webhook fires, verify: did the downstream state actually change? (not "did it call the function" but "did the license switch to Pro?")

**Prevention:** Add a post-webhook audit step: after every checkout.session.completed, re-read the license state and compare to expected. If they don't match, flag for manual review.

### 4.18 Encryption Key / Config File Integrity on Load

**Pattern:** A critical config file (encryption key, API token, database URL) is corrupted, truncated, or duplicated. The load function silently falls back to a degraded mode (simulated Stripe, local-only mode) instead of failing loud. The degraded mode is never tested — the app works differently in production than in dev without anyone noticing.

**Real example (ObserveCo, 2026-06-09):** Fernet key file had two concatenated keys. `load_key()` silently fell back to simulation mode. Stripe payments appeared to work but never actually charged — every transaction was in simulation mode. The difference was invisible unless you checked the Stripe Dashboard.

**Detection:**
- Any critical config file must have integrity validation on load (expected length, expected format, checksum)
- If decryption fails, log the failure AND prevent the degraded mode from silently activating
- Prefer failing loud (error message, blocked startup) over silent degradation for security-critical config
- Test: corrupt the config file. Does the app fail informatively or silently switch modes?

### 4.19 Payment URL Template Variables

**Pattern:** A payment checkout URL is constructed without required template variables. The checkout works in development (Stripe allows test sessions without certain parameters) but fails in production, or the webhook can't correlate the session back to the user.

**Real example (ObserveCo, 2026-06-09):** Stripe `success_url` was missing `{CHECKOUT_SESSION_ID}` template variable. Stripe allows this in test mode — sessions are created, payments complete, but the webhook has no way to map the successful payment back to the original session. Three users paid and never got Pro.

**Detection:**
- For any payment/checkout integration, verify the success_url includes ALL required session identifier template variables
- Check the payment platform docs for: required URL parameters, optional-but-recommended parameters, and environment-specific parameters
- Test in production-like mode (not just test mode — Stripe test mode accepts URLs that production rejects)

---

## 5. The Fidelity Verification Pattern

### 5.1 TestClient-based spec fidelity check

```python
from fastapi.testclient import TestClient
from app import app
import re

client = TestClient(app)
r = client.get('/api/agent-detail/kepler?tab=health')

spec_sections = [
    ('Pulse timeline', 'Last 24 hours' in r.text or 'pulse-timeline' in r.text),
    ('Annotated timeline', 'What happened' in r.text and 'Time' in r.text and 'Status' in r.text),
    ('Summary with verdict', 'Summary' in r.text and 'Verdict' in r.text),
    ('Latest check', 'Latest check' in r.text and 'Latency' in r.text),
]

for name, exists in spec_sections:
    assert exists, f"SPEC FIDELITY FAIL: {name} section missing from Health tab"
```

---

## 6. Pathway Map Architecture — The Graph Visualization Fidelity Layer

**This section is the single most important addition to this playbook.** Pathway maps (directed graphs) are fundamentally different from dashboard cards, lists, modals, and tables. They have failure modes that don't exist in any other UI type:

1. **Data integrity failures** — edges with no valid source/target render as broken arrows
2. **Layout failures** — the graph may render but nodes overlap, edges cross, or the layout is unreadable
3. **Graph library API hallucinations** — Cytoscape.js has a specific, well-documented API. LLMs routinely invent function names that don't exist
4. **Dead-end semantics** — dangling edges without terminal consumers are the most common failure point and the hardest to verify automatically
5. **Filtering destroys connectivity** — showing "green only" hides so many nodes the graph becomes disconnected fragments
6. **Performance at scale** — 50+ nodes with animation and layout re-run causes visible jank

### 6.1 The Graph Data Integrity Checklist

Before rendering a single pixel, verify the data:

```
┌─────────────────────────────────────────────────────────┐
│ GRAPH DATA INTEGRITY CHECK                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Node checks:                                             │
│  [ ] Every node has a unique `id`                        │
│  [ ] Every node has a `type` (agent/cron/platform/etc)   │
│  [ ] Every node has a human-readable `name` or `label`   │
│  [ ] No duplicate IDs (SQL: SELECT COUNT(*) vs DISTINCT) │
│  [ ] Dead-end stub nodes generated per edge, not shared  │
│                                                          │
│ Edge checks:                                             │
│  [ ] Every edge has a valid `source_id` in nodes         │
│  [ ] Every edge has a valid `target_id` OR is dead-end   │
│  [ ] No duplicate edges (same source+target combo)       │
│  [ ] Every edge has a `status` (green/yellow/red/teal)   │
│  [ ] Every edge has a `mechanism` or sensible default    │
│                                                          │
│ Graph-level checks:                                      │
│  [ ] Every node has at least 1 connection (no orphans)   │
│  [ ] Dead-end ratio computed: red_edges / total_edges    │
│  [ ] No infinite cycles (run depth-limited path check)   │
│                                                          │
│ Pass criteria: all checks pass                            │
└─────────────────────────────────────────────────────────┘
```

**SQL verification pattern (run against your pathway DB):**

```sql
-- Orphan nodes (no connections whatsoever)
SELECT n.id FROM pathway_nodes n
LEFT JOIN pathway_edges e ON n.id = e.source_id OR n.id = e.target_id
WHERE e.id IS NULL;

-- Edges with missing source or target
SELECT * FROM pathway_edges
WHERE source_id NOT IN (SELECT id FROM pathway_nodes)
   OR (target_id IS NOT NULL AND target_id NOT IN (SELECT id FROM pathway_nodes));

-- Duplicate edges
SELECT source_id, target_id, COUNT(*) as cnt
FROM pathway_edges
WHERE target_id IS NOT NULL
GROUP BY source_id, target_id
HAVING cnt > 1;
```

**Automated verification script (run after every DB change):**

```python
def verify_pathway_data(conn):
    """Returns list of integrity issues."""
    issues = []
    
    # Orphan nodes
    orphans = conn.execute("""
        SELECT n.id FROM pathway_nodes n
        LEFT JOIN pathway_edges e ON n.id = e.source_id OR n.id = e.target_id
        WHERE e.id IS NULL
    """).fetchall()
    for row in orphans:
        issues.append(f"Orphan node: {row['id']} has no connections")
    
    # Edges without source/target
    bad_edges = conn.execute("""
        SELECT e.id, e.source_id, e.target_id FROM pathway_edges e
        WHERE e.source_id NOT IN (SELECT id FROM pathway_nodes)
           OR (e.target_id IS NOT NULL AND e.target_id NOT IN (SELECT id FROM pathway_nodes))
    """).fetchall()
    for row in bad_edges:
        issues.append(f"Edge {row['id']}: source '{row['source_id']}' or target '{row['target_id']}' missing")
    
    return issues
```

### 6.2 The Cytoscape.js API Fidelity Checklist

**Cytoscape.js is the most hallucinated library in this codebase.** LLMs commonly invent:
- `cy.layout({ name: 'dagre' })` — actual API, `cytoscape-dagre` plugin required
- `cy.style().selector('node').style({...})` — actual API for programmatic styling
- `cy.add([{ group: 'nodes', data: {...} }])` — actual API for adding elements
- **Fake:** `cytoscape.use(require('cytoscape-dagre'))` — require() doesn't work in browser CDN
- **Fake:** `cy.fit()` without arguments — `.fit()` works but only after elements are added
- **Fake:** `cy.zoom(1.5)` — actual is `cy.zoom()(1.5)` (getter/setter pattern)
- **Fake:** `node.data('raw')` — actual `node.data('raw')` only works if `raw` was set in element data

**Before any Cytoscape.js coding:**

1. Load `node_modules/cytoscape/dist/cytoscape.min.js` and check the actual API
2. Check which plugins are loaded (dagre, cose-bilkent, etc.)
3. Verify every Cytoscape function call against the actual library docs
4. Test the code in a browser console before committing

**The 10-point Cytoscape verification gate:**

```
┌─────────────────────────────────────────────────────────┐
│ CYTOSCAPE.JS FIDELITY GATE                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ 1. [ ] Library loads without CDN errors                 │
│ 2. [ ] `cytoscape()` constructor receives valid options  │
│ 3. [ ] All `style` selectors match actual element groups │
│ 4. [ ] Layout name is valid for loaded plugins          │
│ 5. [ ] Event handlers bound to correct selectors         │
│      (`cy.on('tap', 'node', fn)` = click node)          │
│ 6. [ ] No `require()` calls in browser code              │
│ 7. [ ] `cy.destroy()` called before re-initialization   │
│ 8. [ ] DOM container exists before `cytoscape()` call    │
│ 9. [ ] Filter toggle restores layout (not just display)  │
│ 10. [ ] Error boundary wraps initialization              │
│                                                          │
│ Pass: 10/10                                              │
└─────────────────────────────────────────────────────────┘
```

### 6.3 The Dead-End Rendering Pattern

Dead ends are the **most visually delicate** element in the pathway map. They represent an edge that has no terminal consumer. How they render determines whether the user understands the problem at a glance or is confused.

**Rendering approaches (ranked):**

| Approach | What it shows | When to use | 
|----------|--------------|-------------|
| **Invisible stub node + red dashed edge** | Full edge to a small red ∅ node | Default — preserves dagre layout, shows where the gap is |
| **Red dashed edge with no end node** | Arrow just stops mid-air | Only with force-directed layout; confusing in ranked layout |
| **Red edge to a legend-referenced icon** | Edge ends at a cross-mark icon | Acceptable for small graphs (<20 nodes) |
| **Edge highlighted on hover, dead-end marker in detail panel** | Normal arrow until clicked | Only if graph is otherwise unreadable with stub nodes |

**Critical rule: DO NOT use the same stub node ID for multiple dead ends.** Each dead end MUST have its own stub node. If you reuse a single `__dead__` node, Cytoscape collapses all dead-end edges into one target node, making it impossible to click individual dead-end paths.

**Correct implementation:**
```javascript
function createDeadEndStub(sourceId, edgeIndex) {
    const stubId = `__dead__${sourceId}_${edgeIndex}`;
    // Each stub gets a unique ID so edges don't collapse
    return {
        group: 'nodes',
        data: { 
            id: stubId, label: '∅', type: 'dead-end',
            nodeColor: '#ef4444', shape: 'ellipse',
        },
        classes: 'dead-end-node'
    };
}
```

### 6.4 Layout Strategy (Dagre vs Cose vs Manual)

**Dagre** (directed acyclic graph layout) — the correct choice for pathway maps:
- Renders left-to-right, sources on left, targets on right
- Minimizes edge crossings → readable
- Supports `rankDir: 'LR'` and `rankSep` tuning
- Re-runs on every filter change → animation is essential
- **Limitation:** Cannot handle cycles well; if nodes form a loop, dagre makes arbitrary decisions

**Cose** (force-directed — compound spring embedder):
- Organic layout — no inherent direction
- Nodes cluster by connectivity
- Good for exploration but poor for "which way does data flow" pathway maps
- **Do NOT use** for communication pathway maps

**Manual positioning:**
- Only when the graph has fixed topology (same nodes, same positions every time)
- For dynamic pathway maps (nodes added/removed), always use dagre

**Layout refresh rule:**
```javascript
// After any filter or data change:
cy.layout({ 
    name: 'dagre', 
    rankDir: 'LR', 
    animate: true, 
    animationDuration: 300,
    fit: true  // IMPORTANT: zoom to fit the new layout
}).run();
```

### 6.5 Filtering Correctness — The Hidden Pitfall

Filtering a graph by status (show only green edges, show only red edges) is **not** the same as filtering a table. In a table, removing rows just shows fewer rows. In a graph, removing nodes and edges can:

1. Create disconnected fragments (orphan nodes with no visible connections)
2. Destroy the layout (remaining nodes rearrange to fill gaps, losing mental map)
3. Confuse the user ("why is this node here but none of its connections are?")

**Filtering rules:**

| Problem | Solution |
|---------|----------|
| Orphan nodes after filter | Hide any node with zero visible connected edges |
| Dead ends shown when filtering green | Hide dead-end nodes in any non-red filter |
| Layout jumps confuse user | Animate layout transitions (≥200ms) |
| User loses sense of position | Show "N of M edges visible" in filter toolbar |

**Anti-pattern — hiding nodes without hiding their connections:**
```javascript
// WRONG — node hidden but its edges still visible
n.style('display', 'none');
// Edges pointing to hidden node are now floating lines

// CORRECT — hide both or none
if (hasVisibleEdges) {
    n.style('display', 'element');
} else {
    n.style('display', 'none');
}
```

**The filter toolbar should always show the count of visible elements:**
```
Filter: [All] [🟢 Complete (35)] [🟡 Concerns (3)] [🔴 Dead Ends (18)]
Showing 56 of 58 elements
```

### 6.6 Detail Panel Data Flow — The Four-Wire Pattern

The detail panel (click a node → see details) has four distinct data flows that must each work:

```
┌──────────────────────────────────────────────────────────────┐
│ DETAIL PANEL DATA FLOW VERIFICATION                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ Wire 1: Tap event fires                                       │
│   cy.on('tap', 'node', fn) → fn called?                      │
│   Check: console.log('tap fired') in event handler            │
│                                                               │
│ Wire 2: Node data extracted                                   │
│   node.data('id'), node.data('label'), node.data('raw')       │
│   Check: detail body shows node name + type                   │
│                                                               │
│ Wire 3: Detail HTML rendered                                  │
│   panel.innerHTML = buildNodeDetail(node)                     │
│   Check: detail-row elements count > 0                        │
│                                                               │
│ Wire 4: Connections enumerated                                │
│   node.connectedEdges().forEach(...)                          │
│   Check: connection count matches real edge count in DB       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Verification script for detail panel:**
```javascript
// Run in browser console after clicking a node
console.log('Node data:', cy.$(':selected').data());
console.log('Connected edges:', cy.$(':selected').connectedEdges().length);
console.log('Detail rows:', document.querySelectorAll('.detail-row').length);
console.log('Connection rows:', document.querySelectorAll('.detail-row').length - 4);
// Connection count should match edge count
```

### 6.7 Performance Budget for Pathway Maps

| Operation | Budget | Exceeded at | Remediation |
|-----------|--------|-------------|-------------|
| Initial render (fetch + layout) | < 1.5s | > 3s | Paginate nodes, use `compound` nodes for clusters |
| Filter animation | < 300ms | > 1s | Reduce `animationDuration`, skip layout re-run for large graphs |
| Node click → detail panel | < 100ms | > 500ms | Pre-compute detail data, render from node's raw data |
| Pan/zoom (per frame) | < 16ms | > 50ms | Reduce node count, use `minZoom`/`maxZoom` bounds |
| Hover highlight | < 50ms | > 200ms | Use CSS `:hover` instead of JavaScript event handlers |

**Performance testing block:**
```javascript
// Benchmark initial render
const t0 = performance.now();
await fetchGraph();
initializeCy();
console.log(`Graph render: ${performance.now() - t0}ms`);

// Benchmark filter
const t1 = performance.now();
setFilter('green', document.querySelector('[data-filter=green]'));
setTimeout(() => console.log(`Filter animation: ${performance.now() - t1}ms`), 400);
```

### 6.8 The Full Pathway Map Fidelity Gate

```
┌──────────────────────────────────────────────────────────────────┐
│ PATHWAY MAP FIDELITY GATE                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│ DATA INTEGRITY                                                    │
│  [ ] DB query: 0 orphan nodes, 0 bad edges, 0 duplicates         │
│  [ ] Graph-level: every node has ≥1 connection                    │
│  [ ] Dead-end stubs: unique IDs per dead end (not shared)        │
│                                                                   │
│ LIBRARY FIDELITY                                                  │
│  [ ] All 10 Cytoscape.js gate checks pass                        │
│  [ ] No hallucinated API calls (verify against actual docs)       │
│  [ ] cy.destroy() called before re-init on refresh               │
│                                                                   │
│ LAYOUT & VISUAL                                                   │
│  [ ] Initial layout: dagre LR, fit to viewport, no overlap       │
│  [ ] Filter: all 4 options work, no orphan nodes, animated       │
│  [ ] Legend: every node type in legend has visible match         │
│  [ ] Every edge status (green/yellow/red) has legend entry       │
│  [ ] No edge renders as a bare line with no target               │
│  [ ] Dead-end edges end at a visible red marker                  │
│                                                                   │
│ DETAIL PANEL                                                      │
│  [ ] Tap node → detail panel updates with correct data           │
│  [ ] Tap edge → detail shows source + target + mechanism         │
│  [ ] Tap background → detail resets to empty state               │
│  [ ] Connected edges count matches real edge count in DB         │
│  [ ] Detail panel click edge reference → highlight in graph      │
│                                                                   │
│ PERFORMANCE                                                       │
│  [ ] Initial render < 1.5s                                        │
│  [ ] Filter animation < 300ms                                     │
│  [ ] Node click → detail < 100ms                                  │
│  [ ] Pan/zoom: no jank at 50+ nodes                              │
│                                                                   │
│ PASS/FAIL: ___/20 (≥18 = pass, <18 = do not ship)                 │
└──────────────────────────────────────────────────────────────────┘
```

## 7. Coding Conventions

### 7.1 One function per modal/panel
Each drill-down or detail panel gets its own function. Do not inline. This makes it possible to test each section independently and diff between spec and implementation.

### 7.2 No placeholder onclick
Every clickable element must call a real backend endpoint. Never use `onclick="openModal(title, subtitle, 'Loading...')"` with static text. Always use `onclick="loadTab(name, tab)"` which fetches live data.

### 7.3 CSS classes over inline styles
- Static styling → CSS classes in `<style>` block
- Dynamic values (colors, widths that change per agent/status) → inline `style=` attributes
- Exception: utility classes for common patterns (glass surface, hover states)

### 7.4 One recommendation per question
In code reviews and implementation decisions: propose one path, not a menu. The same rule applies to UX — one recommendation, not options.

### 7.5 Commit messages capture WHY
Every commit message should answer: "What did the spec say? What did the code deliver? What was the gap?" This makes it possible to trace spec-to-implementation drift over time.

---

## 8. Spec Update Protocol

When a feature is built according to spec:
1. Update `observeco-master-plan.md` status from `🔴 Not built` / `🟡 Partial` → `✅ Live`
2. Update the feature matrix row (feature number, title, category, status, free/pro, effort, spec reference)
3. Update the feature deep-dive section: remove "see kanban tasks" language, replace with "Built" and actual section descriptions

When a feature DISCOVERS a gap between spec and implementation:
1. Create `specs/experience-gaps-YYYY-MM-DD.md` with before/after table
2. Update `experience-gaps-template.md` with the new gap in the appropriate category
3. Fix the code to match the spec
4. Verify with automated spec-fidelity test

---

## 9. The Golden Gate — Coding Fidelity Gate

Before marking any coding task done:

```
┌─────────────────────────────────────────────────────┐
│ CODING FIDELITY GATE                                │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Pillar 1: Spec Grounding                            │
│  [ ] Spec section re-read and checked off           │
│  [ ] Mockup cross-referenced for structure          │
│  [ ] Exact spec quote output + noun matching        │
│                                                      │
│ Pillar 2: Implementation Fidelity                   │
│  [ ] All states rendered (loading, empty, data, err)│
│  [ ] Every clickable wired to live backend          │
│  [ ] Section count matches spec (no missing/extra)  │
│  [ ] Graph spatial audit (if graph viz): >60%       │
│      viewport utilized, no node overlap, all labels │
│      readable at default zoom                       │
│                                                      │
│ Pillar 3: Verification Autonomy                     │
│  [ ] TestClient spec-fidelity assertions pass       │
│  [ ] f-string leak: zero hits                       │
│  [ ] No hardcoded framework labels                  │
│  [ ] py_compile + server start both pass            │
│  [ ] Two-agent critic check completed               │
│                                                      │
│ Pillar 4: Anti-Hallucination                        │
│  [ ] Every new function call verified (grep)        │
│  [ ] Every new dependency verified (pip list)       │
│  [ ] No "TODO: implement" or lazy boilerplate       │
│  [ ] Multi-file import chain verified               │
│                                                      │
│ Pillar 5: Evolution & Regression                    │
│  [ ] Master plan status updated to ✅ Live          │
│  [ ] Master plan diff proposed with code change     │
│  [ ] Deep-dive section updated (no "kanban tasks")  │
│  [ ] Gap doc created if spec→code divergence found  │
│  [ ] Full pytest + TestClient suite after multi-file│
│                                                      │
│ PASS/FAIL: ___/23 (≥21 = pass, <21 = do not ship)   │
└─────────────────────────────────────────────────────┘
```

---

## 10. Agent Priming Files

Before every coding session, the following files must be loaded:

| File | Purpose |
|------|---------|
| `spec-fidelity-checklist.md` | The 4-question audit + 22-item Golden Gate as executable markdown |
| `mockup-translation-template.md` | Structured template: spec quote → section list → code → verify |
| `AGENTS.md` / `CLAUDE.md` | Exact style rules, forbidden patterns, must-use f-strings, CSS-first rule |

### 10.1 SCOPE Header (Required Before Every Implementation)

Before writing code, force output of:

```
SCOPE:
Structure: [list sections in order — must match spec exactly]
Constraints: [exact counts, exact labels, exact visual elements]
Outcomes: [what must render for this to be done]
Priming Rules: (exact spec quote being implemented — paste the paragraph)
Edge Cases: [empty state, error state, loading state — per section]
```

---

## 11. The 100x Workflow (Replaces 3.1)

```
1. PRIME agent with HOUND.md + exact spec quote + mockup link
2. FORCE agent to output SCOPE header + enumerated sections checklist
3. BUILD (one section at a time)
4. SELF-AUDIT (run TestClient + py_compile + DOM assert + f-string check)
5. HUMAN VISUAL GATE (you confirm screenshot matches mockup)
6. INDEPENDENT CRITIC AGENT reviews
7. UPDATE master plan + log gap if any
```

---

## 12. Expert Prompts for Agent

### Prompt A: Spec Fidelity + Mockup Translation (run before any coding)

```
You are now in 100x Spec-Fidelity Mode.
Task: [describe ticket]

1. Quote the exact paragraph from the spec and the exact section numbers from the mockup HTML.
2. Enumerate every single element/section the spec+mockup require (use bullet list).
3. Output the full SCOPE header (Structure, Constraints, Outcomes, Priming Rules, Edge Cases).
4. Propose changes ONE SECTION AT A TIME. After each, run TestClient audit + Playwright screenshot
   of that section only. Show me the before/after DOM and screenshot.
5. Do not mark complete until I reply "VISUAL MATCH CONFIRMED".

Start now with step 1.
```

### Prompt B: Golden Gate (run autonomously after build)

```
Run the complete Coding Fidelity Gate on the current changes:

1. Spec re-read + checklist of every required section
2. f-string leak check + dependency grep
3. TestClient spec-fidelity assertions (all must pass)
4. Playwright: hard-reload + screenshot every interactive element + assert visible change <200ms
5. Mockup side-by-side diff
6. Master plan status update proposal

Output: ✅ PASS / ❌ FAIL per item + screenshots + one-line fixes for any FAIL.

Only if all PASS may you say "Ready for human visual confirmation."
```

---

## 13. Lessons Learned Log

### 2026-05-30 — Playbook v1 Self-Review

| What was wrong | Category | Fix applied |
|----------------|----------|-------------|
| Duplicate empty `` tag at end of file | Self-inflicted bug (same as UX playbook had in its v1) | Removed — this is the "physician heal thyself" problem. Both playbooks now checked for stray tags before save. |
| Section 4 titled "Known Bug Patterns" with no intro paragraph — jumped directly to 4.1 | Numbering consistency | Added intro paragraph. All sections now have consistent numbering style. |
| Golden Checklist had 10 items as flat checkboxes — no visual progress bar, no pass/fail format | Format consistency | Converted to bordered table with 22-item scorecard organized by pillar, with PASS/FAIL threshold and score display. |
| No "Self-Review" entry in Lessons Log | Completeness | Added this entry. Both playbooks (UX + Coding) now have self-review sections that are updated on every major revision. |
| Only 3 pillars hidden in flat text — no explicit 5-pillar framework | Architecture completeness | Added explicit §2 with 5 Coding-Fidelity Pillars table. Mirrors UX playbook's 5-layer structure for symmetry. |
| Only 8 bug patterns | Coverage | Expanded to 16 patterns (added 4.9–4.16). Patterns now include LLM-specific killers (spec misinterpretation, hallucinated objects, false-negative verification). |
| No explicit SCOPE header requirement | Process gap | Added SCOPE header requirement in §4.9 (spec misinterpretation prevention) and §9.1 as a standalone priming file. |
| No 100x workflow | Process gap | Added §10 with the 7-step 100x Workflow. Replaces the old 5-step Read→Build→Verify cycle. |
| No expert prompts | Tooling gap | Added §11 with Prompt A (Spec Fidelity + Mockup Translation) and Prompt B (Full Pre-Ship Gate). |
| No agent priming files section | Tooling gap | Added §9 with required files (spec-fidelity-checklist.md, mockup-translation-template.md, AGENTS.md/CLAUDE.md) and the SCOPE header template. |
| No visual progress bar for checklist | UX gap | Added §9 Golden Gate as a bordered ASCII table with pillar-grouped items, score tracker, and pass/fail threshold. |
| No cross-ref to Playbook Inventory | Cross-reference gap | Added reference to requirements-fidelity-playbook.md §Playbook Inventory — canonical source for playbook system document count and roles. |

### 2026-05-31 — Standardization Pass

| What was wrong | Category | Fix applied |
|----------------|----------|-------------|
| No Version field or Version History table | Missing metadata | Added Version: 2.1 and Version History table with 2.0 → 2.1 entries. |
| "Golden Checklist" named differently from other playbooks' "Golden Gate" | Naming inconsistency | Renamed all "Golden Checklist" references to "Golden Gate" to match the system-wide convention. |
| No cross-reference to Playbook Inventory | Cross-reference gap | Added reference to requirements-fidelity-playbook.md §Playbook Inventory. |

### 2026-06-01 — Spatial Optimization Gap (The "AI Blindspot")

| What was wrong | Category | Fix applied |
|----------------|----------|-------------|
| Golden Gate had no check for graph layout spatial utilization | Missing UX dimension — AI verifies "nodes render" but doesn't verify "nodes fit the human viewport" | Added "Graph spatial audit" check to Pillar 2 of the Golden Gate — checks >60% viewport utilization, no node overlap, all labels readable at default zoom. |
| No reference to UX playbook's spatial density section | Cross-reference gap | Golden Gate §9 now cross-references `ux-testing-playbook.md §9.7` for full detection protocol. |

### 2026-06-01 — Windows + Telemetry Hardening Sprint

| What was wrong | Category | Fix applied |
|----------------|----------|-------------|
| `signal.signal(signal.SIGTERM, ...)` called unconditionally on Windows | signal.SIGTERM is POSIX-only — raises ValueError on Windows | Added `hasattr(signal, "SIGTERM")` guard + `hasattr(signal, "SIGBREAK")` for Windows. |
| `os.fork()` in `start()` raises AttributeError on Windows | No exception handling around fork in daemon code | Wrapped fork in try/except with graceful degradation message: "Run `observeco watch foreground` instead". |
| `stop()` used CTRL_BREAK_EVENT only — no fallback if process ignores it | Windows process may not be a console app | Added `_windows_kill()` fallback via `taskkill /F`. |
| Telemetry client sent data on `OBSERVECO_TELEMETRY=on` default | No explicit user consent required before first send | Added local opt-in file `~/.observeco/.telemetry_opt_in`. All `send()` functions gate on `_is_opted_in()`. |
| No opt-in prompt on dashboard first load | User never asked about telemetry | Added `/api/telemetry-prompt` (htmx banner), `/api/telemetry-opt-in?choice=yes|no` (persist), `/api/telemetry-status` (JSON state check). |
|| CI F9 check searched raw HTTP first 500 chars | 30KB inline CSS pushed `<body>` past scan window | Audit scripts now search `<body>` content exclusively. |\n|\n|### 2026-06-01 — Team Shared-View Sprint\n|\n|| What was wrong | Category | Fix applied |\n||----------------|----------|-------------|\n|| `--shared` flag and `instance_id` wiring required across 5 files (dirs.py, db.py, cli.py, server.py, watch.py) | Cross-file coordination — required verifying import chain didn't break | Added import compile check: `python3 -c "from observeco.dashboard.server import app"` passes |\n|| Dashboard `/api/instances` endpoint queries pulse_log per agent — must handle empty DB gracefully | First-run safety — empty DB should return empty badge, not 500 | Endpoint early-returns empty string if OBSERVECO_SHARED_DB env var absent |\n|| `get_shared_db_path()` write-test could create `.observeco_write_test` files on network shares | Temp-file leak on shared filesystems | Test file uses `with suppress(OSError): test_file.unlink()` — cleaned up immediately |\n|| WAL mode already enabled in `_get_conn()` — no code change needed for concurrency | Already-got-it — verifying before writing prevented redundant change | Cross-reference check confirmed WAL was already set in `_init_db()` |

---

## Appendix A: The 4-Question Audit (reference card)

| # | Question | What to check | Fail if |
|---|----------|--------------|---------|
| 1 | **Exists?** | Does the element/section render? | DOM query returns null |
| 2 | **Correct?** | Does it show real data (not placeholders)? | Response contains "Loading...", static text, or hardcoded mock data instead of DB content |
| 3 | **Complete?** | Does it have ALL sections the spec describes? | Section count < spec-specified count |
| 4 | **Matches mockup?** | Does structure match mockup's section layout? | Section order differs, labels differ, visual hierarchy differs |

## Appendix B: Dependency Verification Quick Reference

```bash
# Before calling any new function
grep -r "function_name" src/

# Before importing any new package
pip list | grep package_name

# Before using any new API method
pytest tests/ -k "test_" --collect-only  # check test suite compatibility
python3 -c "import package_name; help(package_name.SomeClass)" 2>/dev/null
```

## Appendix C: Multi-File Edit Safety Net

After any change that touches multiple files (or a single file used by multiple modules):

```bash
# 1. Compile check
python3 -m py_compile src/file1.py src/file2.py

# 2. Full test suite
pytest

# 3. Import chain check
python3 -c "from observeco.dashboard.server import app; print('All imports OK')"

# 4. Runtime spec-fidelity check
python3 -c "
from fastapi.testclient import TestClient
from observeco.dashboard.server import app
client = TestClient(app)
for ep in ['/api/agents', '/api/agent-detail/kepler?tab=health', ...]:
    r = client.get(ep)
    assert 'Traceback' not in r.text
    assert r.status_code == 200
print('All endpoints OK')
```

---

## 14. SPOF Hardening — Data Pipeline Single-Point-of-Failure Pattern

### 14.1 The Pattern

Every system has background data-collection pipelines that feed its UI, alerts, or decision logic. When these pipelines depend on a single daemon, thread, or CLI invocation that the user must manually start — and that daemon's lifecycle is tied to a UI process — that's a **data SPOF** (Single Point of Failure).

**Detection checklist:**

| # | Question | How to check |
|---|----------|-------------|
| 1 | **Does the dashboard/UI read data that is written by a background process?** | Search for every `SELECT` in UI code that reads from writable tables. |
| 2 | **Is that background process started automatically with the UI?** | Trace the UI's startup code. Is the writer a daemon thread that dies with the process? |
| 3 | **If the writer crashes or is killed, does data collection resume on next UI start, or is there a gap?** | Check if the writer is a child process or independent daemon. |
| 4 | **Are there *other* data sources (drift, garden, pathway) that no daemon fills at all?** | Run `grep -r "INSERT.*TABLE" src/` for every table the dashboard reads. Cross-reference with running daemons. |
| 5 | **Can a human user on any platform (Mac, Linux, Windows) easily keep this running?** | If the answer involves systemd, launchd, or cron, it's not "easy" for most users. |

### 14.2 The Fix Architecture

```
┌─────────────────────────┐
│  Independent daemon     │  ← Runs in its own process
│  PID file for lifecycle │     Survives UI restarts
│  Heartbeat file for     │     Auto-discovers new agents
│  freshness checks       │     Writes ALL data tables
└────────┬────────────────┘
         │ reads (same SQLite DB)
         ▼
┌─────────────────────────┐
│  UI / Dashboard         │  ← Reads DB only
│  On startup: check      │     Never writes data
│  heartbeat freshness    │     Auto-launches daemon if stale
│  If stale: spawn daemon │     Ephemeral session
└─────────────────────────┘
```

**Principles:**
1. **Writers are independent processes** — not threads of the reader. A crash in data collection must not take down the UI.
2. **PID file + heartbeat** — external processes can check "is it running?" and "is it fresh?" by reading files, not by guessing process lists cross-platform.
3. **UI auto-launches on stale heartbeat** — the user never sees "No data" without the system first trying to start the collector.
4. **All write operations consolidated** — one daemon sweeps all tables (pulse, trim, drift, garden, pathway) rather than requiring separate CLIs for each.
5. **Cross-platform startup** — POSIX: double-fork + setsid. Windows: `DETACHED_PROCESS` subprocess.

### 14.3 Hardening Checklist (for any data pipeline)

Before deploying any feature that reads from a collect-and-store pipeline:

```
☐ 1. Who writes this table? One source or many?
☐ 2. Is the writer an independent process or a UI thread?
☐ 3. If the writer dies, does data collection resume automatically?
☐ 4. Is there a heartbeat/liveness check external processes can read?
☐ 5. Does the UI handle "stale data" gracefully?
     * Shows human-readable age (e.g., "last pulse 3h ago")
     * Offers to start the collector
     * Shows "Monitoring stopped" banner
☐ 6. Can a non-technical user start/stop/check the collector?
☐ 7. Does the collector write ALL data tables for its domain, or is
     there a second table that requires a separate CLI command?
```

### 14.4 Example: ObserveCo Watch Daemon SPOF Audit

| Table | Writer before fix | Writer after fix | Auto-continuous? |
|-------|-------------------|------------------|-----------------|
| `pulse_log` | `observeco watch --once` (manual) or thread in dashboard | Independent daemon | ✅ Every 30s |
| `chisel_trims` | Same thread | Same daemon (per-pulse) | ✅ Every 30s |
| `chisel_drift` | `observeco chisel drift` CLI only | Same daemon (every 5min) | ✅ Every 5min |
| `clawforge_garden` | `observeco memory garden` CLI only | Same daemon (every 15min) | ✅ Every 15min |
| `pathway_nodes/edges` | Nothing wrote these | Same daemon (every 15min) | ✅ Every 15min |
| `errors` | Thread (partial — probe failures) | Same daemon | ✅ Every cycle |

### 14.5 Cross-Platform Considerations

| Concern | POSIX (Mac/Linux) | Windows |
|---------|-------------------|---------|
| **Daemon creation** | `os.fork()` + `os.setsid()` + second fork to prevent terminal re-acquisition | `subprocess.Popen()` with `DETACHED_PROCESS` and `CREATE_NEW_PROCESS_GROUP` flags |
| **PID file** | Works natively | Works (subprocess returns PID) |
| **PID liveness** | `os.kill(pid, 0)` — signal 0 tests existence | `os.kill(pid, 0)` works same way |
| **Signal-based stop** | `os.kill(pid, SIGTERM)` — clean shutdown | `os.kill(pid, signal.CTRL_BREAK_EVENT)` on Windows |
| **Auto-start on dashboard** | Subprocess with `start_new_session=True` | Subprocess with `DETACHED_PROCESS` flag |
| **Install as service** | launchd plist (Mac) / systemd unit (Linux) | NSSM / Windows Service |

### 14.6 The Golden Rule

> **Every data-producing daemon must be an independent process, not a thread of a UI process. The heartbeat file is the contract between the writer and its consumers.**

---

## 15. SPOF Audit Template

Copy this into any feature spec or PR description to document the data pipeline architecture:

```markdown
### Data Pipeline: [Feature Name]

**Writer(s):** [which process/daemon writes]
**Reader(s):** [which process/UI reads]
**Writer lifecycle:** [independent daemon / UI thread / manual CLI]
**Heartbeat available?** [yes/no — path to heartbeat file]
**Stale data handling:** [what UI shows when data is stale]
**Tables written:** [list of tables]
**Tables that should be written but aren't:** [gaps]
**Cross-platform verified?** [Mac / Linux / Windows]
```

## Lessons Learned

| Date | Project | What happened | Root cause | Pattern | Fix applied |
|------|---------|---------------|-----------|---------|-------------|
| 2026-06-09 | ObserveCo | Stripe payment success → Pro not activated — 3 independent bugs | Payment pipeline had 3 sub-states not covered by any test | 4.20 | Added payment pipeline sub-state enumeration to spec template |
| 2026-06-09 | ObserveCo | loadLicenseStatus() crashes silently on 4 of 5 tabs | Cross-tab JS function assumes DOM element exists everywhere | 4.21 | Added null guard to all cross-tab JS functions |
| 2026-06-09 | ObserveCo | License deactivation updates backend but badge shows old state | State change handler doesn't trigger UI refresh | 4.22 | Added refresh call after every modal close |

---

*Failure today taught us that the code can be correct and the system can still be wrong. This playbook bridges that gap — forcing the system-level analysis BEFORE the code, and verifying the system-level properties AFTER the code.*
