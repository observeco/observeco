#!/usr/bin/env python3
"""consent_record.py -- spec 095 section 3.2 and 7.7. THE MISSING WRITER.

WHY THIS FILE EXISTS
--------------------
`migrations/004_consent_records.sql` defines the consent table, and the spec says of it
(section 7.7): "Nothing records consent anywhere: the ..." -- that is, the schema shipped and
NOTHING WROTE TO IT. A consent schema with no writer is worse than no schema: it looks like
compliance in a review and produces no evidence when a regulator asks what this person agreed
to, when, and on the basis of which words.

This module is the writer, and it is deliberately the ONLY writer.

THE FOUR RULES THE SCHEMA ALREADY ENCODES, AND WHICH THIS MODULE MUST NOT BREAK
--------------------------------------------------------------------------------
1. PER PURPOSE, NEVER BUNDLED. Section 3.2: "A single checkbox covering both is the common PDPA
   failure." One 'agreed to terms' row cannot prove WHICH purposes were agreed, so each purpose
   is its own row and withdrawing one does not revoke the other.
2. append-only + ONE LIVE ROW PER (email, purpose). Re-consent UPDATEs the live row rather than
   duplicating, so "what is currently agreed" stays a single lookup.
3. NO DEFAULT-ON. The `granted` column has no default by design, so a caller that forgets to
   pass it fails rather than silently recording agreement. A pre-ticked box is not consent.
4. THE NOTICE VERSION IS PART OF THE RECORD. If the wording changes, the old consent was given
   to DIFFERENT words -- so the version and a hash of the exact text are stored beside it.

PURPOSE 1 IS NOT A PERMISSION (section 7.7)
------------------------------------------
Purpose 1 ("deliver the requested report") is the act the person asked for, not a permission
they granted. It gets NO checkbox -- giving it one would blur exactly the distinction section
7.7 draws. It is still recorded, as an ACKNOWLEDGEMENT, so the notice version shown at
submission is evidenced. The report is NEVER conditional on the two boxes.

THE SANDBOX/PRODUCTION DIVERGENCE, STATED PLAINLY
-------------------------------------------------
The migration at `migrations/004_consent_records.sql` targets POSTGRES (bigserial, timestamptz,
partial unique index). The sandbox runs SQLITE (specs/calibration/sandbox/sandbox.db), and no
Postgres client is wired anywhere in this repo. This module therefore creates a SQLite
equivalent and keeps the same column names and the same constraints, so the production
migration is a copy of the same shape. IT IS NOT YET WRITING TO POSTGRES -- that is a real
limit, not a detail, and it is reported rather than hidden.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# ── The notice, verbatim from privacy_rewrite_draft.md PART E (DRAFT for approval) ──────────
# NOT INVENTED COPY. If this text changes, NOTICE_VERSION MUST change with it, because a
# consent recorded against old words does not evidence agreement to new ones.
NOTICE_VERSION = "partE-2026-10-07"

NOTICE_TEXT = (
    "We'll produce your report and email it to you. Two optional extras below — both "
    "unticked. Tick only what you want.\n"
    "Keep me posted — occasional emails about ObserveCo's services, and what we're learning "
    "from these reviews.\n"
    "Show me how I compare. My answers — with no business name, no email address and no "
    "personal names — can go into Singapore industry benchmarks, and I get the comparison "
    "back on a best-endeavours basis.\n"
    "The report itself is what you asked for. It is never conditional on the boxes above."
)

PURPOSE_DELIVER = 1   # the act they asked for -- an ACKNOWLEDGEMENT, never a checkbox
PURPOSE_FOLLOWUP = 2  # "Keep me posted"
PURPOSE_RESEARCH = 3  # "Show me how I compare"

DDL = """
create table if not exists consent_records (
    id              integer primary key autoincrement,
    email           text        not null,
    purpose         smallint    not null check (purpose in (1,2,3)),
    granted         boolean     not null,
    notice_version  text        not null,
    notice_hash     text        not null,
    granted_at      text        not null,
    withdrawn_at    text,
    source          text        not null default 'business_review_form'
);
create unique index if not exists consent_records_live_idx
    on consent_records (lower(email), purpose) where withdrawn_at is null;
