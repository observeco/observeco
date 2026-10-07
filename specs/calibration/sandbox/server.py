#!/usr/bin/env python3
"""OBSERVECO SANDBOX — a place to submit a business and read the real report.

WHY THIS EXISTS
    Sean: "Let's do something like a sandbox where it is available in the sandbox
    website for me to test? We still need a CRM to get email addresses as well."

    Before this, the only way to see a report was to run scripts by hand against a
    hand-built corpus file. Nothing clicked end-to-end. This is the click.

WHAT IT IS — AND WHAT IT IS NOT
    NOT a mock. Every submission goes through the REAL pipeline, in the REAL order:
        pre-flight gate  ->  (optional) competitor scan  ->  Jev model call
        ->  composite computed IN CODE  ->  report renderer
    It imports run_jev / preflight_gate / generate_report directly, so a sandbox
    result and a production result cannot drift: there is one implementation.

    It IS a sandbox in three specific senses, each of which must be removed before
    this is a product:
      1. NO captcha, NO confirmation gate, NO spend ceiling. Section 3.7's open relay
         is fully present here. It binds to loopback and is single-user by design.
      2. It runs on the operator's machine, synchronously, with no queue.
      3. The CRM is a local SQLite file, not the system of record (spec 7.x).

THE CRM — the second thing Sean asked for
    Every submission stores the email address, the business, the band and the full
    report text in `sandbox.db`. That is the minimum a lead engine needs to prove it
    can capture a lead, and it is deliberately the ONLY thing the CRM does — no
    sequences, no scoring of leads, no vendor. It answers one question: does an
    address actually arrive, attached to a report that actually exists?

⚠ THE EGRESS RULE IS HONOURED. run_jev.build_state already excludes name/email/phone
from the model payload (spec 5.7), so the address is captured here and never leaves.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAL = HERE.parent                      # specs/calibration — the real pipeline
sys.path.insert(0, str(CAL))

from fastapi import FastAPI, Form, Request                    # noqa: E402
from fastapi.middleware.cors import CORSMiddleware             # noqa: E402
from fastapi.responses import HTMLResponse, RedirectResponse   # noqa: E402

DB = HERE / "sandbox.db"
RUNS = HERE / "runs"

# ── the real pipeline, imported not reimplemented ────────────────────────────
import run_jev                                                # noqa: E402
from preflight_gate import evaluate as preflight              # noqa: E402
from generate_report import render as render_report           # noqa: E402
from rubric_gate import require_promoted                      # noqa: E402
import confirmation_gate as gate                              # noqa: E402  (spec 3.7)
from fastapi import Query                                     # noqa: E402

RUBRIC = CAL / "rubric.json"
app = FastAPI(title="ObserveCo sandbox")
# ⚠ CORS IS LOAD-BEARING, NOT DECORATION. When this page is embedded, the parent may
# sandbox the iframe WITHOUT `allow-same-origin`, which gives the document an opaque
# origin — every request is then treated as cross-origin and fails without these
# headers. See the submit-page note below for the whole story.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"],
)


# ── CRM ──────────────────────────────────────────────────────────────────────
def db() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT, email TEXT, business_name TEXT, category TEXT,
        band TEXT, composite REAL, rubric_version TEXT, model_id TEXT,
        outcome TEXT, report TEXT, payload TEXT)""")
    return c


def save(**kw) -> int:
    c = db()
    cur = c.execute(
        "INSERT INTO submissions (created_at,email,business_name,category,band,"
        "composite,rubric_version,model_id,outcome,report,payload) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"),
         kw.get("email"), kw.get("business_name"), kw.get("category"),
         kw.get("band"), kw.get("composite"), kw.get("rubric_version"),
         kw.get("model_id"), kw.get("outcome"), kw.get("report"),
         json.dumps(kw.get("payload") or {})))
    c.commit()
    i = cur.lastrowid or 0
    c.close()
    return int(i)


# ── what a submission from the form looks like ───────────────────────────────
def extract_url(*texts: str) -> str:
    """Pull a URL out of free-text answers.

    ⚠ WHY THIS EXISTS. A small business that has NOT formulated a positioning statement --
    exactly the target segment D3 names -- will reasonably answer "why should I choose
    you?" with its own website. Measured on a real submission: steegeXP answered
    `https://steegexp.com/` and `"I want you to find out"`. Treating that as prose throws
    away the single most useful input the submission contains.
    """
    import re
    for t in texts:
        if not t:
            continue
        m = re.search(r"(?:https?://)?((?:[\w-]+\.)+[a-z]{2,}(?:/[^\s]*)?)", t, re.I)
        if m and "." in m.group(1):
            host = m.group(1)
            return host if host.startswith("http") else "https://" + host
    return ""


def payload_from_form(f: dict) -> dict:
    """Build the pipeline payload from the sandbox form.

    Field names match the real corpus contract, so a sandbox submission and a
    corpus case are the SAME shape. `customer_description` is the one addition:
    section 3.10 needs a customer description to drive demand reach and mental
    advantage, and NO field collects it — so it is collected here, flagged, so the
    consequence can be seen rather than described.
    """
    comps = [c.strip() for c in (f.get("competitors_named") or "").split(",") if c.strip()]
    form = {
        "business_name": f.get("business_name", ""),
        "role": f.get("role", ""),
        "company_size_band": f.get("company_size_band", "10-500"),
        "city": f.get("city") or "Singapore",
        "category": f.get("category", ""),
        "positioning_sentence": f.get("positioning_sentence", ""),
        "differentiator": f.get("differentiator", "") or f.get("positioning_sentence", ""),
        "undercut_on": f.get("undercut_on", ""),
        "your_price_point": f.get("your_price_point", ""),
        "their_price_point": f.get("their_price_point", ""),
        "competitors_named_count": str(len(comps)) if comps else "",
    }
    # the submitter's own site, if the free text carries one. This is ENRICHMENT and is
    # not the same thing as a positioning claim -- build_state sends it to the model as
    # supplied evidence, and the scan uses it as a seed.
    # the explicit field wins; otherwise look for a URL pasted into free text, which is
    # what a business without a positioning statement actually does. Then NORMALISE —
    # a bare "yourbusiness.com" typed into the field has no scheme and would not fetch.
    site = f.get("website") or extract_url(f.get("positioning_sentence", ""),
                                           f.get("differentiator", ""))
    if site:
        site = site.strip()
        if not site.startswith(("http://", "https://")):
            site = "https://" + site.lstrip("/")
        form["website"] = site
    # ⚠ collected but NOT scored by the current rubric — flagged in the UI.
    if f.get("customer_description"):
        form["customer_description"] = f["customer_description"]
    p = {"_meta": {"case": f.get("case_key") or f.get("business_name", "submission").lower(),
                   "business": f.get("business_name", ""),
                   "purpose": "SANDBOX submission"},
         "form": form,
         "competitors_named": comps}
    # ⚠⚠ THE OWNER'S OWN RIVAL WEBSITES, if they supplied them (6.7.13a/6.7.14). Passed straight
    # through: matched to rivals by name in rival_reads(), and taken on the OWNER'S assertion rather
    # than re-derived, because re-deriving is exactly what five failed rules tried to do.
    if f.get("competitor_urls"):
        p["competitor_urls"] = f["competitor_urls"]
    if comps:
        p["derived_competitive_set"] = build_set_from_named(comps)
    return p


