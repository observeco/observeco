# CodeGraph Evaluation — 2026-05-24

**Repo:** github.com/colbymchenry/codegraph
**Version:** 0.9.4
**Stars:** +14.1K this week (#1 fastest growing GitHub repo)
**Claim:** Pre-indexed code knowledge graph for AI agents. 94% fewer tool calls, 77% faster exploration. 100% local.

## Architecture (from cloned source)

CodeGraph is a Node.js project (@colbymchenry/codegraph on npm) with this pipeline:

```
files → ExtractionOrchestrator (tree-sitter WASM) → DB (nodes/edges/files in SQLite FTS5)
              ↓
       ReferenceResolver (imports, name-matching, framework patterns)
              ↓
       GraphQueryManager / GraphTraverser (callers, callees, impact)
              ↓
       ContextBuilder (markdown/JSON for AI agent consumption)
```

### Core Components

| Component | Lines | Purpose |
|-----------|-------|---------|
| `src/extraction/languages/*.ts` | 1,839 | Per-language tree-sitter AST → graph node/edge mapping |
| `src/index.ts` | — | `CodeGraph` class: init/open/close, indexAll, sync, searchNodes, getCallers/getCallees, getImpactRadius, buildContext |
| `src/db/` | — | SQLite + FTS5. better-sqlite3 native, falls back to node-sqlite3-wasm |
| `src/resolution/` | — | Import resolution, name matching, framework detection |
| `src/graph/` | — | BFS/DFS, impact radius, path finding |
| `src/context/` | — | Markdown/JSON formatter for agent consumption |
| `src/mcp/` | — | MCP server (JSON-RPC over stdio) |
| `src/installer/` | — | Multi-agent config writer (Claude Code, Cursor, Codex, OpenCode) |
| **Total** | **31,295** | Full TypeScript codebase |

### Schema

```
nodes — id, kind, name, qualified_name, file_path, language, start/end line/col,
        docstring, signature, visibility, is_exported, is_async, is_static, decorators

edges — source → target with kind (calls, imports, extends, references, contains, etc.)

files — path, content_hash, language, size, modified_at, indexed_at

unresolved_refs — pending cross-file references

nodes_fts — FTS5 full-text search on name, qualified_name, docstring, signature
```

### Per-Language Extractors

Each is ~50-100 lines mapping tree-sitter node types → CodeGraph node/edge kinds:

```
functionTypes, classTypes, methodTypes, importTypes, callTypes, variableTypes
getSignature(), isAsync(), isStatic(), extractImport()
```

Python extractor: **52 lines**. The mapping is trivial — tree-sitter does the parsing, extractors just categorize.

### Framework Detection

Recognizes: Express, Laravel, Rails, Django, FastAPI, Flask, Spring, Gin, Axum, ASP.NET, Vapor, React Router, SvelteKit, Vue/Nuxt. Framework detection emits `route` nodes and `references` edges.

### MCP Integration

Exposes tools: search_nodes, get_callers, get_callees, get_impact_radius, build_context. Transport: JSON-RPC over stdio.

## Decision: Build Python-Native

**Do NOT install.** Reasoning:

1. **Node.js dependency is wrong for a Python ecosystem.** Adding npm for one tool creates fragility.
2. **Schema is 150 lines of SQL.** We can replicate with sqlite3 (stdlib).
3. **Only 2 languages matter.** Python (ObserveCo, Hermes scripts) and Bash. Not 18.
4. **Extraction logic per language is ~50 lines.** tree-sitter Python bindings exist (pip install tree-sitter).
5. **We own the data.** Direct SQLite access beats MCP protocol overhead.
6. **ObserveCo synergy.** Code intelligence = 4th dimension alongside token drift, memory debt, and health.

## Build Plan

### Phase 1: Core (estimated 4-6h)
- `observeco graph init` — creates .observeco/graph.db with compatible schema
- `observeco graph index` — tree-sitter parse Python → nodes + edges
- Python extractor (50 lines port from python.ts)
- FTS5 setup with triggers (copy pattern from CodeGraph schema)

### Phase 2: Dashboard (2-3h)
- "Code Graph" panel in dashboard: module dependency SVG via Mermaid
- API endpoint: /api/graph/query → node lookup + callers/callees

### Phase 3: Agent Integration (2-3h)
- MCP resource: observeco://graph/{query} for Hermes agents
- graph_query tool for direct usage

### Tests
- Index ObserveCo monorepo → verify function count > 50, edge count > 100
- Cross-file reference resolution: class in db.py referenced by server.py
