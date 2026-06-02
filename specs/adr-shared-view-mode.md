### ADR: Shared-View Mode (Team Fleet)

**Status:** Approved — 2026-06-01
**Version:** 1.0

**Context:**
5 team members run `observeco dashboard`. Each instance uses a separate SQLite file at `~/.local/share/observeco/pulse.db`. They see different data. There is no way to verify they're looking at the same fleet.

**Options considered:**

1. **Central cloud server** — FastAPI on a shared host with WebSocket broadcast.
   - Rejected: Requires cloud hosting, auth, deployment. Overkill for 5-20 users.

2. **Shared SQLite on network filesystem** — Point all instances at the same `.db` file.
   - **Selected.** Minimal, zero-infrastructure, works with NFS/Dropbox/Synology/SMB.
   - WAL mode handles concurrent reads.
   - SQLite is the existing storage engine — no new dependencies.

3. **HTTP proxy / forwarder** — One instance runs as "primary", others proxy through it.
   - Rejected: Introduces SPOF, adds latency, complex to configure.

**Chosen option:** Shared SQLite via `--shared <path>` flag + `OBSERVECO_SHARED_DB` env var.

**Architecture:**
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Instance A  │     │  Instance B  │     │  Instance C  │
│  (Alice)     │     │  (Bob)       │     │  (Carol)     │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                   ┌────────────────┐
                   │  Shared .db     │
                   │  (NFS/Dropbox)  │
                   │  WAL mode       │
                   └────────────────┘
```

**Concurrent read safety:** SQLite WAL mode allows multiple readers. Writers serialize via lock — each daemon's 30s cycle is well within SQLite's write latency tolerance.

**Instance tracking:** Each pulse write includes an `instance_id` derived from `hostname + : + dashboard_port`. The heartbeat file now includes `instances: [...]` — a JSON array of recently-active instance IDs.

**Failure modes:**
- DB file doesn't exist → create it (same as non-shared mode)
- DB file is locked → retry with exponential backoff (WAL handles read concurrency)
- Shared path is unreachable → print clear error, fall back to local DB
- Two daemons write simultaneously → SQLite serializes writes, no corruption

**Tables affected:** `pulse_log` gets new `instance_id TEXT DEFAULT ''` column. No new tables needed.

**Non-goals (future):**
- Real-time WebSocket sync between instances (not needed for shared-view reading)
- Auth/permissions (all users share the same file)
- Cloud sync (would be a separate feature)

**Cross-platform:** Paths use platformdirs + explicit user-provided path. Works identically on macOS, Linux, Windows.