def build_set_from_named(comps: list[str]) -> dict:
    """Turn the SUBMITTER'S OWN competitor list into the set the rubric consumes.

    ⚠ THIS IS THE PRODUCTION GAP, FILLED FOR THE SANDBOX. `competitor_scan.to_
    competitive_set()` only accepts a WEB SCAN, which is the part that returns an
    unstable 5/2/0 occupants. Production will hold the owner's list and nothing
    converts it, so PS stays capped at 3 for no good reason.

    The honest caveat is carried INSIDE the set: an owner-named rival is
    EVIDENCE-UNEQUAL to a researched one, and the tier says so rather than
    pretending the two are the same.
    """
    return {
        "_derivation_method": "SUBMITTER-NAMED competitors (sandbox). Not independently researched.",
        "tier_1_direct": {
            "members": comps,
            "why": "Named by the business itself as direct rivals.",
            "caveat": ("⚠ These occupants were NAMED BY THE SUBMITTER, not independently "
                       "researched. Treat each as a rival whose claim you may reason about, "
                       "but do not assume the list is complete or that any rival's claim is "
                       "verified — the owner names who they compete with, not what those "
                       "rivals own."),
        },
    }


# ── the pipeline, in the real order ──────────────────────────────────────────
def run_submission(payload: dict, do_scan: bool) -> dict:
    require_promoted(RUBRIC)
    rubric = json.loads(RUBRIC.read_text())
    out = {"scan_verdict": None, "flags": []}

    # 1. PRE-FLIGHT — before any token spend (spec 3.11)
    pf = preflight(payload, scan_available=do_scan)
    out["flags"] = [f for f in pf.get("flags", []) if not f.startswith("FORM GAP")]
    if pf["outcome"] != "REPORT":
        out["outcome"] = "REFUSED"
        out["refusal"] = pf
        return out

    # 2. THE WEB RESEARCH PASS (spec 4.6, via the web-search-scraping-protocol).
    #
    # ⚠ WHAT WAS WRONG BEFORE THIS. The scan ran ONLY when the submission named no
    # competitors, and it was seeded with NOTHING (run_jev passes `[]`). So:
    #   - a submission that named even one rival SKIPPED research entirely and scored
    #     against the owner's own list, which build_state itself labels "the OWNER'S
    #     PERCEPTION, which is expected to be incomplete";
    #   - and `scan(seed_urls=...)` — ALREADY BUILT — was always handed an empty list,
    #     so the submitter's own website, the richest input in the submission, was never
    #     fetched.
    # Measured on a real submission: steegeXP pasted its URL as its positioning answer,
    # named one rival, and the tool skipped research, ignored the site, and returned a
    # confident "NOT VIABLE" off a URL and a one-name competitor list.
    #
    # Sean: "you did not execute the web search protocol at all. Didn't we spec out that
    # if a website is provided, we would search the web and do a competitive analysis?"
    # He is right, and the fix is not new capability — it is pointing the existing
    # capability at the submitter.
    # ⚠⚠ OWNER-NAMED RIVALS ARE ALWAYS WORTH READING, INDEPENDENT OF THE SCAN SWITCH.
    # Measured on C5-saladshop, which has NO website field: with `do_scan` off and no website,
    # `do_research` was False -- so the tool NEVER LOOKED AT THE FIVE RIVALS THE OWNER NAMED.
    # No rival_reads call, no section in the report explaining it, nothing. The submission named
    # SaladStop!, Stuff'd, Supergreen, Six Hands and OMNIVORE and the report never mentioned them.
    # The switch controls the expensive CATEGORY scan; reading the owner's own names is one fetch
    # each and is the cheapest evidence this product has. It must not be gated behind it.
    _named = payload.get("competitors_named") or []
    # ⚠⚠ OWNER-SUPPLIED RIVAL URLS (spec 6.7.13a/6.7.14). A dict name -> url, matched case-insensitively.
    # This is the fix that restores the competitive read WITHOUT a model call: measured 1/4 -> 4/4 on
    # Aurora. It asks the owner for a FACT they already hold, not a judgement.
    _kurls = {}
    try:
        import re as _re
        _u = (payload.get("competitor_urls") or "").strip()
        for _tok in [t.strip() for t in _re.split(r"[,\n;]+", _u) if t.strip()]:
            if "." not in _tok:
                continue
            if not _tok.lower().startswith("http"):
                _tok = "https://" + _tok.lstrip("/")
            _kurls[_tok.split("//")[-1].split("/")[0].split(".")[0].lower()] = _tok
    except Exception:
        _kurls = {}
    do_research = do_scan or bool((payload.get("form") or {}).get("website")) or bool(_named)
    if do_research:
        try:
            from competitor_scan import scan as _scan, to_competitive_set as _tocs
            form = payload.get("form") or {}
            seeds = [form["website"]] if form.get("website") else []
            res = _scan((form.get("category") or "").strip(),
                        (form.get("city") or "Singapore").strip(),
                        seeds, per_url_timeout=20)
            verdict = (res.get("_meta") or {}).get("verdict", "")
            # Only ADOPT a researched set over the owner's list when the research actually
            # produced something. A failed scan must not replace a real (if thin) list with
            # an empty one -- §4.6's honest-failure rule.
            if "SCAN FAILED" not in verdict and "SEARCH UNAVAILABLE" not in verdict:
                # ⚠ PASS THE OWNER'S NAMED RIVALS IN. They are the PRIMARY set -- the scraped
                # occupant list is a proven negative result (see extract_occupants in
                # competitor_scan.py), while the owner's names are incomplete but CORRECT.
                # 6.7.6: read the OWNER-NAMED rivals' own sites, so the report can answer
                # "does a named rival already own your claim?" instead of asserting it cannot.
                # Costs one search + up to 6 fetches, and ONLY when the owner named rivals.
                _rr = []
                _names = payload.get("competitors_named") or []
                if _names:
                    try:
                        from competitor_scan import rival_reads as _rrf
                        # ⚠ use the SAME market string the scan used -- `market` is not a
                        # name in this scope (the scan call builds it inline from city), and a
                        # NameError here would be swallowed by the except below and silently
                        # skip the rival read entirely.
                        _mk = (form.get("city") or "Singapore").strip()
                        # ⚠⚠ PASS THE CATEGORY -- WITHOUT IT THE IDENTITY GATE IS DEAD CODE.
                        # `category` was defaulted to "" and never supplied, so:
                        #   (a) `_category_corroborates` returned True for EVERY page (nothing to
                        #       check against), i.e. the §6.7.9 optician guard never ran in the
                        #       product despite being built and tested; and
                        #   (b) the category-augmented search query never fired either.
                        # Found by grepping the production call site after measuring the fixes on a
                        # path the product does not take. Same failure class as the guard that
                        # silently never fired (underscores vs space) recorded in 6.7.4.
                        _cat = (form.get("category") or "").strip()
                        _rr = _rrf(_names, _mk, per_url_timeout=15, category=_cat,
                                   known=_kurls)
                    except Exception as _e:      # never let this break a submission
                        # ⚠⚠ A SECOND SILENT SWALLOW, FOUND BY FALSIFYING THE FIRST (spec 6.7.16e).
                        # This handler printed to STDOUT -- which nobody reads -- and continued with an
                        # empty rival list, so the report looked as though it had found nothing. It is
                        # the same defect as the outer handler, one level down: measured while
                        # re-injecting the §6.7.16 TypeError, which this branch caught before the
                        # outer one could classify it.
                        # ⚠ A code error is named and surfaced; a transport error degrades honestly.
                        import traceback as _tb
                        _BUGS = (TypeError, KeyError, IndexError, NameError, AttributeError,
                                 UnboundLocalError, SyntaxError, IndentationError, ValueError)
                        if isinstance(_e, _BUGS):
                            print("⚠⚠ INTERNAL BUG in rival_reads (NOT a limit):", file=sys.stderr)
                            _tb.print_exc()
                            out["flags"] = (out.get("flags") or []) + [
                                f"INTERNAL BUG in rival_reads: {type(_e).__name__}: {_e}"]
                            out["internal_bug"] = f"{type(_e).__name__}: {_e}"
                        else:
                            print("rival_reads failed:", _e, file=sys.stderr)
                cs = _tocs(res, owner_named=_names, rival_pages=_rr)
                # ⚠ THE SUBMITTER'S OWN SITE IS EVIDENCE, AND IT WAS BEING THROWN AWAY.
                # The scan fetches the seed URL and stores `claim` and `excerpt` on the
                # capture — then to_competitive_set() keeps only the derived OCCUPANT
                # names and drops the page content. Measured: steegexp.com captured OK
                # and its content never reached the model.
                # When the seed IS the submitter's own site, that page is the single most
                # relevant evidence in the whole submission, so it is carried into the
                # set explicitly and labelled as the business's OWN stated position —
                # evidence-unequal to a researched rival, and said so.
                if seeds:
                    mine = next((c for c in (res.get("captures") or [])
                                 if c.get("capture_status") == "ok"
                                 and seeds[0].split("//")[-1].split("/")[0]
                                     in (c.get("url") or "")), None)
                    if mine:
                        cs["tier_0_own_stated_position"] = {
                            "members": [mine.get("url") or seeds[0]],
                            "why": ("THE BUSINESS'S OWN SITE, read directly. This is what "
                                    "they say about themselves in public."),
                            "claim": mine.get("claim"),
                            "excerpt": mine.get("excerpt"),
                            "caveat": ("⚠ This is the business's OWN public claim, not an "
                                       "independent finding. Treat it as evidence of what "
                                       "they SAY, and judge whether a rival could say the "
                                       "same thing."),
                        }
                payload["derived_competitive_set"] = cs
                payload["_research"] = {"seeded_with": seeds, "verdict": verdict}
                out["scan_verdict"] = (f"researched the web"
                                       + (f", starting from {seeds[0]}" if seeds else "")
                                       + f" — {verdict}")
            else:
                payload["_research"] = {"seeded_with": seeds, "verdict": verdict}
                out["scan_verdict"] = (f"the web research did not complete ({verdict}) — "
                                       "your position is scored against the rivals you named")
        except Exception as exc:
            # ⚠⚠ A BUG MUST NOT WEAR THE SAME MASK AS A NETWORK FAILURE (spec 6.7.16e).
            #
            # WHAT WENT WRONG. This handler reported EVERY exception as the same soft line:
            #   "research error: <msg> — scored against the rivals you named"
            # That sentence is TRUE for a timeout or a dead host and FALSE for a programming error.
            # Measured on C5-saladshop: a one-character bug (four %-arguments to a three-placeholder
            # string, §6.7.16) raised TypeError, was caught HERE, and the ENTIRE rivals section
            # silently disappeared — member list empty, section gone. The report did not crash and
            # did not warn; it simply looked as though it had found nothing. That is how three
            # one-character bugs survived to production in one session.
            #
            # ⚠ THE DISTINCTION IS THE WHOLE POINT. A transport/parse failure is EXPECTED and
            # degrades honestly. A TypeError/KeyError/IndexError/NameError/AttributeError means the
            # CODE is wrong, and no fixture, canary or human read will catch it if it is reported as
            # a normal result. Those are named, printed to stderr with a traceback, and surfaced in
            # the verdict as a BUG rather than as a limit.
            import traceback as _tb
            _BUGS = (TypeError, KeyError, IndexError, NameError, AttributeError,
                     UnboundLocalError, SyntaxError, IndentationError, ValueError)
            if isinstance(exc, _BUGS):
                print("⚠⚠ INTERNAL BUG in the research pass (this is NOT a limit):", file=sys.stderr)
                _tb.print_exc()
                out["scan_verdict"] = (f"⚠ INTERNAL BUG: {type(exc).__name__}: {exc} — the rival "
                                       "research pass failed on a code error, not on a limit")
                out["flags"] = (out.get("flags") or []) + [
                    f"INTERNAL BUG in research pass: {type(exc).__name__}: {exc}"]
                out["internal_bug"] = f"{type(exc).__name__}: {exc}"
            else:
                out["scan_verdict"] = (f"research error: {exc} — scored against the rivals you named")

    # 3. MODEL CALL
    state = run_jev.build_state(payload)
    questions = run_jev.build_questions(rubric)
    result = run_jev.call_jev(state, questions, rubric["_meta"]["model"])
    if result is None:
        out["outcome"] = "MODEL_UNAVAILABLE"
        return out

    # 4. COMPOSITE IN CODE (never in the model)
    scored = run_jev.score(payload, result, rubric)
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / f"jev-{scored['case']}.json").write_text(json.dumps(scored, indent=2) + "\n")

    # 5. REPORT
    a, b = render_report(scored, RUBRIC, payload)
    out.update(outcome="SCORED", run=scored, report=b, report_a=a)
    return out


