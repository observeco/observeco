# obs-spec-053 — Config Timeline

**Spec ID:** obs-spec-053
**Title:** Config timeline — auto-detected configuration changes
**Status:** DRAFT
**Owner:** Main
**Depends on:** obs-spec-050 (data model)
**Master plan ref:** v0.5.0 "Capability Monitoring Layer"

---

## 1. Auto-Detection

The config timeline is populated automatically by watching:

### 1.1 SOUL.md Changes

Watch daemon (existing `observeco watch`) already monitors agent directories. Extend to detect SOUL.md modifications:

```python
def detect_soul_md_changes(agent_name, agent_dir):
    """Compare current SOUL.md hash against last known hash."""
    soul_path = Path(agent_dir) / "SOUL.md"
    if not soul_path.exists():
        return None
    current_hash = sha256(soul_path.read_bytes()).hexdigest()[:12]
    last_hash = get_last_known_hash(agent_name)
    if current_hash != last_hash:
        return {
            "change_type": "prompt_update",
            "description": extract_diff_summary(soul_path),
            "git_commit": get_git_commit(agent_dir),
        }
```

### 1.2 Model/Config Changes

Detected by comparing the current agent config (from Hermes YAML config files, the same config source used by the existing capability probe) against the last snapshot:

```python
def detect_config_changes(agent_name):
    current = get_agent_config(agent_name)
    last = get_last_config_snapshot(agent_name)
    if current.model != last.model:
        return {
            "change_type": "model_switch",
            "description": f"{last.model} → {current.model}",
        }
    if current.tools != last.tools:
        return {
            "change_type": "tool_update",
            "description": tool_diff_summary(current.tools, last.tools),
        }
```

### 1.3 Baseline Events

Auto-created when `BaselineManager.compute_baseline()` runs:

```python
{
    "change_type": "baseline",
    "description": f"Initial canary run completed. {pass_count}/{total} pass.",
    "accuracy": 82.4,
}
```

### 1.4 Drift Events

Auto-created when `DriftDetector` fires:

```python
{
    "change_type": "drift",
    "description": f"Config unchanged, quality dropped {drift_pct}%. Breach on {task_name}.",
    "accuracy": current_accuracy,
}
```

---

## 2. Segment Assignment

Each config snapshot is assigned a segment letter (A, B, C...) based on config_hash:

```python
def assign_segment(agent_name, config_hash):
    """Assign sequential segment letters per unique config_hash."""
    segments = get_existing_segments(agent_name)
    if config_hash in segments:
        return segments[config_hash]
    next_letter = chr(ord('A') + len(segments))
    return next_letter
```

Segments are displayed as badges on timeline events and in the legend.

---

## 3. API Endpoint

### `GET /api/capability/timeline?agent=NAME`

```json
{
  "agent": "Main",
  "segments": {
    "A": "deepseek-v4-pro",
    "B": "deepseek-v4-flash (initial)",
    "C": "deepseek-v4-flash (current)"
  },
  "events": [
    {
      "date": "2026-07-02T09:14:00",
      "type": "drift",
      "title": "Drift Detected",
      "description": "Config unchanged, quality dropped 3.2%.",
      "severity": "breach",
      "segment": "C",
      "accuracy": 79.2,
      "action_url": "/drift?agent=Main"
    },
    {
      "date": "2026-06-28T14:30:00",
      "type": "prompt_update",
      "title": "Prompt Updated",
      "description": "Changed system prompt preamble. Added tool_selection guidelines.",
      "git_commit": "a3f2c9e",
      "segment": "C"
    },
    {
      "date": "2026-06-25T11:05:00",
      "type": "model_switch",
      "title": "Model Switched",
      "description": "deepseek-v4-pro → flash. Accuracy dropped 1.2% but cost reduced 85%.",
      "segment": "B"
    },
    {
      "date": "2026-06-18T16:00:00",
      "type": "baseline",
      "title": "First Baseline",
      "description": "9 tasks, 7 pass, 1 hang, 1 fail.",
      "accuracy": 82.4,
      "segment": "A"
    }
  ]
}
```

---

## 4. Dashboard Component

### 4.1 Agent Selector

Pill-style buttons at top: Main, Dreamer, Hound, PA. Active pill highlighted.

### 4.2 Timeline

Vertical timeline with:
- Date column (left): date + time
- Dot (center): color-coded by event type
  - Green: baseline, model_switch
  - Yellow: prompt_update
  - Red: drift
  - Blue: tool_update
- Card (right): title, description, metadata, segment badge

### 4.3 Segment Legend

Below timeline: colored swatches with segment labels.

### 4.4 Drift Event Linking (Gladwell Fix #7)

Drift events show "Investigate →" link that navigates to the drift chart section in the dashboard (same page, scroll to `#drift-chart`).

---

## 6. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Config change detection | < 60s from change to timeline event | Watch daemon poll interval |
| Timeline page load | < 1s for 50 events | Dashboard render time |
| Segment assignment accuracy | 100% — no duplicate segments | `config_snapshots.segment` uniqueness per agent |

---

## 7. Dashboard State Table

| Component | Loading State | Empty State | Error State |
|-----------|-------------|-------------|-------------|
| Agent selector pills | Pills greyed out, "Loading agents..." | "No agents detected" | "Could not load agents" |
| Timeline | Skeleton timeline (5 grey event cards) | "No config changes detected yet — changes appear here when SOUL.md or config is modified" | "Timeline unavailable — check watch daemon" |
| Segment legend | Grey swatches | "No segments yet" | "Segment data unavailable" |

---

## 8. File Changes

| File | Change |
|------|--------|
| `src/observeco/capability/timeline.py` | New — ConfigTimeline, change detection |
| `src/observeco/dashboard/server.py` | Add `/api/capability/timeline` route |
| `src/observeco/dashboard/templates/index.html` | Add timeline section |
| `src/observeco/watch_consumers.py` | Extend to detect SOUL.md/config changes |
