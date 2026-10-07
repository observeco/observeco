"""retention.py — the retention promises, as code that actually runs (spec 3.7 / 7.5).

WHY THIS EXISTS. Two promises are made to real people, and until now neither was enforced:

  1. THE CONFIRMATION EMAIL says "If this wasn't you, ignore this email ... We'll delete your
     details within 30 days." That is about the UNCONFIRMED case -- a stranger who never asked
     for a report. `confirmation_gate.purge_expired()` implements it correctly, but NOTHING EVER
     CALLED IT outside a test. A retention rule that nothing runs is not a retention rule.

  2. THE CONFIRMED case is different, and Sean decided it (7 Oct): KEEP the report and the answers
     behind it for TWO YEARS, because a score should still be defensible if the customer comes
     back. Section 7.5's report period, said in plain English.

So this module does both, on a schedule, and reports what it did.

  * unconfirmed + older than 30 days  -> DELETE (the email's promise)
  * confirmed  + older than 730 days  -> the report/contact retention decision, per 7.5

⚠ AND IT IS DELIBERATELY INVERTED FROM THE OBVIOUS SHAPE. The obvious version deletes whatever is
old enough. This one refuses to delete ANYTHING unless the row's status says it is safe to, so a
schema change or a bad query cannot turn "expire a stale row" into "erase a customer's report".

Run it:      python3 retention.py            (sweep + report)
Dry run:     python3 retention.py --dry-run  (report only, deletes nothing)
As a job:    call sweep() on a schedule -- see install_schedule() for the launchd plist.
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "sandbox.db"

# ⚠ THE TWO PERIODS, EACH WITH ITS OWN BASIS -- they are not the same promise.
UNCONFIRMED_DAYS = 30      # the confirmation email: "we'll delete your details within 30 days"
CONFIRMED_DAYS = 730      # Sean, 7 Oct: two years. Spec 7.5's report period


def _cutoff(days: int, now: datetime | None = None) -> str:
    return ((now or datetime.now(timezone.utc)) - timedelta(days=days)
            ).isoformat(timespec="seconds")


def sweep(db_path: Path | str = DB, *, dry_run: bool = False,
          now: datetime | None = None) -> dict:
    """Run both retentions and return what happened. Never raises on an empty db."""
    c = sqlite3.connect(str(db_path))
    out: dict[str, object] = {"unconfirmed_deleted": 0, "confirmed_expired": 0, "dry_run": dry_run}
    deleted = 0

    # ── 1. the email's promise: an unconfirmed submission is deleted ──────────────
    # ⚠ `status='pending'` is load-bearing. Only a row that was NEVER confirmed may be deleted
    # here -- a confirmed row belongs to a customer who asked for a report, and the sweep must
    # not be able to reach it. This is the ordering rule of 3.7 expressed as a WHERE clause.
    cut30 = _cutoff(UNCONFIRMED_DAYS, now)
    n_pending = c.execute("SELECT count(*) FROM confirmations "
                          "WHERE status='pending' AND created_at < ?", (cut30,)).fetchone()[0]
    out["unconfirmed_candidates"] = n_pending
    if n_pending and not dry_run:
        c.execute("DELETE FROM confirmations WHERE status='pending' AND created_at < ?", (cut30,))
        deleted += n_pending
    out["unconfirmed_deleted"] = deleted

    # a submission row that never became a report (captcha refusal / refusal) and is old
    n_sub = c.execute("SELECT count(*) FROM submissions WHERE email IS NOT NULL "
                      "AND outcome IN ('CAPTCHA_REFUSED') AND created_at < ?", (cut30,)).fetchone()[0]
    out["unconfirmed_submission_candidates"] = n_sub
    if n_sub and not dry_run:
        c.execute("DELETE FROM submissions WHERE email IS NOT NULL "
                  "AND outcome IN ('CAPTCHA_REFUSED') AND created_at < ?", (cut30,))
        deleted += n_sub
    out["unconfirmed_deleted"] = deleted

    # ── 2. the confirmed case: KEPT, and counted, so "two years" is a fact and not a slogan ──
    # ⚠ THIS DELIBERATELY DELETES NOTHING. Sean's decision is to KEEP the data; the only thing
    # that must be true is that we KNOW what is older than the stated period, so the period is a
    # number we can defend rather than a claim we make. Turning this into a delete is a one-line
    # change IF he ever wants it enforced -- and that would be his call, not a default.
    cut730 = _cutoff(CONFIRMED_DAYS, now)
    n_oldreports = c.execute("SELECT count(*) FROM submissions WHERE outcome='SCORED_CONFIRMED' "
                             "AND created_at < ?", (cut730,)).fetchone()[0]
    out["confirmed_reports_past_period"] = n_oldreports

    if not dry_run:
        c.commit()
    c.close()
    return out


def install_schedule(load: bool = False) -> str:
    """The launchd job that makes this run. A rule nothing calls is not a rule.

    ⚠ DAILY, NOT CONTINUOUS: a retention promise is measured in days, so an hourly job would
    burn battery to move nothing. Daily at a quiet hour is the right cadence.
    """
    plist = HERE / "com.observeco.sandbox-retention.plist"
    plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.observeco.sandbox-retention</string>
  <key>ProgramArguments</key>
  <array>
    <string>{__import__("sys").executable}</string>
    <string>{HERE / "retention.py"}</string>
  </array>
  <key>WorkingDirectory</key><string>{HERE}</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>4</integer><key>Minute</key><integer>15</integer></dict>
  <key>StandardOutPath</key><string>/tmp/observeco-retention.log</string>
  <key>StandardErrorPath</key><string>/tmp/observeco-retention.log</string>
</dict>
</plist>
""")
    if load:
        import subprocess
        subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
        r = subprocess.run(["launchctl", "load", str(plist)], capture_output=True, text=True)
        return "loaded: %s (rc=%s)" % (plist, r.returncode)
    return "written: %s (not loaded; pass load=True or run launchctl load)" % plist


def main() -> int:
    ap = argparse.ArgumentParser(description="the retention promises, as code")
    ap.add_argument("--dry-run", action="store_true", help="report only; delete nothing")
    ap.add_argument("--install", action="store_true", help="write the launchd job")
    ap.add_argument("--load", action="store_true", help="write AND load the launchd job")
    a = ap.parse_args()
    if a.install or a.load:
        print(install_schedule(load=a.load))
        return 0
    res = sweep(dry_run=a.dry_run)
    print("retention sweep%s" % ("  (DRY RUN)" if a.dry_run else ""))
    for k, v in res.items():
        print("   %-34s %s" % (k, v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