# ── HTML ─────────────────────────────────────────────────────────────────────
CSS = """
:root{color-scheme:dark}
body{font:15px/1.55 ui-sans-serif,-apple-system,Segoe UI,Roboto,sans-serif;
     background:#0e1116;color:#e6e9ef;margin:0;padding:32px;max-width:940px}
h1{font-size:21px;margin:0 0 4px}h2{font-size:15px;margin:26px 0 8px;color:#9fb0c8;
     text-transform:uppercase;letter-spacing:.07em}
.sub{color:#8b97a8;font-size:13px;margin-bottom:22px}
label{display:block;margin:14px 0 4px;font-size:13px;color:#a9b6c8}
input,textarea,select{width:100%;box-sizing:border-box;background:#161b23;
     border:1px solid #2a3340;color:#e6e9ef;border-radius:6px;padding:9px 11px;font:inherit}
textarea{min-height:64px;resize:vertical}
button{background:#2f6fed;color:#fff;border:0;border-radius:6px;padding:11px 22px;
     font:600 15px inherit;cursor:pointer;margin-top:22px}
button:hover{background:#3b7cf7}
.row{display:flex;gap:14px}.row>div{flex:1}
.note{background:#1b2230;border-left:3px solid #2f6fed;padding:11px 14px;
     border-radius:5px;font-size:13px;color:#b9c6d8;margin:16px 0}
.warn{background:#241c14;border-left:3px solid #d08c2c;padding:11px 14px;
     border-radius:5px;font-size:13px;color:#e0c9a2;margin:16px 0}
.err{background:#2a1717;border-left:3px solid #d04a4a;padding:11px 14px;
     border-radius:5px;font-size:13px;color:#f0b9b9;margin:16px 0}
pre{background:#11151c;border:1px solid #232c38;border-radius:6px;padding:18px;
     white-space:pre-wrap;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #232c38}
th{color:#9fb0c8;font-weight:600}
a{color:#6fa8ff}
.badge{display:inline-block;padding:2px 9px;border-radius:11px;font-size:12px;font-weight:600}
.b-ok{background:#16321f;color:#6ddc9a}.b-ref{background:#332020;color:#e88}
"""
PAGE = """<!doctype html><meta charset=utf-8><title>{title}</title>
<style>{css}</style>{body}"""


