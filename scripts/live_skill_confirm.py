"""Live skill-write confirmation for ObserveCo #81.

Reads the OpenAI-compatible provider Hermes already uses (config.yaml ->
providers.deepseek) and mirrors it into ObserveCo's BYOK env vars IN-PROCESS,
so the key never hits shell history or chat. Then verifies a real LLM call
succeeds and runs a real heal to confirm a prevention skill is written live.

Safety: targets ONE real agent (passed as argv[1]); does not fleet-heal.
"""
import os
import sys
import yaml

CONFIG = os.path.expanduser("~/.hermes/config.yaml")

def load_deepseek_creds():
    with open(CONFIG) as f:
        cfg = yaml.safe_load(f)
    prov = cfg.get("providers", {}).get("deepseek", {})
    key = prov.get("api_key", "")
    base = prov.get("base_url", "")
    assert key and base, "deepseek provider missing api_key/base_url in config.yaml"
    return key, base

def main():
    agent = sys.argv[1] if len(sys.argv) > 1 else None
    key, base = load_deepseek_creds()
    # set in-process only
    os.environ["OBSERVECO_LLM_API_KEY"] = key
    os.environ["OBSERVECO_LLM_BASE_URL"] = base

    from observeco.llm_service import ask, _detect_llm_providers, _get_auto_provider, _gate
    from observeco.db import Database

    # Register a byok registry entry pointing at the OpenAI-compatible endpoint
    # Hermes already uses (deepseek). Without this row, the BYOK provider cannot
    # construct a call (api_format falls back to "byok" -> None). Idempotent.
    db = Database()
    if not db.get_provider_config("byok"):
        db.add_provider(
            name="byok", display_name="BYOK (OpenAI-compatible)",
            provider_type="custom", base_url=base, default_model="deepseek-chat",
            api_format="openai", priority=100,
        )
        print("registered byok provider (priority 100)")
    db.close()

    print("gate.should_call(heal_learn):", _gate.should_call(consumer="heal_learn", tier=2))
    p = _get_auto_provider(_detect_llm_providers())
    print("provider:", p.name if p else None, "| base:", base)

    # 1) real LLM call (proves the provider answers)
    out = ask("Reply with exactly: SKILL_TEST_OK", "", consumer="heal_learn", max_cost_cents=0.02, tier=2)
    print("real ask() returned:", repr(out)[:80] if out else None)
    if not out:
        print("FAIL: LLM call returned None — cannot confirm live skill write")
        sys.exit(1)

    # 2) real heal on one agent -> learn-after should write a skill
    from observeco.heal import run_heal, prevention as prev
    before = len(prev.list_skills(agent)) if agent else sum(len(prev.list_skills()) for _ in [0])
    print(f"skills before ({agent}):", before)
    run_heal(auto_heal=True, agent_name=agent, dry_run=False)
    after = len(prev.list_skills(agent))
    print(f"skills after ({agent}):", after)
    for s in prev.list_skills(agent):
        print("  -> id", s["id"], "| diag:", s["diagnosis"][:70])
    print("LIVE SKILL WRITE:", "CONFIRMED" if after > before else "NOT TRIGGERED")

if __name__ == "__main__":
    main()
