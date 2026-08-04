#!/usr/bin/env python3
"""Referential-integrity audit for the ObserveCo dashboard.

Every reference must resolve to a definition, in both directions. This script
detects the class of defect observed repeatedly (four confirmed instances):
two halves that each pass their own check but were never checked against each
other — templates emitting classes with no CSS rules, CSS vars referenced but
never defined, JS calling routes that don't exist, and POST routes with no caller.

Four directions (one script, one report):

  1. classes emitted by templates    -> defined in CSS        (orphaned classes)
  2. CSS variables referenced         -> defined in :root      (latent --fg-3 bug)
  3. fetch/htmx targets               -> registered routes     (dead buttons)
  4. registered POST routes           -> referenced anywhere   (built, never surfaced)

Usage:
    python3 scripts/audit_referential_integrity.py
    python3 scripts/audit_referential_integrity.py --allowlist scripts/audit-allowlist.json

Exit 0 = clean (no findings beyond allowlist). Exit 1 = findings not on allowlist.

Notes on noise:
  - Dynamically constructed class names (e.g. `cls-{var}`) won't be caught; they
    must be allowlisted.
  - Utility classes (spacing, layout helpers) and deliberately unstyled semantic
    hooks must be allowlisted.
  - Don't chase zero. Get to a stable allowlist, then make new entries fail.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "src/observeco/dashboard/static/observeco-dashboard.css"
TEMPLATES = ROOT / "src/observeco/dashboard/templates"
JS = ROOT / "src/observeco/dashboard/static/js"
ROUTES = ROOT / "src/observeco/dashboard/routes"
SERVER = ROOT / "src/observeco/dashboard/server.py"
MOCKUPS = ROOT / "mockups"

# Files whose CSS variables reference the dashboard tokens (index_new loads the
# main stylesheet; inline styles reference tokens directly).
INCLUDE_EXT = {".html", ".js"}


def _files(root: Path, exts: set[str]) -> list[Path]:
    return [p for p in root.rglob("*") if p.suffix in exts and "node_modules" not in p.parts]


# ── Direction 1: classes emitted by templates -> defined in CSS ─────────────
def _class_names_in_text(text: str) -> set[str]:
    return set(re.findall(r'class="([^"]+)"', text))


# A valid CSS class token: starts with a letter/underscore, then letters,
# digits, underscore, or hyphen. Rejects Jinja fragments (btn{%), JS string
# concatenation tokens ((fail, 'red', 0, ?), and any non-identifier garbage.
_VALID_CLASS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def _classes_from_text(text: str) -> set[str]:
    """Flatten all class="" tokens into individual valid class names.

    Only static identifier tokens are kept. Jinja blocks ({% if x %}, {{ var }})
    embedded in a class attribute (class="btn{% if x %} ghost{% endif %}") are
    stripped before splitting, so their keywords (if/endif) don't leak through.
    JS string concatenation (class="val ' + cond + '") yields fragments that
    aren't identifiers and are rejected. This keeps the audit from drowning in
    extraction noise.
    """
    out: set[str] = set()
    for token in _class_names_in_text(text):
        # Strip Jinja statement/expression blocks entirely.
        token = re.sub(r"\{[%{][^}]*[%}]\}", " ", token)
        for c in token.split():
            if _VALID_CLASS_RE.match(c):
                out.add(c)
    return out


def _css_selectors(css_text: str) -> set[str]:
    """Extract simple class selectors defined in CSS (single-class rules)."""
    out: set[str] = set()
    # Match .foo and .foo.bar / #x .foo in selectors
    for m in re.finditer(r"\.([a-zA-Z][a-zA-Z0-9_-]*)", css_text):
        out.add(m.group(1))
    return out


def _all_css_text() -> list[str]:
    """Every CSS source: the global stylesheet + each template's inline <style>.

    SINGLE SOURCE OF TRUTH for 'what CSS exists'. Both the class check and the
    variable check must consume this — never maintain two independent notions of
    where CSS lives, or a third direction reintroduces the under-scan bug.
    """
    texts = [CSS.read_text()]
    for p in _files(TEMPLATES, {".html"}):
        for style_block in re.findall(r"<style>(.*?)</style>", p.read_text(), re.S):
            texts.append(style_block)
    return texts


def _all_defined_css_classes() -> set[str]:
    """Classes defined in the global stylesheet OR any template inline <style>."""
    defined: set[str] = set()
    for css in _all_css_text():
        defined |= _css_selectors(css)
    return defined


def direction1_orphaned_classes() -> list[str]:
    """Classes emitted in templates/JS but never defined in any stylesheet."""
    defined = _all_defined_css_classes()
    emitted: set[str] = set()
    for p in _files(TEMPLATES, {".html"}) + _files(JS, {".js"}):
        emitted.update(_classes_from_text(p.read_text()))
    return sorted(c for c in emitted if c not in defined)


# ── Direction 2: CSS vars referenced -> defined in :root ────────────────────
def _css_vars_referenced(text: str) -> set[str]:
    return set(re.findall(r"var\(--([a-zA-Z][a-zA-Z0-9_-]*)\)", text))


def _css_vars_defined() -> set[str]:
    """CSS variables defined across the SINGLE CSS source of truth.

    Scans the global stylesheet AND every template inline <style> (via
    _all_css_text), so template-local vars like --sec/--blue/--amber (defined
    in pathway.html's own <style>) are not misreported as undefined.
    """
    defined: set[str] = set()
    for css in _all_css_text():
        defined |= set(re.findall(r"--([a-zA-Z][a-zA-Z0-9_-]*)\s*:", css))
    return defined


def direction2_undefined_vars() -> list[str]:
    """CSS variables referenced anywhere but never defined in any stylesheet."""
    defined = _css_vars_defined()
    referenced: set[str] = set()
    # Templates + JS reference tokens in inline styles
    for p in _files(TEMPLATES, {".html"}) + _files(JS, {".js"}):
        referenced.update(_css_vars_referenced(p.read_text()))
    # CSS itself may reference vars
    for css in _all_css_text():
        referenced.update(_css_vars_referenced(css))
    return sorted(v for v in referenced if v not in defined)


# ── Direction 3: fetch/htmx targets -> registered routes ────────────────────
def _registered_routes() -> set[str]:
    """All concrete URL paths registered by FastAPI decorators.

    Scans every APIRouter in src/observeco (routes/ AND standalone packages
    like discover/), plus @app.* decorators in server.py. This is why the
    discover routes resolve: they live outside dashboard/routes/.
    """
    routes: set[str] = set()

    # Parse every APIRouter(prefix="X") + @router.*("path") across all of src.
    src_root = ROOT / "src/observeco"
    for mod in src_root.rglob("*.py"):
        text = mod.read_text()
        prefixes = re.findall(r'APIRouter\(prefix="([^"]+)"', text)
        prefix = prefixes[0] if prefixes else ""
        for method, path in re.findall(r'@router\.(get|post|put|delete)\("([^"]*)"', text):
            full = prefix + path
            full = re.sub(r"\{[^}]+\}", "<param>", full).rstrip("/")
            routes.add(full)

    # Parse server.py @app.get("/path")
    srv = SERVER.read_text()
    for method, path in re.findall(r'@app\.(get|post|put|delete)\("([^"]*)"', srv):
        full = re.sub(r"\{[^}]+\}", "<param>", path).rstrip("/")
        routes.add(full)
    return routes


def _referenced_targets() -> set[str]:
    """Concrete /api/... paths referenced by fetch(), htmx.ajax(), and hx-*.

    Only actual network calls count — NOT <script src>/<link href> asset
    references (which are not routes). Matches:
      fetch('/api/foo'), fetch('/api/foo?x=1')
      htmx.ajax('GET', '/api/foo', {...})
      hx-get="/api/foo" hx-post="/api/foo"
    """
    out: set[str] = set()
    for p in _files(TEMPLATES, {".html"}) + _files(JS, {".js"}):
        text = p.read_text()
        # fetch('...') — capture the first string arg
        for m in re.finditer(r"fetch\(\s*['\"]([^'\"]+)['\"]", text):
            path = m.group(1).split("?")[0].rstrip("/")
            path = re.sub(r"\{[^}]+\}", "<param>", path)
            if path.startswith("/api"):
                out.add(path)
        # htmx.ajax('GET', '...') — capture the second string arg
        for m in re.finditer(r"htmx\.ajax\(\s*['\"](?:GET|POST|PUT|DELETE)['\"]\s*,\s*['\"]([^'\"]+)['\"]", text):
            path = m.group(1).split("?")[0].rstrip("/")
            path = re.sub(r"\{[^}]+\}", "<param>", path)
            if path.startswith("/api"):
                out.add(path)
        # hx-get="/api/x" / hx-post="/api/x" — capture the quoted path
        for m in re.finditer(r'hx-(?:get|post|put|delete)="([^"]+)"', text):
            path = m.group(1).split("?")[0].rstrip("/")
            path = re.sub(r"\{[^}]+\}", "<param>", path)
            if path.startswith("/api"):
                out.add(path)
    return out


def direction3_orphaned_targets() -> list[str]:
    """fetch/htmx targets with no registered route."""
    routes = _registered_routes()
    targets = _referenced_targets()
    # A target resolves if a route equals it, or a route is its prefix+param
    return sorted(t for t in targets if not _route_matches(t, routes))


def _route_matches(target: str, routes: set[str]) -> bool:
    if target in routes:
        return True
    # target like /api/fleet/agents matches /api/fleet/agents (exact handled).
    # target with a concrete value matching a <param> route: /api/inbox/X/ack
    # matches /api/inbox/<param>/ack
    parts = target.split("/")
    for route in routes:
        rparts = route.split("/")
        if len(rparts) != len(parts):
            continue
        if all(rp == pp or rp == "<param>" for rp, pp in zip(rparts, parts)):
            return True
    return False


# ── Direction 4: registered POST routes -> referenced anywhere ──────────────
def direction4_orphaned_post_routes() -> list[str]:
    """Registered POST routes with no reference in templates or JS."""
    # Collect registered POST routes (scan all of src/observeco, not just routes/)
    post_routes: set[str] = set()
    src_root = ROOT / "src/observeco"
    for mod in src_root.rglob("*.py"):
        text = mod.read_text()
        prefixes = re.findall(r'APIRouter\(prefix="([^"]+)"', text)
        prefix = prefixes[0] if prefixes else ""
        for method, path in re.findall(r'@router\.(get|post|put|delete)\("([^"]*)"', text):
            if method != "post":
                continue
            full = prefix + path
            full = re.sub(r"\{[^}]+\}", "<param>", full).rstrip("/")
            post_routes.add(full)
    srv = SERVER.read_text()
    for method, path in re.findall(r'@app\.(post)\("([^"]*)"', srv):
        full = re.sub(r"\{[^}]+\}", "<param>", path).rstrip("/")
        post_routes.add(full)

    # Gather all text that could reference a route (templates, JS, inline onclick)
    reference_text = ""
    for p in _files(TEMPLATES, {".html"}) + _files(JS, {".js"}):
        reference_text += p.read_text()

    orphaned = []
    for route in sorted(post_routes):
        # Reconstruct the literal prefix (without <param>) to grep for
        literal = route.replace("<param>", "{X}")
        # Check if any concrete form of this route is referenced
        # e.g. /api/inbox/{item_id}/ack -> look for "/api/inbox/" and "ack"
        if not _route_referenced(route, reference_text):
            orphaned.append(route)
    return orphaned


def _route_referenced(route: str, text: str) -> bool:
    """Heuristic: a route is referenced if its static prefix appears in text."""
    # Take the part before the first <param> as the static prefix
    parts = route.split("<param>")[0]
    if parts and parts in text:
        return True
    return False


# ── Report ───────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allowlist", type=str, default="", help="JSON file of allowed findings")
    args = ap.parse_args()

    allow: dict[str, set[str]] = {}
    if args.allowlist:
        raw = json.loads(Path(args.allowlist).read_text())
        allow = {k: set(v) for k, v in raw.items()}

    findings: dict[str, list[str]] = {
        "orphaned_css_classes": direction1_orphaned_classes(),
        "undefined_css_vars": direction2_undefined_vars(),
        "orphaned_route_targets": direction3_orphaned_targets(),
        "orphaned_post_routes": direction4_orphaned_post_routes(),
    }

    print("=== Referential Integrity Audit ===")
    new_findings = 0
    for name, items in findings.items():
        unallowed = [i for i in items if i not in allow.get(name, set())]
        print(f"\n[{name}] {len(items)} total, {len(unallowed)} NOT allowed")
        for i in sorted(unallowed)[:30]:
            print(f"  - {i}")
        new_findings += len(unallowed)

    print(f"\n{'PASS' if new_findings == 0 else f'FAIL ({new_findings} unallowlisted findings)'}")
    return 0 if new_findings == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
