"""Graph database — SQLite + FTS5 for code intelligence."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Optional

from platformdirs import user_data_dir

SCHEMA_VERSION = 1
DB_DIR = Path(user_data_dir("observeco", "observeco"))
DB_PATH = DB_DIR / "graph.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS _meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,              -- function, class, method, variable, import, route
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,     -- module.FunctionName
    file_path TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'python',
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    docstring TEXT DEFAULT '',
    signature TEXT DEFAULT '',
    visibility TEXT DEFAULT 'public',  -- public, private, protected
    is_exported INTEGER DEFAULT 0,
    is_async INTEGER DEFAULT 0,
    is_static INTEGER DEFAULT 0,
    decorators TEXT DEFAULT '',
    indexed_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    kind TEXT NOT NULL,              -- calls, imports, extends, references, contains
    FOREIGN KEY (source_id) REFERENCES nodes(id),
    FOREIGN KEY (target_id) REFERENCES nodes(id)
);

CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'python',
    size INTEGER NOT NULL,
    modified_at INTEGER NOT NULL,
    indexed_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS unresolved_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_node_id INTEGER NOT NULL,
    ref_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line INTEGER NOT NULL,
    FOREIGN KEY (source_node_id) REFERENCES nodes(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    name, qualified_name, docstring, signature,
    content='nodes',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
    INSERT INTO nodes_fts(rowid, name, qualified_name, docstring, signature)
    VALUES (new.id, new.name, new.qualified_name, new.docstring, new.signature);
END;

CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
    INSERT INTO nodes_fts(nodes_fts, rowid, name, qualified_name, docstring, signature)
    VALUES ('delete', old.id, old.name, old.qualified_name, old.docstring, old.signature);
END;

CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
    INSERT INTO nodes_fts(nodes_fts, rowid, name, qualified_name, docstring, signature)
    VALUES ('delete', old.id, old.name, old.qualified_name, old.docstring, old.signature);
    INSERT INTO nodes_fts(rowid, name, qualified_name, docstring, signature)
    VALUES (new.id, new.name, new.qualified_name, new.docstring, new.signature);
END;

CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_nodes_qualified ON nodes(qualified_name);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges(kind);
CREATE INDEX IF NOT EXISTS idx_unresolved_node ON unresolved_refs(source_node_id);
"""


