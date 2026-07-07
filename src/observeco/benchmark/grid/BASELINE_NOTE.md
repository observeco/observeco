# Grid Baseline: Text-Prompt Harness

## Result
- **Model:** deepseek-v4-flash (via `custom-ollama` → ollama.com/v1)
- **Config:** baseline (full context, full tool feedback, 120s timeout, 2 retries)
- **Tasks:** τ-bench retail tasks 0-1 (Yusuf Rossi exchange)
- **Trials:** 2
- **Mean reward:** 0.0 [CI: 0.0, 0.49]
- **Calls:** 20 (10 per trial × 2 trials)
- **Timeouts:** 0
- **Total time:** 333s (~16.6s/call)
- **Flags:** LOOP: task=1 trial=0/1 action=respond repeated 5x

## Ceiling Note
**Agent failed to emit any tool calls due to format adherence collapse in flat-text interface.**

The `hermes chat -q` pipeline serializes everything (tool definitions, conversation history, tool results) into flat text. The model receives tool descriptions as prose in the system prompt and must output valid JSON. This works for 1-2 turns but breaks down as conversation history grows — the model reverts to natural language responses instead of JSON tool calls.

This is a **harness limitation**, not a model capability ceiling. The model can do native tool calling (verified via Ollama API directly). The text-prompt harness costs 100% of tool-call accuracy on multi-turn tasks.

## Comparison Data
- **Direct τ-bench baseline:** See `direct/` results — measures model capability ceiling with native tool calling.
- **Reward delta:** Direct reward − 0.0 = harness penalty.
