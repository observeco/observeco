"""Golden Gate runner — playbook compliance verification for ObserveCo.

Usage:
    from observeco.gate.runner import run_gate
    results = run_gate(full=True)
"""

import re
import sys
from pathlib import Path

RESULT_PASS = "PASS"
RESULT_FAIL = "FAIL"
RESULT_SKIP = "SKIP"
RESULT_WARN = "WARN"


class GateResult:
    """Single gate check result."""

    def __init__(self, section: str, name: str, status: str, detail: str = ""):
        self.section = section
        self.name = name
        self.status = status
        self.detail = detail

    def to_dict(self) -> dict:
        return {
            "section": self.section,
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }

    def __repr__(self) -> str:
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "WARN": "⚠️"}.get(
            self.status, "❓"
        )
        return f"  {icon} [{self.section}] {self.name}\n     {self.detail}"


def _get_app():
    """Lazy-import the FastAPI app for TestClient checks."""
    _src = Path(__file__).resolve().parent.parent.parent.parent / "src"
    if _src.is_dir() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))
    from fastapi.testclient import TestClient

    from observeco.dashboard.server import app

    return TestClient(app)


# ── Gate sections ────────────────────────────────────────────────────


def _gate_server_startup(client) -> list[GateResult]:
    """Section 0: Server startup check."""
    results = []
    r = client.get("/")
    ok = r.status_code == 200
    results.append(
        GateResult("Server", "Root returns 200", RESULT_PASS if ok else RESULT_FAIL, f"HTTP {r.status_code}")
    )
    has_html = "ObserveCo" in r.text and ("DOCTYPE" in r.text or "!DOCTYPE" in r.text or "!doctype" in r.text)
    results.append(
        GateResult("Server", "Returns HTML content", RESULT_PASS if has_html else RESULT_FAIL, "HTML signature check")
    )
    notrace = "Traceback" not in r.text and "Internal Server Error" not in r.text
    results.append(
        GateResult("Server", "No tracebacks", RESULT_PASS if notrace else RESULT_FAIL, "")
    )
    return results


def _gate_api_endpoints(client) -> list[GateResult]:
    """Section 1: API endpoint health — all return 200, no tracebacks."""
    results = []
    endpoints = [
        "/api/fleet-summary",
        "/api/agents",
        "/api/errors",
        "/api/alerts",
        "/api/phase",
    ]
    for path in endpoints:
        r = client.get(path)
        ok = r.status_code == 200 and "Traceback" not in r.text and "Internal Server Error" not in r.text
        results.append(
            GateResult(
                "API",
                f"{path} returns 200 + clean",
                RESULT_PASS if ok else RESULT_FAIL,
                f"HTTP {r.status_code}, {len(r.text)}b",
            )
        )
    return results


def _gate_fstring_leaks(client) -> list[GateResult]:
    """Section 2: Coding Fidelity — f-string leak detection."""
    results = []
    total_leaks = 0
    endpoints = ["/api/agents", "/api/fleet-summary", "/api/alerts", "/api/errors"]
    for path in endpoints:
        r = client.get(path)
        # Look for literal {var_name} patterns that indicate f-string prefix missing
        leaks = re.findall(r'(?<!\$)\{[a-z_][a-z_0-9]{2,}\}', r.text)
        if leaks:
            total_leaks += len(leaks)
            results.append(
                GateResult("Coding", f"{path}: f-string leaks", RESULT_FAIL, f"{len(leaks)} leaks: {set(leaks)}")
            )
    if total_leaks == 0:
        results.append(
            GateResult("Coding", "f-string leak scan", RESULT_PASS, "0 leaks across all endpoints")
        )
    return results


def _gate_spec_fidelity(client) -> list[GateResult]:
    """Section 3: Spec fidelity — check endpoint content markers."""
    results = []
    markers = {
        "/api/agents": ("section", "agent"),
        "/api/fleet-summary": ("status-row", "alive"),
        "/api/errors": ("error", "Error"),
        "/api/alerts": ("alert", "Alert"),
    }
    for path, marker_list in markers.items():
        r = client.get(path)
        all_found = all(m in r.text for m in marker_list)
        results.append(
            GateResult(
                "Spec",
                f"{path}: content markers present",
                RESULT_PASS if all_found else RESULT_FAIL,
                f"Markers: {marker_list}",
            )
        )
    return results


