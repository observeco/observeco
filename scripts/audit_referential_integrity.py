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
    # Reject stray template fragments: a Python f-string expression like
    # '/api/inbox/{_html_escape(item['id'])}' truncates at the inner quote,
    # leaving an unbalanced '{' that no {..} pass can resolve. That's template
    # source, not a URL — return '' so it can't become a false orphan/target.
    if "{" in path and path.count("{") != path.count("}"):
        return ""
    return path if path.startswith("/api") else ""


# A non-literal JS expression inside a fetch('...' + expr + '...') concat chain.
# Matches: + encodeURIComponent(agent), + data.subscription.id, + (t ? ... : '').
_EXPR = r"\+[^'\"]+?"  # everything up to the next literal string or the closing paren


def _reconstruct_fetch_url(inner: str) -> str:
    """Reconstruct a fetch() URL arg from its string-concatenation form.

    The arg may be a single literal ('/api/foo') or a chain
    ('/api/agent/' + expr + '/errors?days=' + expr). Non-literal JS expressions
    become <param>; string literals are kept verbatim. So:
      '/api/agent/' + expr + '/errors'  ->  /api/agent/<param>/errors
    which then matches the registered route /api/agent/{name}/errors.

    Returns '' if the chain does not begin with a literal /api prefix (so a
    ternary like ('/api/x' + (cond ? ...)) which produces garbage is rejected).
    """
    # Match a leading literal /api prefix, then + expr + literal+ ... segments.
    m = re.match(r"\s*['\"](/api/[^'\"]*)['\"]\s*(.*)$", inner)
    if not m:
        return ""
    out = [m.group(1)]
    rest = m.group(2)
    # rest looks like: + expr + '/suffix' + expr + '/more'
    for part in re.findall(r"\+([^+]*)", rest):
        part = part.strip()
        if part.startswith(("'", '"')) and part.endswith(("'", '"')) and len(part) >= 2:
            out.append(part[1:-1])  # literal string content
        elif part and part not in ("", ")", ","):
            out.append("<param>")
    result = "".join(out)
    # A real path param is always preceded by '/' (path segment). A <param> not
    # preceded by '/' is query-string garbage from a nested ternary
    # ('/api/x' + (t ? '?a=' + t : '')) — reject it so we don't emit noise.
    path_only = result.split("?")[0]
    if "<param>" in path_only and "/<param>" not in path_only:
        return ""
    return result


