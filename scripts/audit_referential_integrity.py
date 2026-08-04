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


def _classes_from_text(text: str) -> set[str]:
    """Flatten all class="" tokens into individual class names."""
    out: set[str] = set()
    for token in _class_names_in_text(text):
        out.update(token.split())
    return out


def _css_selectors(css_text: str) -> set[str]:
    """Extract simple class selectors defined in CSS (single-class rules)."""
    out: set[str] = set()
    # Match .foo and .foo.bar / #x .foo in selectors
    for m in re.finditer(r"\.([a-zA-Z][a-zA-Z0-9_-]*)", css_text):
        out.add(m.group(1))
    return out


def direction1_orphaned_classes() -> list[str]:
    """Classes emitted in templates/JS but never defined in CSS."""
    css = CSS.read_text()
    defined = _css_selectors(css)
    emitted: set[str] = set()
    for p in _files(TEMPLATES, {".html"}) + _files(JS, {".js"}):
        emitted.update(_classes_from_text(p.read_text()))
    # Inline style attributes aren't classes; strip obvious utility/state hooks
    return sorted(c for c in emitted if c not in defined)


# ── Direction 2: CSS vars referenced -> defined in :root ────────────────────
def _css_vars_referenced(text: str) -> set[str]:
    return set(re.findall(r"var\(--([a-zA-Z][a-zA-Z0-9_-]*)\)", text))


def _css_vars_defined(css_text: str) -> set[str]:
    return set(re.findall(r"^\s*--([a-zA-Z][a-zA-Z0-9_-]*)\s*:", css_text, re.M))


def direction2_undefined_vars() -> list[str]:
    """CSS variables referenced anywhere but never defined in :root."""
    css = CSS.read_text()
    defined = _css_vars_defined(css)
    referenced: set[str] = set()
    # Templates + JS reference tokens in inline styles
    for p in _files(TEMPLATES, {".html"}) + _files(JS, {".js"}):
        referenced.update(_css_vars_referenced(p.read_text()))
    # CSS itself may reference vars
    referenced.update(_css_vars_referenced(css))
    return sorted(v for v in referenced if v not in defined)


# ── Direction 3: fetch/htmx targets -> registered routes ────────────────────
def _registered_routes() -> set[str]:
    """All concrete URL paths registered by FastAPI decorators."""
    routes: set[str] = set()

    # Parse each route module: APIRouter(prefix="X") + @router.get("/path")
    for mod in ROUTES.glob("*.py"):
        text = mod.read_text()
        prefixes = re.findall(r'APIRouter\(prefix="([^"]+)"', text)
        prefix = prefixes[0] if prefixes else ""
        for method, path in re.findall(r'@router\.(get|post|put|delete)\("([^"]*)"', text):
            full = prefix + path
            # Replace path params {item_id} -> wildcard; strip trailing /
            full = re.sub(r"\{[^}]+\}", "<param>", full).rstrip("/")
            routes.add(full)

    # Parse server.py @app.get("/path")
    srv = SERVER.read_text()
    for method, path in re.findall(r'@app\.(get|post|put|delete)\("([^"]*)"', srv):
        full = re.sub(r"\{[^}]+\}", "<param>", path).rstrip("/")
        routes.add(full)
    return routes


def _referenced_targets() -> set[str]:
    """Concrete /api/... paths referenced by fetch() and htmx.ajax() in JS+templates."""
    out: set[str] = set()
    for p in _files(TEMPLATES, {".html"}) + _files(JS, {".js"}):
        text = p.read_text()
        for m in re.findall(r"['\"]((?:/api|/)[a-zA-Z0-9_/\-{}?&=.;:]+)['\"]", text):
            path = m.split("?")[0].rstrip("/")
            # Drop query strings and template vars
            path = re.sub(r"\{[^}]+\}", "<param>", path).rstrip("/")
            if path.startswith("/api") or path.startswith("/static"):
                out.add(path)
        # hx-get="/api/x"
        for m in re.findall(r'hx-(?:get|post|put)="([^"]+)"', text):
            path = m.split("?")[0].rstrip("/")
            path = re.sub(r"\{[^}]+\}", "<param>", path).rstrip("/")
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
    # Collect registered POST routes
    post_routes: set[str] = set()
    for mod in ROUTES.glob("*.py"):
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

    allow = set()
    if args.allowlist:
        allow = set(json.loads(Path(args.allowlist).read_text()))

    findings: dict[str, list[str]] = {
        "orphaned_css_classes": direction1_orphaned_classes(),
        "undefined_css_vars": direction2_undefined_vars(),
        "orphaned_route_targets": direction3_orphaned_targets(),
        "orphaned_post_routes": direction4_orphaned_post_routes(),
    }

    print("=== Referential Integrity Audit ===")
    new_findings = 0
    for name, items in findings.items():
        unallowed = [i for i in items if i not in allow]
        print(f"\n[{name}] {len(items)} total, {len(unallowed)} NOT allowed")
        for i in sorted(unallowed)[:30]:
            print(f"  - {i}")
        new_findings += len(unallowed)

    print(f"\n{'PASS' if new_findings == 0 else f'FAIL ({new_findings} unallowlisted findings)'}")
    return 0 if new_findings == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
