"""Import-boundary test — feature modules must not import OS/runtime specifics.

Per obs-spec-024 §2 Principle 1:
  Only the probe imports OS/runtime specifics.
  Feature modules must not import os.path resolution, lsof, psutil,
  yaml config loaders, or socket/port logic.

This test is enforced in CI to prevent capability leakage into feature modules.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

FEATURES_DIR = pathlib.Path(__file__).parent.parent.parent / "src" / "observeco" / "features"

FORBIDDEN_IMPORTS = {
    "psutil",
    "yaml",
    "socket",
}

# os.path resolution — allowed to import os, but not call os.path.exists/expanduser etc.
# We check at the import level: importing 'socket' or 'psutil' directly is forbidden.
# A feature module importing 'os' for os.environ (safe) is allowed, but
# importing 'psutil', 'yaml', or 'socket' is a boundary violation.


def _collect_imports(source: str) -> set[str]:
    """Return the set of top-level module names imported in a Python source string."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def _feature_files() -> list[pathlib.Path]:
    if not FEATURES_DIR.exists():
        return []
    return [f for f in FEATURES_DIR.glob("*.py") if f.name != "__init__.py"]


@pytest.mark.parametrize("feature_file", _feature_files(), ids=lambda f: f.name)
def test_no_forbidden_imports(feature_file: pathlib.Path):
    """Feature files must not import psutil, yaml, or socket."""
    source = feature_file.read_text()
    imported = _collect_imports(source)
    violations = imported & FORBIDDEN_IMPORTS
    assert not violations, (
        f"{feature_file.name} imports forbidden modules: {violations}. "
        "Feature modules must read from EnvSnapshot only — move OS calls to probe.py."
    )


def test_features_dir_exists():
    """The features directory must exist and contain at least one feature file."""
    assert FEATURES_DIR.exists(), f"features dir missing: {FEATURES_DIR}"
    files = _feature_files()
    assert len(files) >= 1, "No feature files found"


def test_cost_tracking_no_os_path_resolution():
    """cost_tracking.py must not resolve paths — that's the probe's job."""
    cost_file = FEATURES_DIR / "cost_tracking.py"
    assert cost_file.exists()
    source = cost_file.read_text()
    # Forbidden: os.path.expanduser, os.path.realpath, os.path.exists
    assert "expanduser" not in source, "cost_tracking must not call os.path.expanduser"
    assert "realpath" not in source, "cost_tracking must not call os.path.realpath"


def test_tool_call_tracking_no_os_path_resolution():
    """tool_call_tracking.py must not resolve paths — that's the probe's job."""
    tc_file = FEATURES_DIR / "tool_call_tracking.py"
    assert tc_file.exists()
    source = tc_file.read_text()
    assert "expanduser" not in source
    assert "realpath" not in source
