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
) -> None:
    """Run the harness optimization loop with full evaluation framework."""
    from observeco.capability.harness import HarnessOptimizer

    if no_baselines:
        print("WARNING: Running without baselines — gains will not be attributable to harness design vs search budget")

    optimizer = HarnessOptimizer()
    report = optimizer.optimize(agent, iterations=iterations, budget=budget, no_baselines=no_baselines)

    print(f"\n{'='*60}")
    print(f"Harness Optimization Run #{report['run_id'][:8]}")
    print(f"Agent: {agent}")
    print(f"{'='*60}\n")

    print(f"{'Method':<30} {'Dev Score':<12} {'Test Score':<12}")
    print(f"{'-'*54}")
    for method, scores in report['methods'].items():
        label = method.replace('_', ' ').title()
        dev = f"{scores['dev']*100:.1f}%" if scores.get('dev') else "N/A"
        test = f"{scores['test']*100:.1f}%" if scores.get('test') else "N/A"
        print(f"{label:<30} {dev:<12} {test:<12}")

    print(f"\nVerdict: {'PROMOTED' if report.get('promoted') else 'NOT PROMOTED'}")
    if report.get('promotion_reason'):
        print(f"  Reason: {report['promotion_reason']}")
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
