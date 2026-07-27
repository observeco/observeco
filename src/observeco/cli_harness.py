"""Harness optimization CLI commands (obs-spec-056 + obs-spec-061).

Registered as a typer sub-app on the main observeco CLI.
"""
from __future__ import annotations

import typer

harness_app = typer.Typer(
    help="Harness optimization — auto-tune agent config + evaluation framework",
    no_args_is_help=True,
)


@harness_app.command(name="optimize")
def harness_optimize(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    iterations: int = typer.Option(5, "--iterations", "-n", help="Number of optimization iterations"),
    budget: int = typer.Option(45, "--budget", "-b", help="Total compute budget (agent rollouts)"),
    no_baselines: bool = typer.Option(False, "--no-baselines", help="Skip baseline comparison (not recommended)"),
    no_phantom_gate: bool = typer.Option(False, "--no-phantom-gate", help="DEBUG ONLY: disable Phantom Guardrail gate (refused in cron)"),
    context_bloat_threshold: float = typer.Option(2.0, "--context-bloat-threshold", help="Max frontier prompt size multiplier"),
    with_experience: bool = typer.Option(False, "--with-experience", help="Enable experience-bank retrieval for proposer"),
) -> None:
    """Run the harness optimization loop with full evaluation framework."""
    from observeco.capability.harness import HarnessOptimizer

    if no_baselines:
        print("WARNING: Running without baselines — gains will not be attributable to harness design vs search budget")

    optimizer = HarnessOptimizer()
    report = optimizer.optimize(
        agent, iterations=iterations, budget=budget, no_baselines=no_baselines,
        no_phantom_gate=no_phantom_gate,
        context_bloat_threshold=context_bloat_threshold,
        with_experience=with_experience,
    )

    print(f"\n{'='*60}")
    print(f"Harness Optimization Run #{report['run_id'][:8]}")
    print(f"Agent: {agent}")
    print(f"{'='*60}\n")

    if report.get("skipped"):
        print(f"SKIPPED: {report['promotion_reason']}\n")
        return

    print(f"{'Method':<30} {'Dev Score':<12} {'Test Score':<12}")
    print(f"{'-'*54}")
    for method, scores in report['methods'].items():
        label = method.replace('_', ' ').title()
        dev = f"{scores['dev']*100:.1f}%" if scores.get('dev') else "N/A"
        test = f"{scores['test']*100:.1f}%" if scores.get('test') else "N/A"
        print(f"{label:<30} {dev:<12} {test:<12}")

    print(f"Verdict: {'PROMOTED' if report.get('promoted') else 'NOT PROMOTED'}")
    if report.get('promotion_reason'):
        print(f"  Reason: {report['promotion_reason']}")
    print()


@harness_app.command(name="history")
def harness_history(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries to show"),
) -> None:
    """Show harness optimization history — all candidates with scores."""
    from observeco.db import Database

    db = Database()
    conn = db._get_conn()

    rows = conn.execute(
        "SELECT e.id, e.iteration, e.edit_text, e.classification, "
        "e.dev_score, e.incumbent_score, e.promoted, e.promotion_reason, "
        "r.agent_name, r.started_at "
        "FROM harness_edits e "
        "JOIN harness_optimization_runs r ON e.optimization_run_id = r.id "
        "WHERE r.agent_name = ? "
        "ORDER BY r.started_at DESC, e.iteration ASC "
        "LIMIT ?",
        (agent, limit),
    ).fetchall()

    if not rows:
        print(f"No harness optimization history found for agent '{agent}'.")
        return

    print(f"\n{'='*80}")
    print(f"Harness Optimization History — Agent: {agent}")
    print(f"{'='*80}\n")

    for row in rows:
        r = dict(row)
        status = "✅ PROMOTED" if r["promoted"] else "❌ rejected"
        dev_s = f"{r['dev_score']*100:.1f}%" if r['dev_score'] else "N/A"
        inc_s = f"{r['incumbent_score']*100:.1f}%" if r['incumbent_score'] else "N/A"
        print(f"  Iter {r['iteration']:<3} | {status:<14} | dev={dev_s:<8} inc={inc_s:<8} | {r['edit_text'][:60]}")
        if r.get("promotion_reason"):
            print(f"         {'':12} reason: {r['promotion_reason']}")
    print()