# ⚠ THE SUBMIT SCRIPT IS THE FIX FOR "the button does nothing".
# A native <form> POST requires the embedder to grant `allow-forms`. When a frame is
# sandboxed with only `allow-scripts`, the browser blocks form submission outright —
# the click is inert, with no error and no navigation, which is exactly the symptom.
# fetch() needs only `allow-scripts`, so the form is wired through JS instead, and the
# result document replaces this one. If JS is unavailable the page falls back to a real
# form POST (which works in a normal browser tab).
SUBMIT_JS = """
<script>
(function(){
  // ⚠ DO NOT WIRE THIS TO A FORM 'submit' EVENT.
  // Measured: when a frame is sandboxed with only `allow-scripts`, the browser
  // refuses form submission outright and the submit event NEVER FIRES -- so a
  // listener on 'submit' is dead code and the button looks inert. That is the
  // exact symptom reported ("clicking Generate does nothing").
  // A click on a `type=button` never initiates a form submission, so no sandbox
  // permission can block it. We read the fields ourselves and send them with fetch,
  // which needs only `allow-scripts`.
  window.__observSubmit = function(btn){
    var f = btn.closest('form') || document.querySelector('form');
    var out = document.getElementById('msg');
    var params = new URLSearchParams();
    f.querySelectorAll('input,textarea,select').forEach(function(el){
      if(!el.name) return;
      if((el.type === 'checkbox' || el.type === 'radio') && !el.checked) return;
      params.append(el.name, el.value);
    });
    btn.disabled = true;
    var original = btn.textContent;
    btn.textContent = 'Working...';
    if(out){ out.style.display='block'; out.className='note';
             out.textContent = 'Working out your read — this takes 10 to 30 seconds.'; }
    fetch('/submit', {method:'POST',
                      headers:{'Content-Type':'application/x-www-form-urlencoded'},
                      body: params.toString()})
      .then(function(r){ return r.text(); })
      .then(function(html){ document.open(); document.write(html); document.close(); })
      .catch(function(err){
        if(out){ out.className='err'; out.textContent = 'Request failed: ' + err; }
        btn.disabled = false; btn.textContent = original;
      });
  };
  document.addEventListener('click', function(ev){
    var b = ev.target.closest ? ev.target.closest('button[data-submit]') : null;
    if(b){ ev.preventDefault(); window.__observSubmit(b); }
  });
})();
</script>
"""


def shell(title: str, body: str) -> str:
    return PAGE.format(title=title, css=CSS,
                       body=f"<body>{body}{SUBMIT_JS}</body>")


def turnstile_widget() -> str:
    """The Cloudflare Turnstile widget, plus a LOUD warning when it is running on test keys.

    A page protected by a captcha that silently falls back to the always-pass test key would
    look protected and not be -- so the fallback is stated on the page rather than buried.
    """
    warn = ""
    if not gate.turnstile_configured():
        warn = ('<div class=warn style="margin-top:10px">⚠ TURNSTILE IS RUNNING ON ITS PUBLIC '
                'TEST KEYS — this widget always passes and is NOT protecting anything. Set '
                'TURNSTILE_SITE_KEY / TURNSTILE_SECRET_KEY before this form faces the public.</div>')
    return (f'<div class="cf-turnstile" data-sitekey="{gate.site_key()}" '
            f'style="margin-top:14px"></div>'
            f'<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer>'
            f'</script>{warn}')


# ── the worker ───────────────────────────────────────────────────────────────
# ⚠⚠ WHY THIS EXISTS (spec 3.7). The first working version ran the whole pipeline
# INSIDE the /confirm request. It worked, and it was wrong twice over:
#
#   1. THE USER STALLS. The browser sits on a loading page for the full model +
#      research run -- ~4 minutes measured. A confirmation link that appears to do
#      nothing for four minutes gets clicked again, or abandoned.
#   2. IT IS NOT THE DESIGN. Spec 3.7 puts the model calls in the WORKER: the
#      confirmation is acknowledged immediately and the report is delivered when
#      it is ready.
#
# So /confirm now enqueues and returns at once. The work happens here.
#
# ⚠ THE SPEND ORDERING IS UNCHANGED, and that is the point. A run still requires a
# row that `/confirm` flipped to `confirmed` -- the enqueue happens AFTER that flip,
# and only the confirmation handler can enqueue. Nothing else in this file reaches
# the pipeline. The gate is the same gate; only the waiting moved.
def run_job(cid: int, payload: dict, do_scan: bool) -> None:
    """Do the work for a confirmed row, then record it. Runs on a daemon thread."""
    form = payload.get("form") or {}
    # ⚠⚠ THE ADDRESS COMES FROM THE CONFIRMATIONS ROW, NOT FROM THE PAYLOAD. `payload_from_form`
    # rebuilds the corpus form contract, which has no email field -- so `form.get("email")` was
    # ALWAYS None here, and every report that went through the gate was saved WITHOUT an address.
    # The confirmations row is where the address actually lives (it is what the link was sent to),
    # so read it there. This is the lead engine's entire purpose: an address attached to a report.
    c0 = sqlite3.connect(DB)
    row = c0.execute("SELECT email,business_name FROM confirmations WHERE id=?", (cid,)).fetchone()
    c0.close()
    email = (row[0] if row else None) or form.get("email")
    name = (row[1] if row else None) or form.get("business_name") or "your business"
    try:
        r = run_submission(payload, do_scan)
        if r["outcome"] == "REFUSED":
            save(email=email, business_name=name, category=form.get("category"),
                 outcome="REFUSED_CONFIRMED", payload=payload,
                 report="missing: " + ", ".join(r["refusal"]["missing_slots"]))
            _finish(cid, "refused")
            return
        run = r["run"]
        i = save(email=email, business_name=name, category=form.get("category"),
                 band=run.get("band"), composite=run.get("composite"),
                 rubric_version=run.get("rubric_version"), model_id=run.get("model_id"),
                 outcome="SCORED_CONFIRMED", report=r["report"], payload=payload)
        # ⚠ record WHICH submission this confirmation produced, so /status is a lookup rather
        # than a guess. Matching on a name or an address can silently pick the wrong row.
        _finish(cid, "done", i)
    except Exception:                                          # noqa: BLE001
        # ⚠ LOUD. A silent failure here is a person who confirmed and never heard back.
        with open(os.path.join(os.path.dirname(DB), "worker-errors.log"), "a") as fh:
            fh.write("\n=== confirmation #%s ===\n%s\n" % (cid, traceback.format_exc()))
        _finish(cid, "failed")


