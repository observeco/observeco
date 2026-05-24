"""Python source code extractor — tree-sitter AST → graph nodes + edges."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import tree_sitter
import tree_sitter_python as tsp

PY_LANG = tree_sitter.Language(tsp.language())


def _get_text(node: tree_sitter.Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _get_docstring(function_node: tree_sitter.Node, source: bytes) -> str:
    """Get docstring from function/class definition."""
    block = None
    for child in function_node.children:
        if child.type == "block":
            block = child
            break
    if block and block.children:
        first = block.children[0]
        if first.type == "expression_statement" and first.children:
            expr = first.children[0]
            if expr.type == "string":
                txt = _get_text(expr, source).strip("'\"")
                import textwrap
                return textwrap.dedent(txt.strip()).strip()
    return ""


def _get_signature(func_node: tree_sitter.Node, source: bytes) -> str:
    text = _get_text(func_node, source)
    end = text.find(":\n") if ":\n" in text else text.find("\n")
    if end > 0:
        return text[:end].strip()
    return text.strip()


def _file_to_module(file_path: str) -> str:
    """Convert a file path to a Python module name."""
    path = Path(file_path)
    parts = list(path.parts)

    # Find meaningful start — strip up to and including 'src'
    try:
        src_idx = parts.index("src")
        parts = parts[src_idx + 1:]
    except ValueError:
        pass

    name = path.stem
    if name == "__init__":
        return ".".join(parts[:-1])
    return ".".join(parts[:-1] + [name])


def extract_nodes(file_path: str, source: str) -> list[dict]:
    """Extract all function/class/variable/import nodes from a Python file."""
    source_bytes = source.encode("utf-8")
    parser = tree_sitter.Parser(PY_LANG)
    tree = parser.parse(source_bytes)
    root = tree.root_node

    module_name = _file_to_module(file_path)
    nodes: list[dict] = []

    def _walk(node: tree_sitter.Node, qualifier: str = "") -> None:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if not name_node:
                return
            name = _get_text(name_node, source_bytes)
            qual_name = f"{qualifier}.{name}" if qualifier else f"{module_name}.{name}"
            decos = _get_decorators(node, source_bytes)
            is_async = any(c.type == "async" for c in node.children)
            is_static = "@staticmethod" in decos
            kind = "method" if qualifier and "." in qualifier else "function"
            start, end = node.start_point.row + 1, node.end_point.row + 1

            nodes.append({
                "kind": kind,
                "name": name,
                "qualified_name": qual_name,
                "file_path": file_path,
                "language": "python",
                "start_line": start,
                "end_line": end,
                "docstring": _get_docstring(node, source_bytes),
                "signature": _get_signature(node, source_bytes),
                "visibility": "public" if not name.startswith("_") else "private",
                "is_exported": int(not name.startswith("_") and not qualifier),
                "is_async": int(is_async),
                "is_static": int(is_static),
                "decorators": decos,
            })

            for child in node.children:
                _walk(child, qual_name)
            return

        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if not name_node:
                return
            name = _get_text(name_node, source_bytes)
            qual_name = f"{module_name}.{name}"
            decos = _get_decorators(node, source_bytes)
            start, end = node.start_point.row + 1, node.end_point.row + 1

            nodes.append({
                "kind": "class",
                "name": name,
                "qualified_name": qual_name,
                "file_path": file_path,
                "language": "python",
                "start_line": start,
                "end_line": end,
                "docstring": _get_docstring(node, source_bytes),
                "signature": "",
                "visibility": "public",
                "is_exported": 1,
                "is_async": 0,
                "is_static": 0,
                "decorators": decos,
            })

            for child in node.children:
                _walk(child, qual_name)
            return

        if node.type in ("import_statement", "import_from_statement"):
            # Extract imported module names — handle both `import X` and `from X import Y`
            for child in node.children:
                if child.type == "dotted_name":
                    name = _get_text(child, source_bytes)
                    start = node.start_point.row + 1
                    end = node.end_point.row + 1
                    # Deduplicate: skip if same import on same line
                    if not any(n["kind"] == "import" and n["name"] == name and n["start_line"] == start for n in nodes):
                        nodes.append({
                            "kind": "import",
                            "name": name,
                            "qualified_name": name,
                            "file_path": file_path,
                            "language": "python",
                            "start_line": start,
                            "end_line": end,
                            "docstring": "",
                            "signature": "",
                            "visibility": "public",
                            "is_exported": 1,
                            "is_async": 0,
                            "is_static": 0,
                            "decorators": "",
                        })
                        # For `from X import Y`, also emit the alias
                        if node.type == "import_from_statement":
                            nn = node.child_by_field_name("name")
                            if nn and nn.type == "dotted_name":
                                alias = _get_text(nn, source_bytes)
                                alias_qual = f"{name}.{alias}"
                                if not any(n["kind"] == "import" and n["name"] == alias_qual and n["start_line"] == start for n in nodes):
                                    nodes.append({
                                        "kind": "import",
                                        "name": alias,
                                        "qualified_name": alias_qual,
                                        "file_path": file_path,
                                        "language": "python",
                                        "start_line": start,
                                        "end_line": end,
                                        "docstring": "",
                                        "signature": "",
                                        "visibility": "public",
                                        "is_exported": 1,
                                        "is_async": 0,
                                        "is_static": 0,
                                        "decorators": "",
                                    })
            return

        if node.type == "assignment":
            if node.parent and node.parent.type == "module":
                for child in node.children:
                    if child.type == "identifier":
                        name = _get_text(child, source_bytes)
                        if not name.startswith("_"):
                            start = node.start_point.row + 1
                            end = node.end_point.row + 1
                            qual_name = f"{module_name}.{name}"
                            if not any(n["qualified_name"] == qual_name for n in nodes):
                                nodes.append({
                                    "kind": "variable",
                                    "name": name,
                                    "qualified_name": qual_name,
                                    "file_path": file_path,
                                    "language": "python",
                                    "start_line": start,
                                    "end_line": end,
                                    "docstring": "",
                                    "signature": "",
                                    "visibility": "public",
                                    "is_exported": 1,
                                    "is_async": 0,
                                    "is_static": 0,
                                    "decorators": "",
                                })
            return

        # Recurse into all other nodes (module root, blocks, etc.)
        for child in node.children:
            _walk(child, qualifier)

    _walk(root)
    return nodes


def _get_decorators(node: tree_sitter.Node, source: bytes) -> str:
    decos = []
    for child in node.children:
        if child.type == "decorator":
            decos.append(_get_text(child, source).strip())
    return ", ".join(decos)


def _find_function_node(root: tree_sitter.Node, name: str, source: bytes) -> Optional[tree_sitter.Node]:
    """Find a function_definition node by name."""
    def _search(n: tree_sitter.Node) -> Optional[tree_sitter.Node]:
        if n.type == "function_definition":
            nn = n.child_by_field_name("name")
            if nn and _get_text(nn, source) == name:
                return n
        for child in n.children:
            result = _search(child)
            if result:
                return result
        return None
    return _search(root)


def extract_call_edges(nodes: list[dict], source: str) -> list[dict]:
    """Extract call edges between function/method nodes."""
    source_bytes = source.encode("utf-8")
    parser = tree_sitter.Parser(PY_LANG)
    tree = parser.parse(source_bytes)

    name_map: dict[str, int] = {}
    for n in nodes:
        if n.get("_id"):
            name_map[n["qualified_name"]] = n["_id"]
            name_map[n["name"]] = n["_id"]

    edges: list[dict] = []

    def _find_call_targets(n: tree_sitter.Node) -> list[str]:
        targets = []
        if n.type == "call":
            func = n.child_by_field_name("function")
            if func:
                if func.type == "identifier":
                    targets.append(_get_text(func, source_bytes))
                elif func.type == "attribute":
                    attr = func.child_by_field_name("attribute")
                    if attr:
                        targets.append(_get_text(attr, source_bytes))
        for child in n.children:
            targets.extend(_find_call_targets(child))
        return targets

    for n in nodes:
        if n["kind"] in ("function", "method") and n.get("_id"):
            source_id = n["_id"]
            fn_node = _find_function_node(tree.root_node, n["name"], source_bytes)
            if fn_node:
                called_names = _find_call_targets(fn_node)
                for called in set(called_names):
                    target_id = name_map.get(called)
                    if target_id and target_id != source_id:
                        if not any(e["source_id"] == source_id and e["target_id"] == target_id for e in edges):
                            edges.append({
                                "source_id": source_id,
                                "target_id": target_id,
                                "kind": "calls",
                            })

    return edges


def compute_file_hash(source: str) -> str:
    return hashlib.sha256(source.encode()).hexdigest()
