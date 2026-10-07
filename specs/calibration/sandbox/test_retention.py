"""Two-sided test for the retention sweep. The dangerous failure is the SECOND direction.

A sweep that deletes too little breaks a promise to a stranger.
A sweep that deletes too much DELETES A CUSTOMER'S REPORT. So this proves both:
  A. a 45-day-old UNCONFIRMED row IS removed  (the email's promise)
  B. a 45-day-old CONFIRMED row is NOT removed (Sean's keep decision; it is well inside 2 years)
  C. dry-run removes nothing
  D. an aged CONFIRMED row (3 years) is still NOT removed -- keeping is deliberate, not an oversight
"""
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path("/Users/seanfzc/projects/observeco-main/specs/calibration/sandbox")
sys.path.insert(0, str(BASE))
import retention                                                      # noqa: E402

TMP = BASE / "_retention_test.db"
if TMP.exists():
    TMP.unlink()
c = sqlite3.connect(TMP)
c.execute("""CREATE TABLE confirmations (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT,
             email TEXT, business_name TEXT, payload TEXT, status TEXT, token_hash TEXT,
             confirmed_at TEXT, turnstile_ok INTEGER)""")
c.execute("""CREATE TABLE submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT,
             email TEXT, business_name TEXT, category TEXT, band TEXT, composite REAL,
             rubric_version TEXT, model_id TEXT, outcome TEXT, report TEXT, payload TEXT)""")

def ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")

rows = [
    # (table, email, status/outcome, age_days, should_survive)
    ("confirmations", "stranger@x.test", "pending",   45,  False),   # A: email promise
    ("confirmations", "customer@x.test", "confirmed", 45,  True),    # B: kept
    ("confirmations", "stranger2@x.test","pending",    5,  True),    # too new
    ("submissions",   "stranger@x.test", "CAPTCHA_REFUSED", 45, False),  # A: never became a report
    ("submissions",   "customer@x.test", "SCORED_CONFIRMED", 45, True),  # B: kept
    ("submissions",   "old@x.test",      "SCORED_CONFIRMED", 1095, True), # D: 3 yrs, still KEPT
]
for tbl, email, st, age, _ in rows:
    if tbl == "confirmations":
        c.execute("INSERT INTO confirmations (created_at,email,business_name,payload,status,token_hash,"
                  "turnstile_ok) VALUES (?,?,?,?,?,?,?)", (ago(age), email, "Co", "{}", st, "h", 1))
    else:
        c.execute("INSERT INTO submissions (created_at,email,business_name,outcome,report) "
                  "VALUES (?,?,?,?,?)", (ago(age), email, "Co", st, "report text"))
c.commit()
c.close()

def present(tbl, email):
    q = sqlite3.connect(TMP)
    n = q.execute("SELECT count(*) FROM %s WHERE email=?" % tbl, (email,)).fetchone()[0]
    q.close()
    return n > 0

print("=== C. DRY RUN first -- must delete nothing ===")
res = retention.sweep(TMP, dry_run=True)
print("   dry-run result:", {k: v for k, v in res.items() if "candidate" in k or "past" in k})
survived_dry = all(present(t, e) for t, e, _, _, _ in rows)
print("   all 6 rows still present:", "✅" if survived_dry else "✗ SOMETHING DELETED IN DRY RUN")

print("\n=== A/B/D. real sweep ===")
res = retention.sweep(TMP)
print("   ", {k: v for k, v in res.items() if k != "dry_run"})

ok = True
for tbl, email, st, age, should_survive in rows:
    here = present(tbl, email)
    good = (here == should_survive)
    ok &= good
    label = "survives" if should_survive else "removed "
    print("   %s %-22s %-18s age=%4dd  %s" %
          ("✅" if good else "✗ FAIL", email, st[:18], age, label))

print("\nDRY RUN SAFE:", survived_dry)
print("BOTH DIRECTIONS CORRECT:", ok)
TMP.unlink()