def _finish(cid: int, job_status: str, submission_id: int | None = None) -> None:
    """Record the worker's outcome on the confirmation row (own connection: another thread)."""
    c = sqlite3.connect(DB)
    try:
        c.execute("SELECT result_submission_id FROM confirmations WHERE id=?", (cid,)).fetchone()
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE confirmations ADD COLUMN result_submission_id INTEGER")
    c.execute("UPDATE confirmations SET job_status=?, result_submission_id=? WHERE id=?",
              (job_status, submission_id, cid))
    c.commit()
    c.close()


def _worker_page(name: str, cid: int) -> str:
    """The acknowledgement. Returned IMMEDIATELY -- no model has run yet."""
    return shell("Confirmed — running", f'''
<h1>Confirmed — we're running your review now</h1>
<div class=sub>{name}</div>
<div class=note>You can close this tab. The report takes a minute or two — in the live
product it arrives by email.</div>
<p style="margin-top:18px"><a href="/status/{cid}">Check on it →</a></p>
<div class=note style="margin-top:22px">⚠ <b>Sandbox only:</b> because no mail client is wired
here, this page is how the result reaches you. In production you would not need to come back.</div>''')


@app.get("/confirm", response_class=HTMLResponse)
def confirm_page(token: str = Query("")):
    """The confirmation link target. ⚠ THIS IS THE DOOR TO MODEL SPEND (spec 3.7).

    A valid token flips the row to `confirmed` and reports that the worker may now run. It does
    NOT run the pipeline here -- the ordering rule is that nothing reaches enrichment or Jev
    until the address is proven, and this page proves it.
    """
    res = gate.confirm(DB, token)
    if not res.get("ok"):
        return HTMLResponse(shell("Confirmation failed", f"""
<h1>We couldn't confirm this link</h1>
<div class=err><b>{res.get('reason', 'invalid link')}</b></div>
<div class=note>Confirmation links work for 24 hours. If yours has expired, submit the form
again and we'll send a fresh one. Nothing was run, and nothing will be.</div>
<p><a href=/>← start again</a></p>"""), status_code=400)

    payload = res.get("payload") or {}
    form = payload.get("form") or {}
    name = form.get("business_name") or "your business"

    # ⚠ THIS IS THE ONLY PLACE THE PIPELINE RUNS. It sits AFTER the address is proven, which is
    # the whole ordering rule of spec 3.7. In production this is a queue worker; here it runs
    # inline so the flow is end-to-end testable.
    if res.get("already"):
        return HTMLResponse(shell("Already confirmed", f"""
<h1>This review is already under way</h1>
<div class=sub>{name}</div>
<div class=note>This link was already used, so <b>nothing was run twice</b> — no second model
call, no second report. If you need another, submit the form again.</div>
<p><a href=/>← submit another</a></p>"""))

    # ⚠ ENQUEUE AND RETURN. The row is ALREADY `confirmed` at this point (gate.confirm did
    # that above), so the spend permission exists before any work is scheduled -- the ordering
    # rule holds. What changed is only WHERE we wait: the pipeline moved to run_job() on a
    # daemon thread, because blocking here meant a four-minute blank page for the user.
    cid = res.get("id")
    do_scan = bool(payload.pop("_do_scan", False))
    threading.Thread(target=run_job, args=(cid, payload, do_scan), daemon=True).start()
    return HTMLResponse(_worker_page(name, cid))


@app.get("/status/{cid}", response_class=HTMLResponse)
def status_page(cid: int):
    """The result lands here once the worker finishes -- the sandbox stand-in for delivery.

    ⚠ In production the report ARRIVES BY EMAIL and this page would not be needed. It exists
    because no mail client is wired yet, and without it a confirmed submission is unreadable.
    It is also the honest local equivalent of a queue: the state lives in the database, not in
    the browser's memory.
    """
    c = sqlite3.connect(DB)
    # ⚠ a column added to an existing db needs the ALTER; CREATE TABLE IF NOT EXISTS does not do it
    try:
        c.execute("SELECT job_status,result_submission_id FROM confirmations WHERE id=?",
                  (cid,)).fetchone()
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE confirmations ADD COLUMN job_status TEXT")
        c.execute("ALTER TABLE confirmations ADD COLUMN result_submission_id INTEGER")
        c.commit()
    row = c.execute("SELECT email,business_name,status,job_status,result_submission_id "
                    "FROM confirmations WHERE id=?", (cid,)).fetchone()
    c.close()
    if not row:
        return HTMLResponse(shell("Unknown", "<h1>No such review</h1><p><a href=/>← back</a></p>"),
                            status_code=404)
    email, bname, st, job, sid = row
    if job == "done" and sid:
        # ⚠ A DIRECT LOOKUP, NOT A GUESS. The worker records which submission it produced, so
        # this cannot silently show the WRONG person's report -- which is what a name/email
        # match would risk the moment two submissions share either.
        c = sqlite3.connect(DB)
        s = c.execute("SELECT band,composite,report,model_id,rubric_version FROM submissions "
                      "WHERE id=?", (sid,)).fetchone()
        c.close()
        if s:
            band, comp, report, model_id, rver = s
            run = {"band": band, "composite": comp, "model_id": model_id, "rubric_version": rver}
            return HTMLResponse(report_page(bname, email, sid, run, report or "", None))
        job = "running"          # finished but the row is gone; do not claim a result we cannot show
    if job in ("refused", "failed"):
        return HTMLResponse(shell("Stopped", f"""
<h1>We could not produce a report</h1>
<div class=sub>{bname or "your business"}</div>
<div class=note>Confirmation succeeded, but the run stopped before a report existed. Nothing
further will be charged or run.</div>
<p><a href=/>← start again</a></p>"""))
    return HTMLResponse(shell("Running", f"""
<h1>Still running — {bname or "your review"}</h1>
<div class=note>This page does not update by itself. Reload it in a moment.</div>
<p><a href="/status/{cid}">Reload</a> · <a href=/>← back</a></p>"""))


