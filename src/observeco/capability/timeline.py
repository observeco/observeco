"""Config timeline detector — auto-detects SOUL.md, model, and tool changes.

obs-spec-053: Watches agent configuration files and records changes
in config_snapshots table for the timeline dashboard.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from observeco.db import Database

logger = logging.getLogger(__name__)

# How often to poll for config changes (seconds)
CONFIG_POLL_INTERVAL = 60


class ConfigTimelineDetector:
    """Detect configuration changes for all agents and record in config_snapshots.

    Checks three sources of change:
    1. SOUL.md content hash → prompt_update
    2. Hermes model config → model_switch
    3. Tool manifest hash → tool_update
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self._hermes_bin = self._find_hermes_bin()

    # ── Public API ───────────────────────────────────────────────────────

    def check_all_agents(self) -> list[dict]:
        """Check all detected agents for config changes.

        Returns list of new snapshot dicts (empty if no changes).
        """
        from observeco.config import load_config

        config = load_config()
        new_snapshots = []

        for agent in config.agents:
            try:
                snapshot = self._check_agent(agent.name, agent.config_path)
                if snapshot:
                    new_snapshots.append(snapshot)
            except Exception as exc:
                logger.debug("Config check failed for %s: %s", agent.name, exc)

        return new_snapshots

    def check_agent(self, agent_name: str) -> Optional[dict]:
        """Check a single agent for config changes.

        Returns new snapshot dict if a change was detected, None otherwise.
        """
        from observeco.config import load_config

        config = load_config()
        for agent in config.agents:
            if agent.name == agent_name:
                return self._check_agent(agent_name, agent.config_path)
        return None

    # ── Internal check ───────────────────────────────────────────────────

    def _check_agent(self, agent_name: str, config_path_str: Optional[str]) -> Optional[dict]:
        """Check one agent for any config changes.

        Compares current state against the last recorded snapshot.
        Returns a new snapshot dict if a change was detected, None otherwise.
        """
        conn = self.db._get_conn()

        # 1. Detect SOUL.md changes
        soul_result = self._detect_soul_change(agent_name, config_path_str)

        # 2. Detect model changes
        model_result = self._detect_model_change(agent_name)

        # 3. Detect tool changes
        tool_result = self._detect_tool_change(agent_name)

        # 4. Build current config hash from all sources
        current_hash = self._compute_config_hash(
            agent_name,
            soul_result.get("hash", "") if soul_result else "",
            model_result.get("model", "") if model_result else "",
            tool_result.get("tool_hash", "") if tool_result else "",
        )

        # 5. Get last snapshot for this agent
        last = conn.execute(
            "SELECT config_hash, change_type, created_at FROM config_snapshots "
            "WHERE agent_name = ? ORDER BY created_at DESC LIMIT 1",
            (agent_name,),
        ).fetchone()

        # 6. If nothing changed, return None
        if last and last["config_hash"] == current_hash:
            return None

        # 7. Determine change type and description
        if soul_result and soul_result.get("changed"):
            change_type = "prompt_update"
            description = soul_result.get("description", "SOUL.md modified")
        elif model_result and model_result.get("changed"):
            change_type = "model_switch"
            description = model_result.get("description", "Model changed")
        elif tool_result and tool_result.get("changed"):
            change_type = "tool_update"
            description = tool_result.get("description", "Tools updated")
        else:
            # First snapshot — baseline
            change_type = "baseline"
            description = "Initial config snapshot"

        # 8. Assign segment
        segment = self._assign_segment(agent_name, current_hash)

        # 9. Write snapshot
        now_iso = datetime.now(timezone.utc).isoformat()
        snapshot_id = str(uuid.uuid4())

        conn.execute(
            "INSERT INTO config_snapshots "
            "(id, agent_name, config_hash, change_type, description, segment, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (snapshot_id, agent_name, current_hash, change_type, description, segment, now_iso),
        )
        conn.commit()

        logger.info(
            "Config change detected: agent=%s type=%s hash=%s segment=%s",
            agent_name, change_type, current_hash[:12], segment,
        )

        return {
            "id": snapshot_id,
            "agent_name": agent_name,
            "config_hash": current_hash,
            "change_type": change_type,
            "description": description,
            "segment": segment,
            "created_at": now_iso,
        }

    # ── SOUL.md detection ───────────────────────────────────────────────

    def _detect_soul_change(self, agent_name: str, config_path_str: Optional[str]) -> Optional[dict]:
        """Detect SOUL.md changes by comparing file hash.

        Returns dict with {hash, changed, description} if SOUL.md exists,
        or None if no SOUL.md found.
        """
        soul_path = self._find_soul_path(agent_name, config_path_str)
        if soul_path is None or not soul_path.exists():
            return None

        current_hash = self._hash_file(soul_path)
        last_hash = self._get_last_soul_hash(agent_name)

        changed = last_hash is not None and current_hash != last_hash
        description = None
        if changed:
            description = self._summarize_soul_diff(soul_path)

        return {
            "hash": current_hash,
            "changed": changed,
            "description": description or "SOUL.md modified",
        }

    def _find_soul_path(self, agent_name: str, config_path_str: Optional[str]) -> Optional[Path]:
        """Find the SOUL.md path for an agent.

        Priority:
        1. config_path from AgentConfig (if it points to a SOUL.md)
        2. ~/.hermes/profiles/<name>/SOUL.md
        3. ~/.hermes/agents/<name>/SOUL.md
        """
        # Check config_path first
        if config_path_str:
            cp = Path(config_path_str)
            if cp.name == "SOUL.md" and cp.exists():
                return cp
            # Maybe it's a directory containing SOUL.md
            soul = cp / "SOUL.md"
            if soul.exists():
                return soul

        # Check profiles
        from observeco.dirs import hermes_home
        hh = hermes_home()
        if hh:
            soul = hh / "profiles" / agent_name / "SOUL.md"
            if soul.exists():
                return soul
            soul = hh / "agents" / agent_name / "SOUL.md"
            if soul.exists():
                return soul

        return None

    def _get_last_soul_hash(self, agent_name: str) -> Optional[str]:
        """Get the last known SOUL.md hash from the most recent snapshot."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT description FROM config_snapshots "
            "WHERE agent_name = ? AND change_type = 'prompt_update' "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_name,),
        ).fetchone()
        if row is None:
            return None
        # Extract hash from description if present
        desc = row["description"] or ""
        if "hash:" in desc:
            return desc.split("hash:")[-1].strip()[:12]
        return None

    def _summarize_soul_diff(self, soul_path: Path) -> str:
        """Generate a short summary of what changed in SOUL.md.

        ponytail: Simple first-line change detection. Upgrade path: use
        git diff if available.
        """
        return f"SOUL.md modified (hash:{self._hash_file(soul_path)[:12]})"

    # ── Model detection ─────────────────────────────────────────────────

    def _detect_model_change(self, agent_name: str) -> Optional[dict]:
        """Detect model changes by running hermes config show.

        Returns dict with {model, changed, description} or None if detection fails.
        """
        current_model = self._get_current_model()
        if current_model is None:
            return None

        last_model = self._get_last_model(agent_name)
        changed = last_model is not None and current_model != last_model

        return {
            "model": current_model,
            "changed": changed,
            "description": f"{last_model} → {current_model}" if changed else None,
        }

    def _get_current_model(self) -> Optional[str]:
        """Run hermes config show and extract the model string."""
        try:
            result = subprocess.run(
                [self._hermes_bin, "config", "show"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return None

            for line in result.stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("Model:") and "default" in stripped:
                    val = stripped.split(":", 1)[1].strip()
                    try:
                        import ast
                        model_dict = ast.literal_eval(val)
                        if isinstance(model_dict, dict):
                            provider = model_dict.get("provider", "")
                            model = model_dict.get("default", "")
                            if provider and model:
                                return f"{provider}/{model}"
                            return model or "unknown"
                    except (ValueError, SyntaxError):
                        pass
            return None
        except (subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.debug("Model detection failed: %s", exc)
            return None

    def _get_last_model(self, agent_name: str) -> Optional[str]:
        """Get the last known model from the most recent model_switch snapshot."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT description FROM config_snapshots "
            "WHERE agent_name = ? AND change_type = 'model_switch' "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_name,),
        ).fetchone()
        if row is None:
            return None
        desc = row["description"] or ""
        # Description format: "old_model → new_model"
        if "→" in desc:
            return desc.split("→")[-1].strip()
        return None

    # ── Tool detection ──────────────────────────────────────────────────

    def _detect_tool_change(self, agent_name: str) -> Optional[dict]:
        """Detect tool/config changes by hashing the agent's config section.

        ponytail: Simple hash of the agent's profile directory contents.
        Won't detect individual tool definition changes within a file.
        Upgrade path: parse the Hermes config YAML for tool definitions.
        """
        tool_hash = self._hash_tool_config(agent_name)
        if tool_hash is None:
            return None

        last_hash = self._get_last_tool_hash(agent_name)
        changed = last_hash is not None and tool_hash != last_hash

        return {
            "tool_hash": tool_hash,
            "changed": changed,
            "description": "Tools updated" if changed else None,
        }

    def _hash_tool_config(self, agent_name: str) -> Optional[str]:
        """Hash the agent's profile directory for tool/config changes."""
        from observeco.dirs import hermes_home
        hh = hermes_home()
        if hh is None:
            return None

        profile_dir = hh / "profiles" / agent_name
        if not profile_dir.exists():
            return None

        # Hash all .yaml, .yml, .json, .md files in the profile directory
        # (excluding SOUL.md which is tracked separately)
        hasher = hashlib.sha256()
        files_found = False
        for ext in ("*.yaml", "*.yml", "*.json"):
            for f in sorted(profile_dir.glob(ext)):
                if f.name == "SOUL.md":
                    continue
                try:
                    hasher.update(f.read_bytes())
                    files_found = True
                except Exception:
                    pass

        if not files_found:
            return None
        return hasher.hexdigest()[:12]

    def _get_last_tool_hash(self, agent_name: str) -> Optional[str]:
        """Get the last known tool hash from the most recent tool_update snapshot."""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT config_hash FROM config_snapshots "
            "WHERE agent_name = ? AND change_type = 'tool_update' "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_name,),
        ).fetchone()
        return row["config_hash"][:12] if row else None

    # ── Config hash ─────────────────────────────────────────────────────

    def _compute_config_hash(self, agent_name: str, soul_hash: str,
                              model: str, tool_hash: str) -> str:
        """Compute a composite config hash from all change sources."""
        raw = f"{agent_name}:{soul_hash}:{model}:{tool_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    # ── Segment assignment ──────────────────────────────────────────────

    def _assign_segment(self, agent_name: str, config_hash: str) -> str:
        """Assign a segment letter (A, B, C...) for a config_hash.

        If the hash already has a segment, reuse it.
        Otherwise, assign the next available letter.
        """
        conn = self.db._get_conn()

        # Check if this hash already has a segment
        row = conn.execute(
            "SELECT segment FROM config_snapshots "
            "WHERE agent_name = ? AND config_hash = ? AND segment IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_name, config_hash),
        ).fetchone()
        if row and row["segment"]:
            return row["segment"]

        # Get existing segments
        existing = conn.execute(
            "SELECT DISTINCT segment FROM config_snapshots "
            "WHERE agent_name = ? AND segment IS NOT NULL ORDER BY segment",
            (agent_name,),
        ).fetchall()
        used = {r["segment"] for r in existing if r["segment"]}

        # Assign next letter
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in used:
                return letter

        return "Z"  # fallback (26+ configs, unlikely)

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _hash_file(path: Path) -> str:
        """SHA-256 hash of a file's contents."""
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    @staticmethod
    def _find_hermes_bin() -> str:
        """Find the hermes binary path."""
        import shutil
        hermes = shutil.which("hermes")
        if hermes:
            return hermes
        # Common fallback paths
        for p in [
            Path.home() / ".hermes" / "hermes-agent" / "hermes",
            Path.home() / ".local" / "bin" / "hermes",
        ]:
            if p.exists():
                return str(p)
        return "hermes"  # hope it's on PATH
