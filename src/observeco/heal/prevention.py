"""Incident Skill Auto-Creation (L3 Learning Loop) — ObserveCo #81.

After a successful heal, the LLM extracts a failure pattern and writes a
prevention SKILL.md to ~/.observeco/prevention/. On the next failure, the
system checks prevention skills first via FTS5; if a skill matches the error
signature, the known fix is applied directly — skipping the LLM diagnosis
pipeline (faster, zero LLM cost).

The system gets cheaper to run as it learns your infrastructure's failure modes.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional

from observeco.db import Database

PREVENTION_DIR = Path.home() / ".observeco" / "prevention"

# Known-safe remediation actions that may auto-apply from a prevention skill.
# Dangerous actions (pip_install, code_fix) NEVER auto-execute — they require
# human approval per the auto-heal safety model.
SAFE_REMEDIATIONS = {"restart", "restart_with_cap", "cooldown", "trim", "garden_cleanup"}

# Deprecate a skill after this many consecutive verification failures.
DEPRECATE_AFTER = 2


def _prevention_dir() -> Path:
    PREVENTION_DIR.mkdir(parents=True, exist_ok=True)
    return PREVENTION_DIR


def extract_error_signature(error_log: str, agent_name: str, agent_state: dict | None = None) -> str:
    """Extract a normalized error signature for FTS5 matching.

    Strips volatile data (timestamps, PIDs, file paths, addresses) and keeps
    the error type + core message + agent state.

    ponytail: naive regex stripping — doesn't handle obfuscated or multi-line
    stack traces well. Upgrade: LLM-assisted extraction if regex match
    confidence < 0.7 against existing prevention skills.
    """
    state = agent_state or {}
    sig = re.sub(r"\d{4}-\d{2}-\d{2}.*?\d{2}:\d{2}:\d{2}", "", error_log)
    sig = re.sub(r"PID\s*\d+", "PID", sig)
    sig = re.sub(r"/[^/\s]+\.py", "<file>", sig)
    sig = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", sig)
    status = state.get("status", "unknown")
    return f"{agent_name}:{status}:{sig.strip()[:500]}"


def _hash_signature(signature: str) -> str:
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()


def check_prevention(agent_name: str, error_signature: str) -> Optional[dict]:
    """Look up a matching, non-deprecated prevention skill via FTS5.

    Returns the skill dict (with remediation) or None if no match.
    """
    db = Database()
    conn = db._get_conn()
    # FTS5 match on agent_name + error_signature terms
    query = f'"{agent_name}" ' + " OR ".join(
        f'"{tok}"' for tok in error_signature.split(":")[-1].split()[:8] if tok
    )
    try:
        rows = conn.execute(
            "SELECT s.id, s.agent_name, s.pattern_hash, s.trigger_conditions, "
            "s.skill_path, s.diagnosis, s.remediation, s.success_count, "
            "s.fail_count, s.deprecated "
            "FROM prevention_skills_fts f "
            "JOIN prevention_skills s ON s.id = f.skill_id "
            "WHERE prevention_skills_fts MATCH ? AND s.deprecated = 0 "
            "AND s.agent_name = ? "
            "ORDER BY rank LIMIT 1",
            (query, agent_name),
        ).fetchall()
    except Exception:
        return None
    if not rows:
        return None
    r = rows[0]
    return {
        "id": r["id"],
        "agent_name": r["agent_name"],
        "pattern_hash": r["pattern_hash"],
        "skill_path": r["skill_path"],
        "diagnosis": r["diagnosis"],
        "remediation": r["remediation"],
        "success_count": r["success_count"],
        "fail_count": r["fail_count"],
        "deprecated": r["deprecated"],
    }


def write_prevention_skill(
    agent_name: str,
    error_signature: str,
    diagnosis: str,
    remediation: str,
    trigger_conditions: dict | None = None,
) -> Optional[str]:
    """Write a prevention SKILL.md and index it. Returns skill_path or None.

    remediation is the raw remediation text from the LLM. Known-safe actions
    are extracted for auto-application; dangerous ones are recorded but never
    auto-run.
    """
    db = Database()
    conn = db._get_conn()
    pattern_hash = _hash_signature(error_signature)
    # Idempotent: if this exact pattern already has a skill, skip.
    existing = conn.execute(
        "SELECT id FROM prevention_skills WHERE pattern_hash=? AND agent_name=?",
        (pattern_hash, agent_name),
    ).fetchone()
    if existing:
        return None

    d = _prevention_dir()
    skill_path = d / f"{int(__import__('time').time())}-{agent_name}.md"
    conditions = trigger_conditions or {"error_signature": error_signature[:200]}
    content = (
        "---\n"
        f"name: prevention-{agent_name}-{pattern_hash[:8]}\n"
        'version: "1.0"\n'
        f"created: {__import__('time').strftime('%Y-%m-%d')}\n"
        f"agent: {agent_name}\n"
        f"pattern_hash: {pattern_hash}\n"
        f"trigger_conditions: {conditions}\n"
        "---\n\n"
        f"# Prevention: {diagnosis[:80]}\n\n"
        "## Trigger\n"
        f"Agent `{agent_name}` fails with: {error_signature[:300]}\n\n"
        "## Root Cause\n"
        f"{diagnosis}\n\n"
        "## Remediation\n"
        f"{remediation}\n\n"
        "## Verification\n"
        "Heal pipeline re-runs post-fix health check; if green, skill applied.\n"
    )
    skill_path.write_text(content, encoding="utf-8")

    cur = conn.execute(
        "INSERT INTO prevention_skills "
        "(agent_name, pattern_hash, trigger_conditions, skill_path, diagnosis, "
        "remediation, created_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        (
            agent_name,
            pattern_hash,
            str(conditions),
            str(skill_path),
            diagnosis[:2000],
            remediation[:2000],
        ),
    )
    row_id = cur.lastrowid
    # Index in FTS5 (standalone table — store skill_id for join/delete)
    conn.execute(
        "INSERT INTO prevention_skills_fts "
        "(skill_id, pattern_hash, agent_name, error_signature, diagnosis) "
        "VALUES (?, ?, ?, ?, ?)",
        (row_id, pattern_hash, agent_name, error_signature, diagnosis[:2000]),
    )
    conn.commit()
    return str(skill_path)


def apply_prevention(skill: dict, agent_name: str) -> tuple[bool, str]:
    """Apply the remediation from a prevention skill.

    Only known-safe actions auto-execute. Dangerous actions are reported but
    NOT executed (require human approval). Returns (success, message).
    """
    remediation = skill.get("remediation", "")
    low_rem = remediation.lower()
    # Dangerous remediations must NEVER auto-execute, even if a safe word
    # also appears (e.g. "pip_install X then restart"). Block first.
    DANGEROUS = ("pip_install", "pip install", "code_fix", "code fix",
                 "edit source", "modify code")
    if any(d in low_rem for d in DANGEROUS):
        return False, "Skill contains a dangerous remediation (pip_install/code_fix); requires human review"

    # Extract a known-safe action token from the remediation text.
    action = None
    for line in remediation.splitlines():
        low = line.lower()
        for a in SAFE_REMEDIATIONS:
            if a in low:
                action = a
                break
        if action:
            break

    if action is None:
        # No known-safe action found — cannot auto-apply.
        return False, "No safe auto-remediation in skill; requires human review"

    # Delegate to the heal executor for the safe action
    try:
        from observeco.heal import _execute_action
        ok, msg = _execute_action(action, {"agent_name": agent_name})
    except Exception as e:  # pragma: no cover
        return False, f"remediation execution error: {e}"

    # Record outcome
    _record_outcome(skill["id"], ok)
    if not ok:
        _maybe_deprecate(skill["id"])
    return ok, msg


def _record_outcome(skill_id: int, success: bool) -> None:
    db = Database()
    conn = db._get_conn()
    if success:
        conn.execute(
            "UPDATE prevention_skills SET success_count = success_count + 1, "
            "last_used_at = datetime('now') WHERE id=?",
            (skill_id,),
        )
    else:
        conn.execute(
            "UPDATE prevention_skills SET fail_count = fail_count + 1 "
            "WHERE id=?",
            (skill_id,),
        )
    conn.commit()


def _maybe_deprecate(skill_id: int) -> None:
    db = Database()
    conn = db._get_conn()
    row = conn.execute(
        "SELECT fail_count FROM prevention_skills WHERE id=?", (skill_id,)
    ).fetchone()
    if row and row["fail_count"] >= DEPRECATE_AFTER:
        conn.execute(
            "UPDATE prevention_skills SET deprecated=1 WHERE id=?", (skill_id,)
        )
        conn.commit()


def get_skill(skill_id: int) -> Optional[dict]:
    db = Database()
    conn = db._get_conn()
    r = conn.execute(
        "SELECT * FROM prevention_skills WHERE id=?", (skill_id,)
    ).fetchone()
    return dict(r) if r else None


def list_skills(agent_name: str | None = None) -> list[dict]:
    db = Database()
    conn = db._get_conn()
    if agent_name:
        rows = conn.execute(
            "SELECT * FROM prevention_skills WHERE agent_name=? ORDER BY created_at DESC",
            (agent_name,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM prevention_skills ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def remove_skill(skill_id: int) -> bool:
    db = Database()
    conn = db._get_conn()
    r = conn.execute(
        "SELECT skill_path FROM prevention_skills WHERE id=?", (skill_id,)
    ).fetchone()
    if not r:
        return False
    path = Path(r["skill_path"])
    if path.exists():
        path.unlink()
    conn.execute("DELETE FROM prevention_skills_fts WHERE skill_id=?", (skill_id,))
    conn.execute("DELETE FROM prevention_skills WHERE id=?", (skill_id,))
    conn.commit()
    return True