@app.get("/", response_class=HTMLResponse)
def index():
    cases = sorted(p.stem for p in (CAL / "inputs-v4").glob("*.json")
                   if not p.stem.startswith("_"))
    opts = "".join(f"<option value='{c}'>{c}</option>" for c in cases)
    return shell("Your positioning read", f"""
<h1>Find out how strong your position really is</h1>
<div class=sub>Answer a few questions about your business. You'll get a free,
plain-language read on how clearly you own a position your competitors don't —
and what to work on next.</div>

<div class=note><b>It takes about 3 minutes</b> and there's nothing to prepare.
Answer in your own words — short answers are fine, and "we don't have one yet"
is a perfectly good answer to the positioning question. <b>The more honestly you
answer, the more useful your read.</b></div>

<div id=msg style="display:none"></div>
<noscript><div class=warn>JavaScript is off, so the button will post the form normally.
If nothing happens when you click it, the frame blocked form submission — open
<a href=http://127.0.0.1:8765/>127.0.0.1:8765</a> in a normal tab.</div></noscript>

<form id=submitform>
  <h2>Your business</h2>
  <div class=row>
    <div><label>What is your business called? *</label>
      <input name=business_name required placeholder="e.g. Two Men Bagel House"></div>
    <div><label>Where should we send your read? *</label>
      <input name=email type=email required placeholder="you@yourbusiness.com"></div>
  </div>
  <div class=row>
    <div><label>What do you sell, in your own words? *</label>
      <input name=category required
        placeholder="e.g. Fresh bagels and coffee, made in-store"></div>
    <div><label>Where do you sell it?</label><input name=city value="Singapore"></div>
  </div>
  <div class=row>
    <div><label>Your role</label><input name=role placeholder="Owner / founder"></div>
    <div><label>How many people work in the business?</label>
      <select name=company_size_band>
        <option value="1-9">Just me, or a small team (1-9)</option>
        <option value="10-500">10 to 500 people</option>
        <option value="500+">More than 500</option>
      </select></div>
  </div>
  <label>If you have a website, what is it?</label>
  <input name=website placeholder="yourbusiness.com — leave blank if you don't have one">
  <div class=note>We'll read your site so we don't have to rely only on what you
  type here. <b>This improves your read more than any other single answer</b> —
  and it's completely optional.</div>

  <h2>How you stand out</h2>
  <div class=note>Answer these in your own words. <b>If you don't have a positioning
  statement yet, just say so</b> — that's a useful answer, not a wrong one.</div>
  <label>If a customer asked "why should I choose you?", what would you say? *</label>
  <textarea name=positioning_sentence required placeholder="e.g. We bake fresh every
morning, so ours are never shipped in frozen the way the chains do it."></textarea>
  <label>What do you believe makes you different from the others?</label>
  <textarea name=differentiator placeholder="What could you honestly say about your
business that a competitor couldn't say about theirs?"></textarea>
  <label>What do competitors beat you on?</label>
  <textarea name=undercut_on placeholder="e.g. They're cheaper, they're open later,
they have more outlets."></textarea>

  <h2>Price and competitors</h2>
  <div class=row>
    <div><label>How would you describe your pricing?</label>
      <input name=your_price_point placeholder="e.g. a bit above the chains"></div>
    <div><label>And theirs?</label>
      <input name=their_price_point placeholder="e.g. similar, or a bit cheaper"></div>
  </div>
  <label>Who do you compete with, day to day?</label>
  <input name=competitors_named placeholder="Who do your customers choose between?">
  <div class=note>Naming them <b>helps your position score a lot</b>. The read can only
  tell you whether a claim is yours if it knows who else might hold it.</div>
  <label>Their websites, if you know them <span style="color:#8b97a8">(optional, but it makes the
    rival comparison reliable)</span></label>
  <input name=competitor_urls placeholder="e.g. rivalA.com, rivalB.com.sg — in the same order as above">
  <div class=note>This is the single biggest improvement you can make to your read. Our tool can
  usually find a rival's website from its name, but when a name is a common word — <i>KOI</i>,
  <i>Modo</i>, <i>Six Hands</i> — it cannot tell their site apart from a different business with the
  same name, so it stays silent rather than quote the wrong company. <b>If you paste their web
  addresses, we read exactly the pages you mean.</b></div>

  <h2>Your customers</h2>
  <label>Who is your customer, specifically?</label>
  <textarea name=customer_description placeholder="e.g. office workers within 10 minutes
of us who buy lunch on weekdays, and families on weekend mornings."></textarea>
  <div class=note>Being specific here — who they are, and when they buy — is the single
  thing that most improves the read on whether you can actually reach them.</div>

  <label style="margin-top:22px"><input type=checkbox name=do_scan value=1
     style="width:auto"> <span style="color:#8b97a8;font-size:12px">Also search the web
     for competitors (takes longer, and doesn't always find them)</span></label>

  <div class=note style="margin-top:18px">We'll email you a link to confirm.
  <b>Nothing is run until you click it.</b> That's how we make sure nobody can use this
  form to send a report about a business to someone who never asked for it.</div>
  {turnstile_widget()}
  <button type=button data-submit>Show me my read →</button>
</form>

<details style="margin-top:36px">
  <summary style="color:#8b97a8;font-size:13px;cursor:pointer">Sandbox tools — start
  from a known business, or view the CRM</summary>
  <form method=post action=/prefill style="margin-top:14px">
    <label>Start from a known business, then edit anything</label>
    <div class=row>
      <div><select name=prefill_case><option value="">— none —</option>{opts}</select></div>
      <div style="flex:0 0 130px"><button type=submit
           style="margin:0;width:100%;padding:10px">Prefill</button></div>
    </div>
  </form>
  <div class=warn style="margin-top:16px"><b>⚠ Sandbox build.</b> The captcha and the
  confirmation gate are now WIRED (§3.7) — but this instance runs on loopback, single-user,
  with no spend ceiling. Not safe to expose.
  <a href=/crm>View the CRM →</a></div>
</details>""")


