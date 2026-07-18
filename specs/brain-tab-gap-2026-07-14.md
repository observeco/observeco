# Brain Tab Gap Analysis — 2026-07-14

## Verdict
Three sections Sean flagged are **backend-complete but frontend-unwired**. Not missing logic — missing `loadBrain()` calls.

## Evidence

### 1. Efficiency scoring (session-based, across models)
- Backend: `src/observeco/dashboard/routes/efficiency.py:460` → `brain_efficiency()` → `GET /api/efficiency/brain`
- Returns: full HTML with model×archetype×efficiency matrix (686 sessions, real data)
- Test: `curl /api/efficiency/brain` → 200, renders "📊 Session Efficiency (fleet-wide · unattributed)"
- Frontend: `index_new.html` has **0 references** to `efficiency` or `api/efficiency`. `loadBrain()` never calls it.

### 2. Skill compression
- Backend: `GET /api/chisel/compress-skill` (server.py:5166) works. `skillSelect` + `skillCompressStatus` IDs exist in served HTML.
- Frontend: "📜 Skills Compression" section renders per-agent but `loadBrain()` (fleet view) doesn't surface it.

### 3. Compression history
- Backend: `compress_log` table has **686 rows** (real data).
- Frontend: `compressLogContainer` div shows "Loading..." permanently. **No JS populates it** — search for `compressLogContainer|loadCompressLog|/api/compress` in HTML = 0 matches. The container was scaffolded but the fetch was never written.

## Root Cause
`loadBrain()` (index_new.html:225) uses htmx `hx-get="/api/brain"` + `hx-on::after-swap="setTimeout(loadOptimiser, 100)"`. Only loads token-breakdown/savings/optimiser. Efficiency router + compression-history fetch were never wired into the swap.

## Fix Path (3 changes, all frontend)
1. **Efficiency**: Add `<div hx-get="/api/efficiency/brain" hx-trigger="revealed once" hx-swap="innerHTML">` to brainContainer, OR call it in `loadBrain()` JS.
2. **Compression history**: Add JS that fetches `/api/compress-log` (or query) and populates `compressLogContainer`. Need to confirm endpoint exists.
3. **Skill compression**: Already in HTML per-agent; confirm it's visible in fleet Brain tab or add to `loadBrain()`.

## Confidence
- Efficiency missing from frontend: **HIGH** (0 references, endpoint verified working)
- Compression history stuck on "Loading...": **HIGH** (no fetch JS, container static)
- Skill compression present but not surfaced at fleet level: **MODERATE** (section exists in HTML, need to confirm visibility)

## Next Step
Before building: confirm compression-history endpoint name. Then wire all 3 into `loadBrain()`. Route to forge (implementation) with this as the spec.
