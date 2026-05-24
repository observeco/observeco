"""File indexing — read source, extract nodes, persist to graph DB."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from observeco.graph.db import GraphDB
from observeco.graph.extractor import compute_file_hash, extract_call_edges, extract_nodes


class Indexer:
    """Index Python source files into the code graph."""

    def __init__(self, db: Optional[GraphDB] = None):
        self.db = db or GraphDB()

    def index_file(self, file_path: str, source: Optional[str] = None) -> dict:
        """Index a single Python file. Returns stats."""
        if source is None:
            source = open(file_path, "r").read()

        content_hash = compute_file_hash(source)
        file_stat = os.stat(file_path)

        # Skip if unchanged
        if self.db.check_file_indexed(file_path, content_hash):
            return {"file": file_path, "status": "unchanged", "nodes": 0, "edges": 0}

        # Extract nodes
        raw_nodes = extract_nodes(file_path, source)

        if not raw_nodes:
            return {"file": file_path, "status": "no_nodes", "nodes": 0, "edges": 0}

        # Insert nodes into DB (keep track of IDs)
        node_count = 0
        for n in raw_nodes:
            nid = self.db.upsert_node(
                kind=n["kind"],
                name=n["name"],
                qualified_name=n["qualified_name"],
                file_path=n["file_path"],
                start_line=n["start_line"],
                end_line=n["end_line"],
                language=n["language"],
                docstring=n["docstring"],
                signature=n["signature"],
                visibility=n["visibility"],
                is_exported=bool(n["is_exported"]),
                is_async=bool(n["is_async"]),
                is_static=bool(n["is_static"]),
                decorators=n["decorators"],
            )
            n["_id"] = nid
            node_count += 1

        # Extract and insert edges
        edges = extract_call_edges(raw_nodes, source)
        for e in edges:
            src = e.get("source_id")
            tgt = e.get("target_id")
            if src and tgt:
                self.db.add_edge(src, tgt, e["kind"])

        # Record file
        self.db.record_file(
            file_path=file_path,
            content_hash=content_hash,
            language="python",
            size=file_stat.st_size,
            modified_at=int(file_stat.st_mtime),
        )

        return {
            "file": file_path,
            "status": "indexed",
            "nodes": node_count,
            "edges": len(edges),
        }

    def index_directory(self, directory: str, pattern: str = "**/*.py",
                        exclude_dirs: Optional[list[str]] = None) -> list[dict]:
        """Index all Python files in a directory tree."""
        exclude = set(exclude_dirs or ["__pycache__", ".git", "venv", ".venv",
                                        "node_modules", "dist", "build",
                                        ".eggs", "*.egg-info", ".mypy_cache",
                                        ".pytest_cache", "references"])
        results = []

        for pyfile in sorted(Path(directory).glob(pattern)):
            # Check exclusion
            parts = pyfile.parts
            if any(ex in parts for ex in exclude):
                continue
            if any(p.endswith(".egg-info") for p in parts):
                continue

            try:
                source = pyfile.read_text("utf-8")
                result = self.index_file(str(pyfile), source)
                results.append(result)
            except Exception as e:
                results.append({"file": str(pyfile), "status": "error", "error": str(e)})

        return results

    def clear_and_reindex(self, directory: str, pattern: str = "**/*.py") -> list[dict]:
        """Clear existing graph and reindex from scratch."""
        self.db.clear()
        return self.index_directory(directory, pattern)

    def remove_deleted_files(self, directory: str) -> int:
        """Remove graph data for files that no longer exist on disk."""
        conn = self.db._get_conn()
        cur = conn.execute("SELECT path FROM files")
        count = 0
        for row in cur.fetchall():
            if not os.path.exists(row["path"]):
                self.db.remove_file(row["path"])
                count += 1
        return count