@app.post("/prefill", response_class=HTMLResponse)
def prefill(prefill_case: str = Form("")):
    if not prefill_case:
        return RedirectResponse("/", status_code=303)
    d = json.loads((CAL / "inputs-v4" / f"{prefill_case}.json").read_text())
    f = d.get("form") or {}
    e = lambda v: (v or "").replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")  # noqa: E731
    comps = ", ".join(d.get("competitors_named") or [])
    return RedirectResponse("/", status_code=303) if not f else shell(
        f"prefilled {prefill_case}", f"""
<h1>Prefilled: {f.get('business_name','')}</h1>
<div class=sub>This is a real business from the test set. Edit any answer, then
generate your read.</div>
<div id=msg style="display:none"></div>
<form id=submitform>
  <input type=hidden name=case_key value="{e(prefill_case)}">
  <h2>Your business</h2>
  <div class=row>
    <div><label>What is your business called? *</label><input name=business_name value="{e(f.get('business_name'))}" required></div>
    <div><label>Where should we send your read? *</label><input name=email type=email
         value="sean@observeco.com" required></div>
  </div>
  <div class=row>
    <div><label>What do you sell? *</label><input name=category value="{e(f.get('category'))}" required></div>
    <div><label>Where do you sell it?</label><input name=city value="{e(f.get('city')) or 'Singapore'}"></div>
  </div>
  <div class=row>
    <div><label>Your role</label><input name=role value="{e(f.get('role'))}"></div>
    <div><label>How many people work in the business?</label><input name=company_size_band value="{e(f.get('company_size_band'))}"></div>
  </div>
  <label>If you have a website, what is it?</label>
  <input name=website value="{e(f.get('website'))}" placeholder="yourbusiness.com">
  <h2>How you stand out</h2>
  <label>If a customer asked "why should I choose you?", what would you say? *</label>
  <textarea name=positioning_sentence required>{e(f.get('positioning_sentence'))}</textarea>
  <label>What makes you different from the others?</label>
  <textarea name=differentiator>{e(f.get('differentiator'))}</textarea>
  <label>What do competitors beat you on?</label>
  <textarea name=undercut_on>{e(f.get('undercut_on'))}</textarea>
  <h2>Price and competitors</h2>
  <div class=row>
    <div><label>How would you describe your pricing?</label><input name=your_price_point value="{e(f.get('your_price_point'))}"></div>
    <div><label>And theirs?</label><input name=their_price_point value="{e(f.get('their_price_point'))}"></div>
  </div>
  <label>Who do you compete with, day to day?</label>
  <input name=competitors_named value="{e(comps)}">
  <h2>Your customers</h2>
  <div class=warn>Section 3.10 needs a <b>customer description</b> for DEMAND REACH
  and MENTAL ADVANTAGE. No field collects it — the corpus does not carry one either.
  It is collected here and flagged rather than silently scored.</div>
  <label>Who is your customer, specifically?</label>
  <textarea name=customer_description></textarea>
  <button type=button data-submit>Show me my read →</button>
</form>""")


@app.post("/submit", response_class=HTMLResponse)
def submit(request: Request, business_name: str = Form(""), email: str = Form(""),
           category: str = Form(""), city: str = Form("Singapore"), role: str = Form(""),
           company_size_band: str = Form("10-500"), positioning_sentence: str = Form(""),
           differentiator: str = Form(""), undercut_on: str = Form(""),
           your_price_point: str = Form(""), their_price_point: str = Form(""),
           competitors_named: str = Form(""), customer_description: str = Form(""),
           competitor_urls: str = Form(""),
           website: str = Form(""),
           case_key: str = Form(""), do_scan: str = Form(""),
           cf_turnstile_response: str = Form("")):
    """⚠ SPEC 3.7: THIS HANDLER MUST NOT REACH THE MODEL.

    Order of operations, and the order is the design:
        1. captcha  -- stops a bot filling the form at machine speed
        2. store as `pending` + show/send the confirmation link   [ZERO MODEL COST]
        3. stop. Nothing else runs here.

    All model work happens on /confirm, behind a proven address. That is what protects the
    budget: a captcha stops automated SUBMISSION, it does not stop LLM SPEND.
    """
    f = dict(business_name=business_name, email=email, category=category, city=city,
             role=role, company_size_band=company_size_band,
             positioning_sentence=positioning_sentence, differentiator=differentiator,
             undercut_on=undercut_on, your_price_point=your_price_point,
             their_price_point=their_price_point, competitors_named=competitors_named,
             customer_description=customer_description, website=website,
             competitor_urls=competitor_urls, case_key=case_key)

    # ── 1. THE CAPTCHA. Fails closed: an unreachable verifier refuses rather than admits.
    #
    # ⚠ THE LOCAL BYPASS, AND WHY IT IS SAFE HERE. Turnstile refuses an unauthorized hostname
    # with error 110200 ("Domain not authorized"), which blocks LOCAL testing on a dashboard
    # setting. The captcha exists to stop bots hitting a PUBLIC endpoint; on a loopback-only
    # instance there is nothing to protect and the confirmation gate is the real spend control.
    # So the bypass is allowed ONLY when all three hold: the request came from loopback, the
    # operator asked for it, and the client address is genuinely local. It is OFF by default and
    # it REFUSES on a public bind -- a bypass that could survive a deploy is worse than none.
    _peer = request.client.host if request.client else ""
    _local = _peer in ("127.0.0.1", "::1", "localhost")
    if os.environ.get("SANDBOX_SKIP_CAPTCHA") == "1" and _local:
        captcha = {"ok": True, "reason": "SKIPPED (loopback sandbox)"}
    else:
        captcha = gate.verify_turnstile(cf_turnstile_response, remote_ip=_peer)
    if not captcha["ok"]:
        save(email=email, business_name=business_name, category=category,
             outcome="CAPTCHA_REFUSED", payload=payload_from_form(f),
             report="blocked at the captcha: " + captcha["reason"])
        return HTMLResponse(shell("Check failed", f"""
<h1>We couldn't verify that you're a person</h1>
<div class=err><b>{captcha["reason"]}</b></div>
<div class=note>Nothing was run and nothing was sent — this submission stopped at the captcha,
before any research or scoring.</div>
<p><a href=/>← try again</a></p>"""), status_code=400)

    # ── 2. STORE AS PENDING AND ASK FOR CONFIRMATION. Still zero model cost.
    payload = payload_from_form(f)
    payload["_do_scan"] = bool(do_scan)
    pending = gate.submit_pending(DB, email, business_name, payload, captcha_ok=True)

    # In production this link is EMAILED and never shown. The sandbox has no mail client, so it
    # displays the link and says so -- showing it silently would make the gate look like
    # theatre when it is the load-bearing control.
    link = f"/confirm?token={pending['token']}"
    return HTMLResponse(shell("Confirm your email", f"""
<h1>Check your email to confirm</h1>
<div class=sub>{business_name} · submission #{pending["id"]}</div>
<div class=note><b>Nothing has been run yet.</b> No research, no scoring, no cost — the
submission is stored and waiting. We would now email
<b>{email or "(no address given)"}</b> a link that looks like this:</div>
<div class=note style="border-left-color:#2f6fed"><a href="{link}">{link}</a></div>
<div class=warn><b>⚠ Sandbox:</b> there is no mail client here, so the link is shown instead
of emailed. <b>In production this link is emailed and never displayed</b> — that is what stops
a stranger's submission from spending our model budget (spec 3.7).</div>
<p><a href=/>← back</a> &nbsp; <a href=/crm>CRM →</a></p>"""))
    if r["outcome"] == "MODEL_UNAVAILABLE":
        save(email=email, business_name=business_name, category=category,
             outcome="MODEL_UNAVAILABLE", payload=payload, report="(no report)")
        return HTMLResponse(shell("unavailable",
            "<h1>Jev unavailable</h1><p>No output written.</p><p><a href=/>← back</a></p>"))

    run = r["run"]
    i = save(email=email, business_name=business_name, category=category,
             band=run.get("band"), composite=run.get("composite"),
             rubric_version=run.get("rubric_version"), model_id=run.get("model_id"),
             outcome="SCORED", report=r["report"], payload=payload)
    return HTMLResponse(report_page(business_name, email, i, run, r["report"],
                                    r.get("scan_verdict")))