create index if not exists consent_records_email_idx on consent_records (lower(email));
"""


def notice_hash() -> str:
    """Hash of the EXACT notice text shown, so the record proves which words were agreed to."""
    return hashlib.sha256(NOTICE_TEXT.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(DDL)


def record(con: sqlite3.Connection, email: str, follow_up: bool, research: bool) -> dict:
    """Write the consent rows for one submission. Returns what was recorded.

    ⚠ follow_up and research MUST arrive as real booleans derived from an explicit click. They
    are NOT defaulted here -- a caller that forgets them passes False, which records refusal,
    and refusal is the safe direction (the schema's no-default rule, section 7.7).
    """
    email = (email or "").strip()
    if not email:
        return {"ok": False, "reason": "no email -- a consent record with no subject is not evidence"}
    ensure_schema(con)
    nh = notice_hash()
    stamp = _now()
    written = []
    # purpose 1: the ACKNOWLEDGEMENT. granted=True because they asked for the report.
    plan = [(PURPOSE_DELIVER, True, "acknowledgement: the report was requested"),
            (PURPOSE_FOLLOWUP, bool(follow_up), "optional: keep me posted"),
            (PURPOSE_RESEARCH, bool(research), "optional: show me how I compare")]
    for purpose, granted, why in plan:
        # re-consent UPDATEs the live row; it never duplicates it.
        cur = con.execute(
            "update consent_records set granted=?, notice_version=?, notice_hash=?, granted_at=?, source=?"
            " where lower(email)=lower(?) and purpose=? and withdrawn_at is null",
            (1 if granted else 0, NOTICE_VERSION, nh, stamp, "business_review_form", email, purpose))
        if cur.rowcount == 0:
            con.execute(
                "insert into consent_records"
                " (email,purpose,granted,notice_version,notice_hash,granted_at,source)"
                " values (?,?,?,?,?,?,?)",
                (email, purpose, 1 if granted else 0, NOTICE_VERSION, nh, stamp,
                 "business_review_form"))
        written.append({"purpose": purpose, "granted": granted, "why": why})
    con.commit()
    return {"ok": True, "email": email, "notice_version": NOTICE_VERSION,
            "notice_hash": nh, "granted_at": stamp, "rows": written}


def current(con: sqlite3.Connection, email: str) -> dict:
    """What is currently agreed for this address -- the single indexed lookup the schema promises."""
    ensure_schema(con)
    rows = con.execute(
        "select purpose, granted from consent_records where lower(email)=lower(?) and withdrawn_at is null",
        (email,)).fetchall()
    return {int(p): bool(g) for p, g in rows}


def withdraw(con: sqlite3.Connection, email: str, purpose: int) -> int:
    """Withdraw ONE purpose without touching the others -- the whole reason the rows are split."""
    ensure_schema(con)
    cur = con.execute(
        "update consent_records set withdrawn_at=? where lower(email)=lower(?) and purpose=?"
        " and withdrawn_at is null", (_now(), email, purpose))
    con.commit()
    return cur.rowcount


def _selftest() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "t.db"
    con = sqlite3.connect(tmp)
    fails = []

    def check(name, got, want):
        ok = got == want
        print(("PASS  " if ok else "FAIL  ") + name, "->", got if ok else f"got {got!r} want {want!r}")
        if not ok:
            fails.append(name)

    print("1. notice hash is stable and versioned")
    check("notice_hash stable", notice_hash() == notice_hash(), True)
    check("notice_version recorded", NOTICE_VERSION.startswith("partE"), True)

    print("2. purpose 1 is an ACKNOWLEDGEMENT, never a checkbox")
    r = record(con, "a@x.test", follow_up=False, research=False)
    check("no-consent still records purpose 1", r["ok"], True)
    for row in r["rows"]:
        print(f"      purpose {row['purpose']} granted={row['granted']}  ({row['why']})")
    check("purpose 1 granted", [x for x in r["rows"] if x["purpose"] == 1][0]["granted"], True)

    print("3. NO DEFAULT-ON -- unticked means refusal is recorded, not agreement")
    check("purpose 2 refused", current(con, "a@x.test")[2], False)
    check("purpose 3 refused", current(con, "a@x.test")[3], False)

    print("4. ticking one purpose does not grant the other (section 3.2)")
    record(con, "b@x.test", follow_up=True, research=False)
    cur = current(con, "b@x.test")
    check("purpose 2 granted", cur[2], True)
    check("purpose 3 still refused", cur[3], False)

    print("5. re-consent UPDATES the live row, never duplicates it")
    record(con, "a@x.test", follow_up=True, research=True)
    n = con.execute("select count(*) from consent_records where lower(email)='a@x.test' and withdrawn_at is null").fetchone()[0]
    check("still 3 live rows (not 6)", n, 3)
    check("purpose 2 now granted", current(con, "a@x.test")[2], True)

    print("6. withdrawal is per purpose and does not revoke the other")
    check("withdrew 1 row", withdraw(con, "a@x.test", 2), 1)
    cur = current(con, "a@x.test")
    check("purpose 2 gone", 2 in cur, False)
    check("purpose 3 survives", cur[3], True)

    print("7. a record with no subject is refused, not written")
    check("empty email refused", record(con, "", True, True)["ok"], False)

    print("8. append-only: withdrawal leaves the row, it does not delete it")
    total = con.execute("select count(*) from consent_records where lower(email)='a@x.test'").fetchone()[0]
    check("withdrawn row preserved", total >= 3, True)

    print(f"\nSELF-TEST: {len(fails)} failed")
    con.close()
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
