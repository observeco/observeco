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
def _normalize_route_key(path: str) -> str:
    """Normalize a URL path to a comparison key.

    Handles three shapes so a reference and a route compare equal:
      - '/api/fleet/canary-card/{agent_name}'  (route)  -> /api/fleet/canary-card/<param>
      - '/api/fleet/canary-card/agent'          (literal)-> /api/fleet/canary-card/<param>
      - '/api/fleet/canary-card/' + concat      (JS ref) -> /api/fleet/canary-card/<param>
    A trailing slash on a reference means a param continues via string concat,
    so append <param>. Strips query strings. Returns '' if not an API path.
    """
    path = path.split("?")[0]
    trailing_concat = path.endswith("/")  # param continues via JS concat
    path = path.rstrip("/")
    # Jinja params ({{ aname }}) first — must not be eaten by the {..} pass.
    path = re.sub(r"\{\{[^}]+\}\}", "<param>", path)
    path = re.sub(r"\{[^}]+\}", "<param>", path)
    if trailing_concat:
        path += "/<param>"
    return path if path.startswith("/api") else ""


def _registered_routes() -> set[str]:
    """All normalized URL path keys registered by FastAPI decorators.

    Scans every APIRouter in src/observeco (routes/ AND standalone packages
    like discover/), plus @app.* decorators in server.py.
    """
    routes: set[str] = set()
    src_root = ROOT / "src/observeco"
    for mod in src_root.rglob("*.py"):
        text = mod.read_text()
        prefixes = re.findall(r'APIRouter\(prefix="([^"]+)"', text)
        prefix = prefixes[0] if prefixes else ""
        for method, path in re.findall(r'@router\.(get|post|put|delete)\("([^"]*)"', text):
            key = _normalize_route_key(prefix + path)
            if key:
                routes.add(key)
    srv = SERVER.read_text()
    for method, path in re.findall(r'@app\.(get|post|put|delete)\("([^"]*)"', srv):
        key = _normalize_route_key(path)
        if key:
            routes.add(key)
    return routes


def _referenced_targets() -> set[str]:
    """API paths referenced by any network call pattern.

    Matches fetch(), htmx.ajax(), hx-{get,post,put,delete}, form action=,
    and onclick/JS string references. Method is NOT required — we ask "is this
    route reachable at all," not "with the right verb," so dropping the method
    requirement removes a whole class of miss. Returns normalized route keys.
    """
    out: set[str] = set()
    for p in _files(TEMPLATES, {".html"}) + _files(JS, {".js"}):
        text = p.read_text()
        # fetch('/api/foo') — URL is the first string arg, method agnostic
        for m in re.finditer(r"fetch\(\s*['\"]([^'\"]+)['\"]", text):
            key = _normalize_route_key(m.group(1))
            if key:
                out.add(key)
        # htmx.ajax('GET', '/api/foo', ...) — second string arg
        for m in re.finditer(r"htmx\.ajax\(\s*['\"][^'\"]+['\"]\s*,\s*['\"]([^'\"]+)['\"]", text):
            key = _normalize_route_key(m.group(1))
            if key:
                out.add(key)
        # hx-get="/api/x" hx-post="/api/x"
        for m in re.finditer(r'hx-(?:get|post|put|delete)="([^"]+)"', text):
            key = _normalize_route_key(m.group(1))
            if key:
                out.add(key)
        # form action="/api/x"
        for m in re.finditer(r'<form[^>]*action="([^"]+)"', text):
            key = _normalize_route_key(m.group(1))
            if key:
                out.add(key)
        # onclick / inline handlers calling a route: onclick="fetch('/api/x')"
        for m in re.finditer(r"on(?:click|change|submit)=\"[^\"]*fetch\(['\"]([^'\"]+)['\"]", text):
            key = _normalize_route_key(m.group(1))
            if key:
                out.add(key)
    return out


def direction3_orphaned_targets() -> list[str]:
    """fetch/htmx/form targets with no registered route."""
    routes = _registered_routes()
    targets = _referenced_targets()
    return sorted(t for t in targets if t not in routes)


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
            key = _normalize_route_key(prefix + path)
            if key:
                post_routes.add(key)
    srv = SERVER.read_text()
    for method, path in re.findall(r'@app\.(post)\("([^"]*)"', srv):
        key = _normalize_route_key(path)
        if key:
            post_routes.add(key)

    # A POST route is orphaned if NO reference (any verb, any pattern) reaches it.
    referenced = _referenced_targets()
    orphaned = sorted(r for r in post_routes if r not in referenced)
    return orphaned


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
