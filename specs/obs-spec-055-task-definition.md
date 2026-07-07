# obs-spec-055 — Task Definition UI

**Spec ID:** obs-spec-055
**Title:** Task definition — YAML editor, form mode, assertions system
**Status:** DRAFT
**Owner:** Main
**Depends on:** obs-spec-050 (data model)
**Master plan ref:** v0.5.0 "Capability Monitoring Layer"

---

## 1. CLI Entry Point

```
observeco task list [--agent AGENT]
observeco task create [--yaml FILE]
observeco task edit TASK_ID [--yaml FILE]
observeco task delete TASK_ID
observeco task validate [--yaml FILE]
```

- `task list` — shows all defined tasks with status indicators
- `task create` — creates a new task from YAML or interactive prompt
- `task edit` — edits an existing task
- `task delete` — deletes a task
- `task validate` — validates a YAML file without saving

---

## 2. Task YAML Schema

```yaml
name: chart-interpretation
description: "Agent reads a bar chart and answers questions about the data"
prompt: |
  Given the following chart data, answer the question.
  Chart: {{ chart_data }}
  Question: {{ question }}
assertions:
  - type: numeric_range
    target: answer
    min: 0
    max: 100
    tolerance: 5
  - type: contains
    target: reasoning
    keywords: ["increase", "decrease", "unchanged"]
timeout: 45
model: deepseek-v4-flash
trials: 3
```

### 2.1 Assertion Types

| Type | Fields | Description |
|------|--------|-------------|
| `exact_match` | `target` | Output must match target exactly (after strip) |
| `contains` | `target`, `keywords` | Output must contain all keywords |
| `numeric_range` | `target`, `min`, `max`, `tolerance` | Extracted number must be within range ± tolerance |
| `regex` | `target`, `pattern` | Output must match regex pattern |
| `llm_judge` | `target`, `criteria` | LLM evaluates output against criteria (see spec-051 §5) |

### 2.2 Template Variables

Variables use `{{ var_name }}` syntax. When running a task, the runner provides sample data for each variable. Built-in tasks ship with sample data files at `~/.observeco/tasks/samples/`.

**Override precedence:** CLI `--trials N` flag overrides the task's default `trials` value. CLI `--model M` flag overrides the task's `model` override. If neither flag nor task default is set, the agent's current model is used.

---

## 3. API Endpoints

### `GET /api/capability/tasks`

Returns all tasks:

```json
{
  "tasks": [
    {
      "id": "chart-interpretation",
      "name": "Chart interpretation",
      "description": "Agent reads a bar chart...",
      "assertion_type": "numeric_range",
      "timeout": 45,
      "trials": 3,
      "built_in": true,
      "last_run": "2026-07-02T09:00:00",
      "last_accuracy": 34.0
    }
  ]
}
```

### `POST /api/capability/tasks`

Create or update a task. Body is the YAML content as JSON.

### `DELETE /api/capability/tasks/{id}`

Delete a task.

---

## 4. Dashboard Component

### 4.1 Task List

List of all defined tasks with:
- Status dot (green = passing, yellow = degrading, grey = no data)
- Task name
- Meta line: assertion type, timeout, assertion count
- Actions: Edit, Duplicate, Delete

### 4.2 Task Editor (YAML Mode)

Code editor with monospace font, basic YAML syntax highlighting (new component — no existing code editor in the dashboard, use a `<textarea>` with monospace font as MVP). Shows the raw YAML. "Form" / "YAML" toggle at top.

### 4.3 Task Editor (Form Mode)

Structured form with fields:
- Task Name (text input)
- Description (text input, optional)
- Prompt Template (textarea, monospace)
- Assertion Type (dropdown: exact_match / contains / numeric_range / regex / llm_judge)
- Timeout (number input)
- Model Override (dropdown: default / model list)
- Trials (number input)

### 4.4 Empty States

- **No tasks defined:** "Create your first task to start measuring quality" + "New Task" button
- **No runs yet:** "Run a canary to see results" + "Run Canary" button

---

## 5. Built-in Tasks

Shipped with ObserveCo, 9 tasks covering the canary suite (separate from the existing lm-eval benchmark tasks in `benchmark/engine.py` — these are for the capability monitoring system, user-defined and assertion-based):

1. Extract structured data (exact_match)
2. Follow multi-step instructions (contains)
3. Arithmetic reasoning (numeric_range)
4. Summarize conversation (contains)
5. Tool selection (contains)
6. Time-bound response (exact_match)
7. Chart interpretation (numeric_range)
8. Document Q&A (contains)
9. Code generation (regex)

Each has sample data files at `~/.observeco/tasks/samples/`.

**Note (2026-07-06):** The current assertion types are insufficient for meaningful quality evaluation. 6 of 9 tasks use keyword containment checks that can be passed by echoing prompt content. 6 of 9 tasks have `{{ template }}` variables that are silently skipped for agents without context to resolve them. See **obs-spec-057-benchmark-methodology-upgrade.md** for the full upgrade plan — adds `llm_judge`, `json_schema`, `semantic_similarity`, `expected_output`, `category`, `difficulty`, temperature control, and concrete fixture data.

---

## 6. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Canary run completion | 95% of runs complete under 5 min | `canary_runs.completed_at - started_at` |
| Drift detection FPR | False positive rate < 5% | Manual audit of first 100 drift events |
| Grid report load | < 2s for 9 tasks × 4 configs | Dashboard render time |
| Task definition save | < 500ms | API response time |
| Config change detection | < 60s from change to timeline event | Watch daemon poll interval |

---

## 8. Dashboard State Table

| Component | Loading State | Empty State | Error State |
|-----------|-------------|-------------|-------------|
| Task list | Skeleton list (3 grey items) | "No tasks defined — create your first task to start measuring quality" | "Could not load tasks — check database" |
| Task editor (YAML) | "Loading task..." | "Select a task to edit" | "Could not load task — check YAML syntax" |
| Task editor (Form) | "Loading form..." | "Select a task to edit" | "Could not load form" |
| "New Task" button | Spinner | Enabled | "Could not create task" |

---

## 9. File Changes

| File | Change |
|------|--------|
| `src/observeco/cli.py` | Add `task` command group |
| `src/observeco/capability/tasks.py` | New — TaskManager, YAML validation |
| `src/observeco/dashboard/server.py` | Add `/api/capability/tasks` routes |
| `src/observeco/dashboard/templates/index.html` | Add task list + editor section |
| `src/observeco/capability/tasks_builtin/` | New — 9 built-in task YAML files |
