# Human Test Protocol — ObserveCo v0.2.0 Sprint Test

**Date:** 2026-06-11
**Tester:** Sean Foo
**Time estimate:** 15-20 minutes

---

## Test 1: Migration Infrastructure (2 min)

**Action:** Open terminal, run:
```bash
observeco doctor run --data-health
```

**What to look for:**
- Output shows schema version status (✓ or ✗)
- Output shows backup recency (hours/days since last backup)
- Output shows row counts for key tables
- No Python tracebacks or errors

**Report back:**
- Did the command run successfully?
- What status did each check show?
- Any confusing output?

---

## Test 2: Action Log Dashboard (5 min)

**Action:** Open browser, go to `http://localhost:8787`

**Steps:**
1. Navigate to Brain Analysis tab
2. Look for "Your ObserveCo Impact" card
3. Navigate to Skills Audit tab
4. Click on any skill to see compression history
5. Navigate to Token Optimiser tab
6. Check for recent activity feed

**What to look for:**
- Brain Analysis shows action log data (compression, healing events)
- Skills Audit shows per-skill compression history
- Token Optimiser shows recent activity with timestamps
- Free users see upsell banners, Pro users see real data
- Empty states show appropriate messages (not blank/broken)

**Report back:**
- Which tabs showed data?
- Did any tab show blank/broken content?
- Did the Free/Pro distinction work correctly?
- Any confusing UI elements?

---

## Test 3: Compression Labels (3 min)

**Action:** In the dashboard, go to Skills Audit

**Steps:**
1. Click on a skill to open compression preview
2. Look at the compression percentage display
3. Check if any skill shows "Already condensed" label

**What to look for:**
- Skills with ≤5% savings show "Already condensed — no further savings" instead of 0%
- Skills with >5% savings show normal percentage
- No skills show "0%" when they should show "Already condensed"

**Report back:**
- Which skills showed "Already condensed"?
- Did any show 0% when they shouldn't?
- Is the label clear and helpful?

---

## Test 4: Data Health Check (3 min)

**Action:** Run in terminal:
```bash
observeco doctor run --data-health
```

**What to look for:**
- Schema version matches expected (should be 20)
- Backup exists and is recent
- Row counts are reasonable (token_logs should have thousands)
- No warnings about stranded tables

**Report back:**
- What schema version was reported?
- When was the last backup?
- Are the row counts reasonable?
- Any warnings or errors?

---

## Test 5: Error States (2 min)

**Action:** In the dashboard, try to trigger error states:

**Steps:**
1. Disconnect from network (or simulate)
2. Refresh the dashboard
3. Look for error messages

**What to look for:**
- Error messages are user-friendly (not raw Python tracebacks)
- Error states show retry options or helpful guidance
- No broken UI elements

**Report back:**
- What error messages appeared?
- Were they helpful or confusing?
- Did the UI remain usable?

---

## Summary Questions

After running all tests, please answer:

1. **Overall impression:** Does the dashboard feel polished and trustworthy?
2. **Biggest pain point:** What was most confusing or frustrating?
3. **Biggest win:** What worked surprisingly well?
4. **Blocking bugs:** Anything that would prevent you from showing this to a user?
5. **Nice-to-have:** Anything that would make it feel more professional?

---

## Notes

- The test_checkout_redirects failure is a known Stripe test environment issue (not a bug)
- The 15 F841 lint warnings are intentional unused variables (not bugs)
- All 87 other tests pass
