# Side-by-Side: Text-Prompt vs Native Tool Calling

## Test Conditions
- **Model:** deepseek-v4-flash (via `custom-ollama` → `ollama.com/v1`)
- **Tasks:** τ-bench retail tasks 0-1 (Yusuf Rossi exchange)
- **Trials:** 2 per harness
- **Max steps:** 15 per trial
- **Date:** 2026-07-02

## Results

| Metric | Text-Prompt (grid) | Direct (native) | Δ |
|--------|-------------------|-----------------|---|
| Mean reward | 0.0 [CI: 0.0, 0.49] | 0.0 | 0 |
| Tool calls | 0 | 8 | +8 |
| Respond calls | 20 | 22 | +2 |
| Total calls | 20 | 30 | +10 |
| Total time | 333s | 78s | −255s (−77%) |
| Tokens | N/A | 220,728 | — |
| Avg time/call | 16.6s | 2.6s | −84% |
| Tool call rate | 0% | 27% | +27pp |

## Analysis

**Both scored 0.0 reward, but for different reasons:**

1. **Text-prompt harness** — 100% format-adherence collapse. The model never outputs valid JSON after 1-2 turns. All actions are `respond` (prose). The `hermes chat -q` flat-text serialization strips tool definitions of their structured meaning.

2. **Native tool calling** — 27% tool call rate. The model calls tools but makes wrong choices (asks for email instead of using `find_user_id_by_name_zip`), then gets stuck in a verification loop. 8 tool calls, 0 reward.

3. **Model capability** — deepseek-v4-flash has poor conversation state tracking. It asks for information the user already provided, loops on the same question, and can't follow a multi-step workflow.

## Harness Penalty
- Native tool calling gets **+27pp tool call rate** over text-prompt
- But still 0.0 reward — model capability is the bottleneck, not just the harness
- The harness penalty is real but doesn't matter until the model can solve the task at all

## Next Grid
- Run direct runner across all 3 models (flash, pro, ornith)
- Run text-prompt grid across all 3 models
- Compare reward delta per model
- The gap between direct and text-prompt is the harness penalty; the gap between models is the capability ceiling