class GraphDB:
    """SQLite graph database for code intelligence."""

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(_SCHEMA_SQL)
        cur = conn.execute("SELECT value FROM _meta WHERE key='schema_version'")
        row = cur.fetchone()
        if row is None:
            conn.execute("INSERT INTO _meta (key, value) VALUES ('schema_version', ?)",
                         (str(SCHEMA_VERSION),))
        conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- Nodes --

    def upsert_node(self, kind: str, name: str, qualified_name: str,
                    file_path: str, start_line: int, end_line: int,
                    language: str = "python", docstring: str = "",
                    signature: str = "", visibility: str = "public",
                    is_exported: bool = False, is_async: bool = False,
                    is_static: bool = False, decorators: str = "") -> int:
        conn = self._get_conn()
        now = int(time.time())
        cur = conn.execute(
            """INSERT INTO nodes (kind, name, qualified_name, file_path, language,
               start_line, end_line, docstring, signature, visibility,
               is_exported, is_async, is_static, decorators, indexed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT DO NOTHING""",
            (kind, name, qualified_name, file_path, language,
             start_line, end_line, docstring[:2000], signature[:500], visibility,
             1 if is_exported else 0, 1 if is_async else 0, 1 if is_static else 0,
             decorators[:500], now),
        )
        conn.commit()
        # Check if it already existed
        existing = conn.execute(
            "SELECT id FROM nodes WHERE qualified_name=? AND file_path=?",
            (qualified_name, file_path)
        ).fetchone()
        if existing:
            return existing["id"]
        return cur.lastrowid

    def get_node_by_id(self, node_id: int) -> Optional[dict]:
        conn = self._get_conn()
        cur = conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_node_by_qualified_name(self, name: str) -> Optional[dict]:
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM nodes WHERE qualified_name=? ORDER BY file_path LIMIT 1",
            (name,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def search_nodes(self, query: str, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        cur = conn.execute(
            """SELECT nodes.*, rank
               FROM nodes_fts
               JOIN nodes ON nodes_fts.rowid = nodes.id
               WHERE nodes_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (query, limit),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_nodes_by_file(self, file_path: str) -> list[dict]:
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT * FROM nodes WHERE file_path=? ORDER BY start_line",
            (file_path,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_all_nodes(self, kind: Optional[str] = None) -> list[dict]:
        conn = self._get_conn()
        if kind:
            cur = conn.execute("SELECT * FROM nodes WHERE kind=? ORDER BY qualified_name", (kind,))
        else:
            cur = conn.execute("SELECT * FROM nodes ORDER BY qualified_name")
        return [dict(r) for r in cur.fetchall()]

    # -- Edges --

    def add_edge(self, source_id: int, target_id: int, kind: str) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR IGNORE INTO edges (source_id, target_id, kind)
               VALUES (?, ?, ?)""",
            (source_id, target_id, kind),
        )
        conn.commit()

    def get_callers(self, node_id: int) -> list[dict]:
        conn = self._get_conn()
        cur = conn.execute(
            """SELECT n.*, e.kind as edge_kind
               FROM edges e
               JOIN nodes n ON e.source_id = n.id
               WHERE e.target_id = ? AND e.kind = 'calls'
               ORDER BY n.qualified_name""",
            (node_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_callees(self, node_id: int) -> list[dict]:
        conn = self._get_conn()
        cur = conn.execute(
            """SELECT n.*, e.kind as edge_kind
               FROM edges e
               JOIN nodes n ON e.target_id = n.id
               WHERE e.source_id = ? AND e.kind = 'calls'
               ORDER BY n.qualified_name""",
            (node_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_dependencies(self, file_path: str) -> list[dict]:
        """Get all imports in a file (what it depends on)."""
        conn = self._get_conn()
        cur = conn.execute(
            """SELECT qualified_name, name, start_line, end_line, kind
               FROM nodes
               WHERE file_path=? AND kind='import'
               ORDER BY start_line""",
            (file_path,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_dependents(self, file_path: str) -> list[dict]:
        """Get all files that import modules from this file."""
        conn = self._get_conn()
        # Get the module name from this file
        # Convert file path to module name (e.g., src/observeco/db.py -> observeco.db)
        module_parts = file_path.replace(".py", "").split("/")
        try:
            src_idx = module_parts.index("src")
            module_parts = module_parts[src_idx + 1:]
        except ValueError:
            pass
        module_name = ".".join(module_parts)
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]

        # Find files that import this module
        cur = conn.execute(
            """SELECT DISTINCT file_path, qualified_name
               FROM nodes
               WHERE kind='import'
               AND (qualified_name=? OR qualified_name LIKE ?)
               AND file_path != ?
               ORDER BY file_path""",
            (module_name, f"{module_name}.%", file_path),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_impact_radius(self, node_id: int, depth: int = 2) -> list[dict]:
        """BFS up to N levels to find all transitively affected callers."""
        self._get_conn()
        visited = set()
        queue = [node_id]
        results = []
        for level in range(depth):
            if not queue:
                break
            next_queue = []
            for nid in queue:
                callers = self.get_callers(nid)
                for c in callers:
                    if c["id"] not in visited:
                        visited.add(c["id"])
                        c["impact_depth"] = level + 1
                        results.append(c)
                        next_queue.append(c["id"])
            queue = next_queue
        return results

    # -- Stats --

    def get_stats(self) -> dict:
        conn = self._get_conn()
        node_count = conn.execute("SELECT COUNT(*) as c FROM nodes").fetchone()["c"]
        edge_count = conn.execute("SELECT COUNT(*) as c FROM edges").fetchone()["c"]
        file_count = conn.execute("SELECT COUNT(*) as c FROM files").fetchone()["c"]
        kind_counts = conn.execute(
            "SELECT kind, COUNT(*) as c FROM nodes GROUP BY kind ORDER BY c DESC"
        ).fetchall()
        edge_kind_counts = conn.execute(
            "SELECT kind, COUNT(*) as c FROM edges GROUP BY kind ORDER BY c DESC"
        ).fetchall()
        return {
            "nodes": node_count,
            "edges": edge_count,
            "files": file_count,
            "node_kinds": {r["kind"]: r["c"] for r in kind_counts},
            "edge_kinds": {r["kind"]: r["c"] for r in edge_kind_counts},
        }

    # -- Maintenance --

    def clear(self) -> None:
        conn = self._get_conn()
        conn.executescript("DELETE FROM nodes_fts; DELETE FROM edges; DELETE FROM nodes; DELETE FROM files; DELETE FROM unresolved_refs;")
        conn.commit()

    def check_file_indexed(self, file_path: str, content_hash: str) -> bool:
        conn = self._get_conn()
        cur = conn.execute(
            "SELECT content_hash FROM files WHERE path=?",
            (file_path,),
        )
        row = cur.fetchone()
        return row is not None and row["content_hash"] == content_hash

    def record_file(self, file_path: str, content_hash: str, language: str,
                    size: int, modified_at: int) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO files (path, content_hash, language, size, modified_at, indexed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (file_path, content_hash, language, size, modified_at, int(time.time())),
        )
        conn.commit()

    def remove_file(self, file_path: str) -> None:
        """Remove all data for a deleted file."""
        conn = self._get_conn()
        nodes = conn.execute(
            "SELECT id FROM nodes WHERE file_path=?", (file_path,)
        ).fetchall()
        node_ids = [n["id"] for n in nodes]
        if node_ids:
            placeholders = ",".join("?" * len(node_ids))
            conn.execute(f"DELETE FROM edges WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})", node_ids * 2)
            conn.execute(f"DELETE FROM unresolved_refs WHERE source_node_id IN ({placeholders})", node_ids)
            conn.execute("DELETE FROM nodes WHERE file_path=?", (file_path,))
            # FTS cleanup
            conn.executescript("DELETE FROM nodes_fts WHERE rowid IN (SELECT id FROM nodes WHERE file_path = ?)")  # noqa — runs as script
        conn.execute("DELETE FROM files WHERE path=?", (file_path,))
        conn.commit()