def _gate_spatial_audit() -> list[GateResult]:
    """Section 4: Spatial density audit — check the pathway map layout file exists and flag verification."""
    results = []
    # Find the pathway map HTML or template
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    pathway_files = list(repo_root.glob("**/pathway*"))
    if pathway_files:
        f = pathway_files[0]
        size = f.stat().st_size
        results.append(
            GateResult(
                "Spatial",
                "Pathway map file exists",
                RESULT_PASS,
                f"{f.name} ({size}b)",
            )
        )
        results.append(
            GateResult(
                "Spatial",
                "3-question audit (manual)",
                RESULT_WARN,
                "Run §9.7 audit: 1) >60% viewport filled? 2) No node overlap? 3) Labels readable at default zoom?",
            )
        )
    else:
        results.append(
            GateResult("Spatial", "Graph visualization", RESULT_SKIP, "No pathway map / graph viz files found")
        )
    return results


def _gate_data_pipeline() -> list[GateResult]:
    """Section 5: System design — data pipeline audit."""
    results = []
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    # Check key files exist
    key_files = ["src/observeco/pulse/check.py", "src/observeco/pulse/circuit.py", "src/observeco/db.py"]
    all_exist = True
    for kf in key_files:
        p = repo_root / kf
        if not p.exists():
            all_exist = False
            results.append(
                GateResult("System", f"Source file: {kf}", RESULT_FAIL, "Not found")
            )
    if all_exist:
        results.append(
            GateResult("System", "Core source files", RESULT_PASS, f"All {len(key_files)} present")
        )
    return results


def _gate_code_graph() -> list[GateResult]:
    """Section 6: CodeGraph index status."""
    results = []
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    cg = repo_root / ".codegraph"
    if cg.exists():
        stat_files = list(cg.glob("**/*"))
        results.append(
            GateResult("CodeGraph", "Index exists", RESULT_PASS, f"{len(stat_files)} files in .codegraph")
        )
    else:
        results.append(
            GateResult("CodeGraph", "Index exists", RESULT_SKIP, "No .codegraph directory — run 'codegraph index' first")
        )
    return results


# ── Main gate runner ─────────────────────────────────────────────────


def run_gate(full: bool = True, json_output: bool = False) -> list[GateResult]:
    """Run all Golden Gate checks. Returns list of GateResult objects.

    Args:
        full: If True, run all gates. If False, run coding-only.
        json_output: If True, don't print anything (caller handles output).
    """
    results = []

    try:
        client = _get_app()
    except Exception as e:
        results.append(
            GateResult("Server", "TestClient init", RESULT_FAIL, str(e))
        )
        return results

    # Always run
    results.extend(_gate_server_startup(client))
    results.extend(_gate_api_endpoints(client))
    results.extend(_gate_fstring_leaks(client))
    results.extend(_gate_spec_fidelity(client))

    if full:
        results.extend(_gate_spatial_audit())
        results.extend(_gate_data_pipeline())
        results.extend(_gate_code_graph())

    if not json_output:
        print("\n" + "=" * 60)
        print("  OBSERVECO GOLDEN GATE — Full Compliance Check")
        print("=" * 60)
        sections = set(r.section for r in results)
        for sec in sorted(sections):
            sec_results = [r for r in results if r.section == sec]
            passed = sum(1 for r in sec_results if r.status == RESULT_PASS)
            failed = sum(1 for r in sec_results if r.status == RESULT_FAIL)
            warned = sum(1 for r in sec_results if r.status == RESULT_WARN)
            skipped = sum(1 for r in sec_results if r.status == RESULT_SKIP)
            print(f"\n─── {sec} ({passed}✅ / {failed}❌ / {warned}⚠️ / {skipped}⏭️) ───")
            for r in sec_results:
                print(r)

        total = len(results)
        passed = sum(1 for r in results if r.status == RESULT_PASS)
        failed = sum(1 for r in results if r.status == RESULT_FAIL)
        warned = sum(1 for r in results if r.status == RESULT_WARN)
        pct = round(passed / total * 100) if total > 0 else 0
        print(f"\n{'=' * 60}")
        print(f"  TOTAL: {passed}/{total} passed ({pct}%) — {failed} fails, {warned} warnings")
        if failed > 0:
            print("  ❌ GATE FAILED — fix flagged items before shipping")
        elif warned > 0:
            print("  ⚠️  GATE PASSED WITH WARNINGS — verify flagged items")
        else:
            print("  ✅ GATE PASSED — all checks clean")
        print(f"{'=' * 60}\n")

    return results


if __name__ == "__main__":
    run_gate(full="--full" in sys.argv, json_output="--json" in sys.argv)