def report_page(business_name, email, i, run, report, scan) -> str:
    """A result page that REPLACES THE DOCUMENT, so it works inside any iframe.

    ⚠ WHY THIS IS A SEPARATE FUNCTION AND WHY IT MATTERS.
    The first version returned the report as the POST response. That is the normal
    thing to do, and it worked in a plain browser — but it FAILED in an embedded
    frame, and the failure looked like "the button does nothing":

        sandbox="allow-scripts"  (no allow-forms)  ->  the browser blocks the form
        submission entirely. The button is inert. No navigation, no error the user
        can see. Measured across five iframe variants: every variant WITHOUT
        allow-forms produced NO POST; every variant WITH it submitted normally.

    Rather than depend on the embedder granting `allow-forms`, the form now posts
    through `fetch()` (which needs only `allow-scripts`) and the response HTML
    replaces the document via document.write. `allow-scripts` is the one permission
    a live app is essentially always given.

    ⚠ AND THE SECOND TRAP THIS CLOSES: a frame sandboxed WITHOUT
    `allow-same-origin` runs at an OPAQUE origin, so the fetch is cross-origin and
    fails silently unless the server sends CORS headers. That is why the CORS
    middleware above exists — it is load-bearing, not decoration.
    """
    dims = run.get("dimensions_display_1to5") or {}
    rows = "".join(f"<tr><td>{k}</td><td>{v}/5</td></tr>" for k, v in dims.items())
    return shell(f"Your read — {business_name}", f"""
<h1>{business_name}</h1>
<div class=sub>A copy is on its way to {email}.</div>
<p><span class="badge b-ok">{run.get('composite')}/100 — {run.get('band')}</span></p>
<h2>Your scores at a glance</h2><table><tr><th>what we looked at</th><th>your level</th></tr>{rows}</table>
<div class=note><b>How we judged your competitors:</b> {scan or "—"}</div>
<h2>Your full read</h2>
<pre>{report.replace("<", "&lt;")}</pre>
<details style="margin-top:26px"><summary style="color:#8b97a8;font-size:12px;cursor:pointer">
  Sandbox details</summary>
<div class=note>submission #{i} · rubric {run.get('rubric_version')} · {run.get('model_id')}
 · <a href=/>submit another</a> · <a href=/crm>CRM →</a></div></details>""")


@app.get("/crm", response_class=HTMLResponse)
def crm():
    c = db()
    # ⚠ LEFT JOIN, because the address for a gate-confirmed row lives on the CONFIRMATIONS row
    # (that is what the link was sent to). Without the join the CRM shows a scored report with no
    # address -- which is the one thing a lead engine must never do silently.
    rows = c.execute(
        "SELECT s.id, s.created_at, COALESCE(NULLIF(s.email,''), c.email), s.business_name, "
        "s.band, s.composite, s.outcome "
        "FROM submissions s LEFT JOIN confirmations c ON c.result_submission_id = s.id "
        "ORDER BY s.id DESC").fetchall()
    c.close()
    body = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
        "<td>{}</td></tr>".format(
            i, (t or "")[:19], e or "", (b or "")[:34], band if band is not None else "—",
            comp if comp is not None else "—", o)
        for i, t, e, b, band, comp, o in rows) or "<tr><td colspan=7>(empty)</td></tr>"
    return shell("CRM", f"""
<h1>CRM — captured addresses</h1>
<div class=sub>{len(rows)} submission(s). The minimum a lead engine must do: prove an
address arrives attached to a report that exists.</div>
<div class=note><b>⚠ A local SQLite file</b> (<code>sandbox.db</code>), NOT the system
of record (spec 7.x). No sequences, no lead scoring, no vendor — deliberately.</div>
<table><tr><th>#</th><th>when (UTC)</th><th>email</th><th>business</th><th>band</th>
<th>score</th><th>outcome</th></tr>{body}</table>
<p><a href=/>← back</a></p>""")


if __name__ == "__main__":
    import uvicorn
    # ⚠ THE TEST-KEY INSTANCE RUNS ON A DIFFERENT PORT ON PURPOSE. Cloudflare's always-pass test
    # secret is only accepted BY the test sitekey pair, so a happy-path test needs an instance
    # configured with the test keys -- and that instance must never be the one the public sees.
    # `SANDBOX_PORT` lets a proof instance run alongside the real one; `TURNSTILE_TEST_KEYS=1`
    # pins it to the documented test pair and announces that it verifies nothing.
    import os as _os
    if _os.environ.get("TURNSTILE_TEST_KEYS") == "1":
        _os.environ["TURNSTILE_SITE_KEY"] = gate.TEST_SITEKEY
        _os.environ["TURNSTILE_SECRET_KEY"] = gate.TEST_SECRET
    _port = int(_os.environ.get("SANDBOX_PORT", "8765"))
    # ⚠⚠ THE NOT-LIVE GUARD. The sandbox has NO captcha bypass in production terms: no spend
    # ceiling, and the confirmation link is DISPLAYED rather than emailed because no mail client
    # is wired. Exposing it would publish a tool that mails nothing and can be drained.
    # So it refuses any non-loopback bind unless the operator explicitly overrides. Sean:
    # "Just don't make it go live yet." This is that instruction as code, not as a note.
    if _os.environ.get("SANDBOX_ALLOW_PUBLIC") != "1":
        _host = "127.0.0.1"
    else:
        _host = _os.environ.get("SANDBOX_HOST", "0.0.0.0")
        print("⚠⚠ SANDBOX_ALLOW_PUBLIC=1 — BINDING TO %s. This is NOT launch-ready: no spend "
              "ceiling, and confirmation links are displayed rather than emailed." % _host,
              file=sys.stderr)
    _test = _os.environ.get("TURNSTILE_TEST_KEYS") == "1"
    print("ObserveCo sandbox → http://%s:%d%s%s" % (
        _host, _port,
        "   ⚠ TEST KEYS — the captcha always passes" if _test else "",
        "   ⚠ NOT LIVE: loopback only, nothing on the website points here" if _host == "127.0.0.1"
        else "   ⚠⚠ PUBLIC BIND — NOT launch-ready"), file=sys.stderr)
    uvicorn.run(app, host=_host, port=_port, log_level="warning")
