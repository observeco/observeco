"""`observeco graph` — Code intelligence CLI."""

from __future__ import annotations

import typer

graph_app = typer.Typer(help="Code intelligence graph — module dependencies, callers, callees", no_args_is_help=True)


@graph_app.command(name="init")
def graph_init() -> None:
    """Initialize (or re-create) the graph database."""
    from observeco.graph.db import GraphDB
    db = GraphDB()
    stats = db.get_stats()
    typer.echo(f"Graph DB initialized: {stats['files']} files, {stats['nodes']} nodes, {stats['edges']} edges")
    typer.echo(f"  Path: {db.db_path}")
    typer.echo(f"  Node kinds: {stats['node_kinds']}")


@graph_app.command(name="index")
def graph_index(
    path: str = typer.Option(".", "--path", "-p", help="Directory to index"),
    recursive: bool = typer.Option(True, "--recursive/--flat", help="Recurse into subdirectories"),
    clear: bool = typer.Option(False, "--clear", "-c", help="Clear existing graph first"),
) -> None:
    """Index Python source files into the code graph."""
    from observeco.graph.indexer import Indexer

    idx = Indexer()
    pattern = "**/*.py" if recursive else "*.py"

    if clear:
        idx.db.clear()
        typer.echo("Cleared existing graph.")

    results = idx.index_directory(path, pattern)
    indexed = [r for r in results if r["status"] == "indexed"]
    unchanged = [r for r in results if r["status"] == "unchanged"]
    errors = [r for r in results if r.get("status") == "error"]

    total_nodes = sum(r.get("nodes", 0) for r in indexed)
    total_edges = sum(r.get("edges", 0) for r in indexed)

    typer.echo(f"Indexed: {len(indexed)} files (+{total_nodes} nodes, +{total_edges} edges)")
    if unchanged:
        typer.echo(f"Unchanged: {len(unchanged)} files (skipped)")
    if errors:
        typer.echo(f"Errors: {len(errors)} files")
        for e in errors:
            typer.echo(f"  ✗ {e['file']}: {e.get('error', 'unknown')}")

    from observeco.graph.db import GraphDB
    db = GraphDB()
    stats = db.get_stats()
    typer.echo(f"Graph total: {stats['nodes']} nodes, {stats['edges']} edges, {stats['files']} files")


@graph_app.command(name="search")
def graph_search(
    query: str = typer.Argument(..., help="FTS5 search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results"),
) -> None:
    """Search the code graph for functions, classes, and modules."""
    from observeco.graph.db import GraphDB
    db = GraphDB()
    results = db.search_nodes(query, limit=limit)
    if not results:
        typer.echo("No results.")
        return
    for r in results:
        start = r.get("start_line", "?")
        end = r.get("end_line", "?")
        file_short = r.get("file_path", "?").split("/")[-1]
        kind = r["kind"].ljust(10)
        typer.echo(f"  {kind} {r['qualified_name']}  [{file_short}:{start}-{end}]")


@graph_app.command(name="callers")
def graph_callers(
    name: str = typer.Argument(..., help="Qualified function/method name"),
) -> None:
    """Show all functions that call a given function."""
    from observeco.graph.db import GraphDB
    db = GraphDB()
    node = db.get_node_by_qualified_name(name)
    if not node:
        typer.echo(f"Node not found: {name}")
        raise typer.Exit(1)
    callers = db.get_callers(node["id"])
    if not callers:
        typer.echo(f"No callers found for {name}.")
        return
    typer.echo(f"Callers of {name}:")
    for c in callers:
        typer.echo(f"  ← {c['qualified_name']} [{c['file_path']}:{c['start_line']}]")


@graph_app.command(name="callees")
def graph_callees(
    name: str = typer.Argument(..., help="Qualified function/method name"),
) -> None:
    """Show all functions called by a given function."""
    from observeco.graph.db import GraphDB
    db = GraphDB()
    node = db.get_node_by_qualified_name(name)
    if not node:
        typer.echo(f"Node not found: {name}")
        raise typer.Exit(1)
    callees = db.get_callees(node["id"])
    if not callees:
        typer.echo(f"No callees found for {name}.")
        return
    typer.echo(f"Callees of {name}:")
    for c in callees:
        typer.echo(f"  → {c['qualified_name']} [{c['file_path']}:{c['start_line']}]")


@graph_app.command(name="stats")
def graph_stats() -> None:
    """Show graph statistics."""
    from observeco.graph.db import GraphDB
    db = GraphDB()
    stats = db.get_stats()
    typer.echo(f"Files:  {stats['files']}")
    typer.echo(f"Nodes:  {stats['nodes']}")
    typer.echo(f"Edges:  {stats['edges']}")
    typer.echo("")
    for kind, count in stats.get("node_kinds", {}).items():
        typer.echo(f"  {kind}: {count}")
    typer.echo("")
    for kind, count in stats.get("edge_kinds", {}).items():
        typer.echo(f"  → {kind}: {count}")


@graph_app.command(name="watch")
def graph_watch(
    path: str = typer.Option(".", "--path", "-p", help="Directory to watch"),
    recursive: bool = typer.Option(True, "--recursive/--flat", help="Recurse into subdirectories"),
    once: bool = typer.Option(False, "--once", help="Single scan and exit"),
    interval: int = typer.Option(5, "--interval", "-i", help="Poll interval in seconds"),
) -> None:
    """Watch for file changes and re-index automatically (intelligence-driven)."""
    from observeco.graph.watch import run_graph_watch
    run_graph_watch(directory=path, recursive=recursive, once=once, interval=interval)
