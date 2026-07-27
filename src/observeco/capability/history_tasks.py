"""History-assisted canary task generation.

Mines real agent conversations from the Hermes session database, clusters them
by topic, and proposes canary task drafts. The LLM proposes assertions; the user
reviews and approves via the dashboard (obs-spec-060).

Design notes:
- Read-only access to ~/.hermes/state.db. Never writes to it.
- macOS only — path is hardcoded.
- Two-pass design: generic tasks (built_in=1) run via the existing adapter chain;
  user-defined tasks (built_in=0) run via HermesBenchmarkAdapter with -p default.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone

HERMES_STATE_DB = os.path.expanduser("~/.hermes/state.db")

_STOPWORDS = {
    "a", "an", "the", "of", "for", "to", "in", "on", "with", "and", "or",
    "is", "are", "was", "were", "this", "that", "my", "your", "i", "you",
    "it", "at", "by", "from", "be", "had", "has", "have", "do", "did",
}


def _connect_state_db(db_path: str = HERMES_STATE_DB) -> sqlite3.Connection:
    """Open the Hermes session DB read-only. Raises if missing."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Hermes state.db not found at {db_path}")
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def mine_sessions(
    db_path: str = HERMES_STATE_DB,
    source: str = "telegram",
    min_messages: int = 3,
    days: int = 30,
    limit: int = 10,
) -> list[dict]:
    """Extract qualifying sessions with their first user message.

    Returns list of {session_id, title, first_user_message, message_count}.
    Empty list on any error (missing DB, no rows).
    """
    try:
        conn = _connect_state_db(db_path)
    except (FileNotFoundError, sqlite3.Error):
        return []

    try:
        cutoff = time.time() - days * 86400
        rows = conn.execute(
            """
            SELECT id, title, message_count, started_at
            FROM sessions
            WHERE source = ? AND message_count >= ? AND started_at > ?
              AND title NOT LIKE '%test%'
            ORDER BY message_count DESC
            """,
            (source, min_messages, cutoff),
        ).fetchall()

        sessions = []
        for sid, title, msg_count, _started in rows:
            first = conn.execute(
                "SELECT content FROM messages WHERE session_id = ? AND role = 'user' "
                "ORDER BY timestamp ASC LIMIT 1",
                (sid,),
            ).fetchone()
            sessions.append({
                "session_id": sid,
                "title": title or "",
                "first_user_message": (first[0] if first else ""),
                "message_count": msg_count or 0,
            })
        return sessions[: limit * 3]  # oversample for clustering headroom
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _keywords(title: str) -> set[str]:
    """Extract non-stopword lowercase keywords from a title."""
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def cluster_sessions(sessions: list[dict], limit: int = 10) -> list[dict]:
    """Naive keyword-overlap clustering. One session kept per cluster.

    ponytail: naive keyword overlap, not embeddings. Ceiling: semantically
    related but lexically different topics won't cluster together. Upgrade path:
    sentence-transformers embeddings with cosine-similarity threshold.
    """
    # Union-find over sessions that share >=1 keyword.
    parent = list(range(len(sessions)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    kws = [_keywords(s["title"]) for s in sessions]
    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):
            if kws[i] and kws[j] and kws[i] & kws[j]:
                union(i, j)

    # Group by root, keep highest message_count per cluster.
    clusters: dict[int, dict] = {}
    for i, s in enumerate(sessions):
        root = find(i)
        if root not in clusters or s["message_count"] > clusters[root]["message_count"]:
            clusters[root] = s

    merged = sorted(clusters.values(), key=lambda s: s["message_count"], reverse=True)
    return merged[:limit]


def propose_assertions(
    session: dict, llm_api_key: str | None = None
) -> tuple[list[dict], bool]:
    """Propose 1-3 assertions for a session.

    Returns (assertions_list, llm_judge_unavailable_flag).

    Failure modes (obs-spec-060 §4.2a):
    - No LLM key → default contains assertion from title keywords, flag=True
    - LLM call fails / invalid YAML → empty assertions, flag=True
    """
    api_key = llm_api_key or os.environ.get("OBSERVECO_LLM_API_KEY") or os.environ.get("OLLAMA_CLOUD_API_KEY")
    title = session.get("title", "")
    title_kw = [w for w in _keywords(title)][:3]

    if not api_key:
        return ([{"type": "contains", "keywords": title_kw}] if title_kw else [], True)

    try:
        import requests

        prompt = (
            "Given this user request to an AI agent, propose 1-3 evaluation "
            "assertions as YAML. Assertion types:\n"
            "- llm_judge: {criteria: <what a correct answer must show>}\n"
            "- contains: {keywords: [<required phrases>]}\n\n"
            f"User request: {session.get('first_user_message', '')[:500]}"
        )
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=20,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        # Extract first YAML-ish block.
        block = text.strip()
        if "```" in block:
            block = block.split("```")[1].strip()
        parsed = __import__("yaml").safe_load(block)
        assertions = parsed if isinstance(parsed, list) else parsed.get("assertions", [])
        if not isinstance(assertions, list):
            return ([], True)
        return (assertions, False)
    except Exception:
        return ([], True)


def clean_prompt(text: str) -> str:
    """Strip Telegram metadata prefixes and quoted replies; cap at 500 words."""
    if not text:
        return ""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        # Strip leading [Name] or [Replying to: ...] prefixes.
        if re.match(r"^\[[^\]]+\]\s*$", line.strip()):
            continue
        if line.strip().startswith(">"):
            continue
        cleaned.append(line)
    out = "\n".join(cleaned).strip()
    words = out.split()
    if len(words) > 500:
        out = " ".join(words[:500])
    return out


def generate_drafts(limit: int = 10) -> list[dict]:
    """Mine → cluster → propose assertions → build draft dicts."""
    sessions = mine_sessions(limit=limit)
    if not sessions:
        return []
    clustered = cluster_sessions(sessions, limit=limit)

    drafts = []
    seen_ids: set[str] = set()
    date = datetime.now().strftime("%Y%m%d")
    for s in clustered:
        if not s.get("first_user_message"):
            print(f"  Skipped session {s['session_id'][:12]} — no user message found")
            continue
        assertions, unavailable = propose_assertions(s)
        slug = re.sub(r"[^a-z0-9]+", "-", s["title"].lower())[:30].strip("-")
        task_id = f"history-{slug}-{date}"
        # Dedup in case of slug collision.
        n = 1
        while task_id in seen_ids:
            task_id = f"history-{slug}-{date}-{n}"
            n += 1
        seen_ids.add(task_id)

        drafts.append({
            "id": task_id,
            "name": s["title"][:60],
            "description": f"Agent must handle: {s['first_user_message'][:120]}",
            "prompt": clean_prompt(s["first_user_message"]),
            "assertions": assertions,
            "timeout": 300,
            "trials": 2,
            "category": "operations",
            "difficulty": "medium",
            "source_session": s["session_id"],
            "built_in": 0,
            "llm_judge_unavailable": unavailable,
        })
    return drafts


def save_drafts_as_pending(drafts: list[dict], db=None) -> int:
    """Insert drafts into canary_task_drafts. Returns count inserted."""
    from observeco.db import Database

    database = db or Database()
    conn = database._get_conn()
    count = 0
    for d in drafts:
        conn.execute(
            """
            INSERT OR REPLACE INTO canary_task_drafts
            (id, name, description, prompt, assertions, category, difficulty,
             source_session, llm_judge_unavailable, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                d["id"],
                d.get("name", ""),
                d.get("description", ""),
                d.get("prompt", ""),
                json.dumps(d.get("assertions", [])),
                d.get("category"),
                d.get("difficulty", "medium"),
                d.get("source_session"),
                1 if d.get("llm_judge_unavailable") else 0,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        count += 1
    conn.commit()
    return count
