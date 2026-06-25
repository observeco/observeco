# obs-spec-043: Hermes Post-Turn Webhook Hook

**Status:** ✅ Built — 2026-06-16
**Product:** Hermes Agent → ObserveCo
**Depends on:** ObserveCo `POST /api/tokens/log` endpoint (exists, extended with model/latency/tool_calls/topic_id via migration 29)
**Author:** Main

---

## §1 Problem

ObserveCo's cloud token tracking architecture (§14) has two lanes: a post-turn webhook (primary) and a provider billing API (fallback). The **backend endpoint** (`POST /api/tokens/log`) exists and is fully wired. The **Hermes-side hook** that calls it does not exist.

Without the hook, ObserveCo has zero cloud token data from Hermes agents. The dashboard shows "No token data recorded yet."

## §2 Solution

Add a fire-and-forget HTTP POST to `POST /api/tokens/log` at the end of every `run_conversation()` turn in Hermes' `agent/conversation_loop.py`. The POST carries token usage data the agent already computes internally.

## §3 RDR

```
Problem: ObserveCo's /api/tokens/log endpoint exists but no agent calls it.
         Cloud token tracking is dead without the agent-side hook.
Solution: Fire-and-forget POST to /api/tokens/log after every turn completes.
          Uses httpx (already a dependency). Never blocks the agent response.
Key constraint: POST must be fire-and-forget — 2s timeout, no retry, no exception
               propagation. If the POST fails, the agent continues as if nothing
               happened. Data loss is acceptable for v1 (provider billing API
               fallback catches gaps).
Success metric: >90% of agent turns produce a POST within 2s of completion.
               <0.5% of agent turns delayed by >50ms due to the POST.
```

## §4 Payload

```json
POST /api/tokens/log
{
  "agent_name": "main",
  "turn_id": "conv_abc123_turn_5",
  "model": "deepseek-v4-flash",
  "provider": "custom-ollama",
  "total_tokens": 8432,
  "input_tokens": 7800,
  "output_tokens": 632,
  "cache_read_tokens": 3200,
  "cache_creation_tokens": 0,
  "identity_tokens": 0,
  "skills_tokens": 0,
  "memory_tokens": 0,
  "tools_tokens": 0,
  "guidance_tokens": 0,
  "latency_ms": 3400,
  "tool_calls": ["search_files", "read_file"],
  "topic_id": ""
}
```

**Notes:**
- `agent_name` — from `agent._agent_name` or `agent.config.get("name", "hermes")` or profile name
- `turn_id` — constructed as `{session_id}_turn_{turn_number}`
- `model` — from `agent.model` (the actual model used)
- `provider` — from `agent.provider` (e.g. `custom-ollama`, `deepseek`)
- `total_tokens` / `input_tokens` / `output_tokens` / `cache_*` — **per-turn delta** (tokens used in THIS turn only). The agent already tracks per-turn usage in the response dict (`response.usage`). Cumulative session totals would cause the dashboard to double-count every turn. Per-turn delta is the correct shape for `token_logs`.
- `identity_tokens` through `guidance_tokens` — **set to 0 for v1**. Component breakdown requires prompt builder instrumentation (future work)
- `latency_ms` — wall-clock time of the turn (computed from `time.monotonic()` at turn start/end)
- `tool_calls` — list of tool names called this turn (from `messages` history)
- `topic_id` — from agent's platform context if available (Telegram topic ID)

## §5 States

| State | Display |
|-------|---------|
| Hook not installed (Hermes < v0.14.1) | "Agent not sending token data — update Hermes" |
| Hook installed, endpoint reachable | Normal data flow |
| Hook installed, endpoint unreachable | Silent data loss — agent continues, provider API catches gap |
| Hook installed, endpoint returns error | Silent data loss — same as unreachable |
| Component breakdown not instrumented | identity/skills/memory/tools/guidance show as 0 |

## §6 Implementation

### 6.1 Location

Insert the POST call in `agent/conversation_loop.py` at the end of `run_conversation()`, after the final response is built and before the return statement. Specifically after line ~4077 (the `on_session_end` plugin hook block) and before the return at line ~4095.

### 6.2 Mechanism

```python
import threading
import time as time_module
import httpx

def _post_token_usage(agent, turn_start_time, tool_names, turn_number):
    """Fire-and-forget POST of token usage to ObserveCo."""
    elapsed_ms = int((time_module.monotonic() - turn_start_time) * 1000)
    payload = {
        "agent_name": getattr(agent, "_agent_name", "hermes"),
        "turn_id": f"{agent.session_id}_turn_{turn_number}",
        "model": agent.model or "",
        "provider": getattr(agent, "_provider_name", ""),
        "total_tokens": agent.session_total_tokens,
        "input_tokens": agent.session_input_tokens,
        "output_tokens": agent.session_output_tokens,
        "cache_read_tokens": agent.session_cache_read_tokens,
        "cache_creation_tokens": agent.session_cache_write_tokens,
        "identity_tokens": 0,
        "skills_tokens": 0,
        "memory_tokens": 0,
        "tools_tokens": 0,
        "guidance_tokens": 0,
        "latency_ms": elapsed_ms,
        "tool_calls": tool_names,
        "topic_id": "",
    }
    try:
        with httpx.Client(timeout=2.0) as client:
            client.post(f"{observeco_url}/api/tokens/log", json=payload)
    except Exception:
        pass  # Fire-and-forget — never block the agent
```

### 6.3 Integration Point

In `run_conversation()`, at the turn start capture `turn_start_time = time_module.monotonic()`. At the end (after the `on_session_end` hook, before return), collect tool names from messages and spawn:

```python
threading.Thread(
    target=_post_token_usage,
    args=(agent, turn_start_time, tool_names, turn_number),
    daemon=True,
).start()
```

### 6.4 Configuration

The ObserveCo endpoint URL should be configurable via:
1. Environment variable `OBSERVECO_URL` (default: `http://localhost:9200`)
2. Agent config key `observeco_url`

This allows users to point at a remote ObserveCo instance.

## §7 Acceptance Criteria

- [ ] AC1: After every `run_conversation()` call, a POST is sent to `/api/tokens/log`
- [ ] AC2: POST is fire-and-forget — a 2s timeout prevents blocking
- [ ] AC3: If the endpoint is unreachable, the agent continues normally (no crash, no delay)
- [ ] AC4: Payload includes agent_name, turn_id, model, provider, total/input/output/cache tokens
- [ ] AC5: latency_ms reflects wall-clock time of the turn
- [ ] AC6: tool_calls lists the names of tools invoked this turn
- [ ] AC7: Component breakdown fields (identity/skills/memory/tools/guidance) are present but set to 0
- [ ] AC8: ObserveCo dashboard shows token data from Hermes within 1 turn

## §8 Future Work (Not in v1)

- **Component breakdown** — instrument `agent/prompt_builder.py` to count tokens per section (identity, skills, memory, tools, guidance) before concatenation. This requires changes to `build_skills_system_prompt()`, `build_context_files_prompt()`, and `load_soul_md()` to return per-section token counts.
- **topic_id** — extract from the agent's platform context (Telegram topic ID). Requires the gateway to pass topic context through to `run_conversation()`.
- **Per-turn delta** — currently sends cumulative session totals. Future: send per-turn delta (tokens used in THIS turn only, not the whole session).

## §9 Effort

~1 day (spec + build + verify)