def _fetch_urls(text: str) -> set[str]:
    """All /api URLs referenced by fetch() including concat chains."""
    out: set[str] = set()
    # Match fetch( <arg> ) where <arg> may itself contain nested parens.
    # We capture up to the matching close paren heuristically: fetch( then
    # everything up to the first ', {' options object or the final ')'.
    for m in re.finditer(r"fetch\(\s*", text):
        start = m.end()
        # Find the arg: from start to the first comma at paren-depth 0 or final )
        depth = 0
        i = start
        while i < len(text):
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                if depth == 0:
                    break
                depth -= 1
            elif c == "," and depth == 0:
                break
            i += 1
        arg = text[start:i]
        path = _reconstruct_fetch_url(arg)
        if path and path.startswith("/api"):
            out.add(path)
    return out


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

    Scans templates + static JS + ALL python router files under src/observeco
    (server.py AND standalone router modules like discover/api.py, which carry
    inline HTML with hx-post/fetch/hx-get references). Omitting non-server router
    files made discover/*, garden/* etc. look orphaned when they're called from
    HTML those modules render.
    """
    out: set[str] = set()
    py_files = [SERVER] + sorted(ROOT.joinpath("src/observeco").rglob("*.py"))
    for p in _files(TEMPLATES, {".html"}) + _files(JS, {".js"}) + py_files:
        text = p.read_text()
        # fetch('/api/foo' + expr + '/bar') — reconstruct full concat chain
        # (handles plain '/api/foo' and concatenated forms; a naive first-literal
        # regex would truncate '/api/agent/' and miss the '/profile' suffix).
        for raw in _fetch_urls(text):
            key = _normalize_route_key(raw)
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
        # OR onclick="...htmx.ajax('POST', '/api/x', ...)" (the in-app action
        # pattern — both carry the auth header, so both are real references).
        for m in re.finditer(
            r"on(?:click|change|submit)=\"[^\"]*"
            r"(?:fetch\('([^'\"]+)'|htmx\.ajax\('(?:GET|POST|PUT|DELETE)'\s*,\s*'([^'\"]+)')",
            text,
        ):
            raw = m.group(1) or m.group(2)
            if not raw:
                continue
            # Reject Python f-string fragments: an inner quote in
            # '/api/inbox/{_html_escape(item['id'])}/restore' truncates the regex
            # at item[, leaving a stray '{' with no '}'. That's not a URL — it's
            # template source. (Direction 4's render-time pass captures the real
            # rendered value, so nothing is lost by skipping these here.)
            if "{" in raw and raw.count("{") != raw.count("}"):
                continue
            key = _normalize_route_key(raw)
            if key:
                out.add(key)
    return out


def direction3_orphaned_targets() -> list[str]:
    """fetch/htmx/form targets with no registered route."""
    routes = _registered_routes()
    targets = _referenced_targets()
    return sorted(t for t in targets if t not in routes)


# ── Direction 4: registered POST routes -> referenced anywhere ──────────────
def _orphaned_post_routes(post_routes: set[str], referenced: set[str]) -> list[str]:
    """Pure: given registered POST routes and all references, return the orphans.

    Extracted so the positive control can exercise the orphan-detection logic
    with a SYNTHETIC route set (a fixture owned by the test), instead of tying
    it to a real production route that then can't be deleted even if it should
    be. A reference may carry a CONCRETE id where the route has a <param>
    (e.g. /api/inbox/agent_dead::...::2026-08-04T12:35:35/split matches
    /api/inbox/{parent_id}/split) — collapse any reference that agrees with the
    route on every literal segment and differs only at a param position.
    """
    referenced_paths = set(referenced)
    # Routes that are exactly referenced (no param matching needed) are resolved.
    resolved = set(r for r in post_routes if r in referenced_paths)
    # Param-routes resolve if a concrete reference agrees on every literal segment
    # and differs only at a param position.
    for route in post_routes:
        if "<param>" not in route:
            continue
        route_segs = route.split("/")
        for ref in referenced_paths:
            ref_segs = ref.split("/")
            if len(ref_segs) != len(route_segs):
                continue
            if all(
                rs == "<param>" or rs == rl
                for rs, rl in zip(route_segs, ref_segs)
            ):
                resolved.add(route)
                break
    return sorted(r for r in post_routes if r not in resolved)


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
    # Include render-time references (the rendered HTML's fetch/htmx.ajax/hx-*
    # calls), not just static source — runtime/DB-generated actions (e.g. the
    # inbox's split/snooze/restore onclick built from stored actions) only appear
    # in rendered output, and would otherwise look orphaned.
    referenced = _referenced_targets()
    for body in _render_endpoints():
        for raw in re.findall(r"['\"]((?:/api)/[^'\"]+)['\"]", body):
            key = _normalize_route_key(raw)
            if key:
                referenced.add(key)
    return _orphaned_post_routes(post_routes, referenced)


# ── Direction 5: bare-API anchors -> navigation failures (RENDER-TIME) ───────
def _is_bare_api_anchor(tag: str) -> bool:
    """True if an <a> tag full-page-navigates to a token-protected /api/ route.

    A bare anchor (no hx-*, no fetch/htmx.ajax onclick) does a full-page load,
    which sends cookies only — it CANNOT send the X-ObserveCo-Token header, so
    it 401s. htmx/fetch-driven anchors carry the header and are fine.
    """
    if any(hx in tag for hx in ("hx-get", "hx-post", "hx-put", "hx-delete", "hx-target")):
        return False  # htmx-driven — carries the header
    if "onclick" in tag and ("htmx.ajax" in tag or "fetch(" in tag):
        return False  # JS-driven — carries the header
    return True


def _render_endpoints() -> list[str]:
    """Render the app's main HTML surfaces via TestClient and return their bodies.

    Category change vs static scanning: rather than teach the scanner about each
    HTML generation site (templates, server.py inline, runtime/DB-built actions
    from inbox/correlate.py), BOOT the app and hit the routes, then check the
    HTML that actually comes back. This catches every generation path at once —
    present and future — without knowing where any of them live. It's what would
    have caught the 57 DB-generated "View the window" dead links without needing
    a human to notice them on the page.
    """
    bodies: list[str] = []
    try:
        from fastapi.testclient import TestClient
        from observeco.dashboard.auth import init_auth
        from observeco.dashboard.server import app
        secret = init_auth(app)
        client = TestClient(app)
        hdr = {"X-ObserveCo-Token": secret}
        for path in ("/", "/api/inbox", "/api/inbox?filter=crit",
                     "/api/inbox?filter=watch", "/api/inbox?filter=insight",
                     "/api/inbox?filter=acked", "/api/fleet-summary",
                     "/api/agents", "/api/alerts", "/api/errors",
                     "/api/drift-summary", "/api/capability/page"):
            try:
                r = client.get(path, headers=hdr)
                if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
                    bodies.append(r.text)
            except Exception:
                continue
    except Exception:
        # Server can't boot (e.g. no DB) — fall back to static scan so the
        # direction still runs.
        for p in _files(TEMPLATES, {".html"}) + _files(JS, {".js"}) + [SERVER]:
            bodies.append(p.read_text())
    return bodies


def direction5_bare_api_anchors() -> list[str]:
    """Anchors in RENDERED HTML that navigate to a token-protected /api/ route.

    The dashboard authenticates /api/ routes with the X-ObserveCo-Token HEADER
    (auth.py). A plain <a href="/api/..."> does a full-page navigation, which
    sends cookies only — it CANNOT send that header, so it 401s. Any such anchor
    is a navigation failure (a "dead link" that resolves but dumps the user on a
    chrome-less 401 page), even though the route exists and is referenced.

    Checks the RENDERED HTML (app booted + routes hit), so runtime/DB-generated
    anchors are caught too — the class the static directions can't see.

    Excludes: anchors that are htmx/fetch-driven (they carry the header), and
    the AUTH_EXEMPT public routes (no token needed).
    """
    AUTH_EXEMPT = {
        "/api/billing/success", "/api/billing/cancel", "/api/billing/webhook",
        "/api/phase", "/api/discover/count",
    }
    bad: set[str] = set()
    for body in _render_endpoints():
        for m in re.finditer(r'<a\b[^>]*href="(/api/[^"]+)"[^>]*>', body):
            href = m.group(1).split("?")[0]
            if not _is_bare_api_anchor(m.group(0)):
                continue  # htmx/fetch-driven — carries the header
            if href in AUTH_EXEMPT or href.startswith("/api/licenses/"):
                continue
            if href.startswith("/api/"):
                bad.add(href)
    return sorted(bad)


# ── Report ───────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allowlist", type=str, default="", help="JSON file of allowed findings")
    args = ap.parse_args()

    allow: dict[str, set[str]] = {}
    if args.allowlist:
        raw = json.loads(Path(args.allowlist).read_text())
        for k, v in raw.items():
            # orphaned_post_routes is a TRIAGE QUEUE: entries are {route, note}
            # so it reads as a to-do ("not yet triaged"), not an absolution.
            # Extract just the route keys for set membership; a new orphan not
            # on the queue still fires. Other sections stay plain string lists.
            if v and isinstance(v[0], dict):
                allow[k] = {item["route"] for item in v}
            else:
                allow[k] = set(v)

    findings: dict[str, list[str]] = {
        "orphaned_css_classes": direction1_orphaned_classes(),
        "undefined_css_vars": direction2_undefined_vars(),
        "orphaned_route_targets": direction3_orphaned_targets(),
        "orphaned_post_routes": direction4_orphaned_post_routes(),
        "bare_api_anchors": direction5_bare_api_anchors(),
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