@harness_app.command(name="frontier")
def harness_frontier(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
) -> None:
    """Show the current best harness (frontier) for an agent."""
    import json

    from observeco.db import Database

    db = Database()
    conn = db._get_conn()

    row = conn.execute(
        "SELECT f.*, c.description, c.mechanism_type, c.dev_score "
        "FROM harness_frontier f "
        "LEFT JOIN harness_candidates c ON f.candidate_id = c.id "
        "WHERE f.agent_name = ?",
        (agent,),
    ).fetchone()

    if not row:
        print(f"No frontier found for agent '{agent}'. Run `harness optimize` first.")
        return

    r = dict(row)
    print(f"\n{'='*60}")
    print(f"Current Frontier — Agent: {agent}")
    print(f"{'='*60}")
    print(f"  Score:       {r['score']*100:.1f}%" if r['score'] else "  Score: N/A")
    print(f"  Candidate:   {r.get('description', 'N/A')[:80]}")
    print(f"  Type:        {r.get('mechanism_type', 'N/A')}")
    try:
        stack = json.loads(r.get("mechanism_stack", "[]"))
        if stack:
            print(f"  Mechanisms:  {len(stack)} stacked")
            for i, m in enumerate(stack):
                print(f"    {i+1}. {m}")
    except (json.JSONDecodeError, TypeError):
        pass
    print(f"  Updated:     {r.get('updated_at', 'N/A')}")
    print()


@harness_app.command(name="experience")
def harness_experience(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    clear: bool = typer.Option(False, "--clear", help="Prune all experiences for this agent"),
) -> None:
    """Show or clear the experience bank for an agent (obs-spec-088 §3)."""
    from observeco.capability.experience import ExperienceBank

    bank = ExperienceBank()
    if clear:
        n = bank.clear(agent)
        print(f"Cleared {n} experiences for agent '{agent}'.")
        return

    stats = bank.stats(agent)
    print(f"\n{'='*60}")
    print(f"Experience Bank — Agent: {agent}")
    print(f"{'='*60}")
    print(f"  Total experiences: {stats['total']}")
    print(f"  Global patterns:   {stats['global_patterns']}")
    print(f"  Per layer:          {stats['per_layer']}")
    if stats['failure_classes']:
        print("  Failure classes (observed):")
        for fc, c in stats['failure_classes'].items():
            print(f"    {fc}: {c}")
    if stats['rejection_log']:
        print(f"  Phantom rejections ({len(stats['rejection_log'])}):")
        for r in stats['rejection_log'][:10]:
            print(f"    {r['failure_class']}: {r['diagnosis'][:60]}")
    print()


@harness_app.command(name="revert")
def harness_revert(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
) -> None:
    """PG-5 edit-and-revert: remove the most recently deployed harness edit.

    Restores the live agent's SOUL.md from the pre-deploy backup and pops the
    last entry from the frontier stack. Safe to call repeatedly (LIFO).
    """
    from observeco.capability.harness import HarnessOptimizer

    optimizer = HarnessOptimizer()
    result = optimizer._revert_last_edit(agent)
    if result.get("reverted"):
        print(f"✅ Reverted last edit for '{agent}'.")
        print(f"   Removed: {result.get('removed', 'n/a')}")
        print(f"   Remaining stack ({len(result.get('remaining_stack', []))}):")
        for i, m in enumerate(result.get("remaining_stack", [])):
            print(f"     {i+1}. {m}")
    else:
        print(f"⚠️  No edit reverted: {result.get('reason', 'unknown')}")


@harness_app.command(name="gate")
def harness_gate(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    test: bool = typer.Option(False, "--test", help="Run Counterfactual Fabrication Lab self-check"),
) -> None:
    """Phantom Guardrail gate operations (obs-spec-088 §2)."""
    from observeco.capability.harness import HarnessOptimizer

    if not test:
        print("Use --test to run the Counterfactual Fabrication Lab self-check.")
        return

    optimizer = HarnessOptimizer()
    result = optimizer.run_gate_test(agent)
    print(f"\n{'='*60}")
    print(f"Phantom Guardrail Gate Test — Agent: {agent}")
    print(f"{'='*60}")
    print(f"  Verdict: {result['verdict']}")
    print(f"  Total runs: {result['total_runs']} | Fabricated: {result['fabricated_runs']} "
          f"| Rate: {result['fabrication_rate']*100:.1f}%")
    for r in result['detail']:
        mark = "✅" if r['accepted'] == r['expected'] else "❌"
        print(f"  {mark} {r['edit'][:50]} → accepted={r['accepted']} (expected={r['expected']})")
    print()



@harness_app.command(name="baseline")
def harness_baseline(
    agent: str = typer.Option("default", "--agent", "-a", help="Hermes agent profile name"),
    budget: int = typer.Option(45, "--budget", "-b", help="Total compute budget (agent rollouts)"),
) -> None:
    """Run test-time scaling baselines for comparison."""
    from observeco.capability.harness import HarnessOptimizer

    optimizer = HarnessOptimizer()
    baseline_report = optimizer.runner.run(agent, split='dev')

    print(f"\n{'='*60}")
    print(f"Test-Time Scaling Baselines — Agent: {agent}")
    print(f"{'='*60}\n")
    print(f"{'Method':<30} {'Score':<12}")
    print(f"{'-'*42}")
    print(f"{'Baseline (single-shot)':<30} {baseline_report.overall_accuracy*100:.1f}%")
