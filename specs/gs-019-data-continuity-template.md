## N. Data Continuity (GS-019 — mandatory)

**What happens to existing data?**
<State whether any existing table is migrated/dropped. Name every schema change and
mark it additive or destructive. If a field/value moves location, state where it is
captured first so nothing is lost.>
- Migrations: <Migration NN — additive | destructive>
- Telemetry tables touched: <none | list>

**Is backup required?**
<If any operation is destructive (DROP/ALTER/recreate-table), `db.backup()` MUST run
before it per GS-019 §Principle 2. If purely additive, state that no backup is
triggered. For features that mutate user-owned files, state the file-level safety
mechanism (atomic rename + owned snapshot) that stands in for db backup.>

**What does the user see if empty?**
<Map each empty case to a concrete UI state — never a blank or stack trace:>
- Empty (fresh install): <what renders>
- Empty (post-upgrade): <re-probe / re-derive, not a blank>
- Empty (post-retention): <independent of feature state?>
- Error: <reason + remediation surfaced via ActiveFeature.reason / next_tier_hint>

**What's the recovery path?**
<For each way state can be lost or a write can fail, give the recovery:>
- Derived/cache data lost: <recompute — harmless?>
- Write interrupted: <atomic guarantee — old-or-new, retry next pass>
- Source file missing/unreadable: <skip + surface in discovery report, no crash>
- Worst case: <the safety invariant that still holds — e.g. agent never broken>

**Self-monitoring (GS-019 §Principle 5):**
<List the per-pass metrics: row counts / last insert / schema version / backup recency,
plus any feature-specific signal (tier drift, dead-port window, revert count).>
