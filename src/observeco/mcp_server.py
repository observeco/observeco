"""`observeco mcp serve` — MCP protocol server for agent queries.

v1.1 feature. Implements Model Context Protocol (JSON-RPC 2.0 over stdio).
"""
from __future__ import annotations

import json
import sys
from typing import Any, Optional

from observeco.db import Database


class MCPServer:
    def __init__(self):
        self.db = Database()

    def _make_response(self, request_id: Any, result: Any) -> dict:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _make_error(self, request_id: Any, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def _write(self, data: dict) -> None:
        sys.stdout.write(json.dumps(data) + "\n")
        sys.stdout.flush()

    def _build_fleet_summary(self) -> str:
        agents = self.db.get_agents()
        summary = self.db.get_agent_status_summary()
        lines = [f"Fleet: {len(agents)} agents"]
        alive = dead = error = 0
        for name, s in summary.items():
            status = s.get("status", "unknown")
            if status == "alive":
                alive += 1
            elif status == "dead":
                dead += 1
            else:
                error += 1
            lines.append(f"  {name}: {status} (latency={s.get('latency_ms',0):.0f}ms)")
        lines.append(f"Summary: {alive} alive, {dead} dead, {error} errors")
        return "\n".join(lines)

    def _build_agent_health(self, agent_name: str) -> str:
        summary = self.db.get_agent_status_summary()
        s = summary.get(agent_name, {})
        if not s:
            return f"Agent '{agent_name}' not found in pulse data."
        return (f"Agent: {agent_name}\nStatus: {s.get('status', 'unknown')}\n"
                f"Latency: {s.get('latency_ms', 0):.0f}ms\nLast check: {s.get('timestamp', 'N/A')}\n"
                f"Circuit tripped: {s.get('circuit_tripped', 0)}")

    def _build_agent_config(self, agent_name: str) -> str:
        agents = self.db.get_agents()
        a = next((x for x in agents if x.get("agent_name") == agent_name), None)
        if not a:
            return f"Agent '{agent_name}' not found in config."
        return (f"Agent: {a.get('agent_name', '?')}\nFramework: {a.get('framework', '?')}\n"
                f"Health check: {a.get('health_check', 'none')}\nActive: {a.get('is_active', 1)}")

    def _build_agent_errors(self, agent_name: str) -> str:
        errors = self.db.get_errors(agent_name, limit=10)
        if not errors:
            return f"No errors for '{agent_name}'."
        lines = [f"Recent errors for '{agent_name}':"]
        for e in errors:
            ts = e.get("timestamp", "?")
            etype = e.get("error_type", "?")
            msg = e.get("error_message", "")[:100]
            lines.append(f"  [{ts}] {etype}: {msg}")
        return "\n".join(lines)

    def _build_agent_context(self, agent_name: str) -> str:
        try:
            conn = self.db._get_conn()
            row = conn.execute(
                "SELECT * FROM chisel_trims WHERE agent_name=? ORDER BY timestamp DESC LIMIT 1",
                (agent_name,),
            ).fetchone()
            if row:
                d = dict(row)
                return (f"Token breakdown for '{agent_name}':\n"
                        f"  identity: {d.get('identity_tokens', 0)}\n  memory: {d.get('memory_tokens', 0)}\n"
                        f"  skills: {d.get('skills_tokens', 0)}\n  tools: {d.get('tools_tokens', 0)}\n"
                        f"  guidance: {d.get('guidance_tokens', 0)}\n  total: {d.get('total_tokens', 0)}\n"
                        f"  savings ratio: {d.get('savings_ratio', 0):.1%}")
        except Exception:
            pass
        return f"No token data for '{agent_name}'. Run `observeco chisel trim` first."

    def _build_alert(self, rule: str) -> str:
        return (f"Alert rule: {rule}\nStatus: configured (rule engine coming in v1.2)\n"
                f"Triggered: check dashboard for alert history")

    def _read_resource(self, uri: str) -> str:
        parts = uri.replace("observeco://", "").split("/")
        if parts[0] == "fleet":
            return self._build_fleet_summary()
        elif parts[0] == "graph" and len(parts) >= 2 and parts[1] == "stats":
            try:
                from observeco.graph.db import GraphDB
                gdb = GraphDB()
                stats = gdb.get_stats()
                lines = [
                    "Code Graph Stats:",
                    f"  Files: {stats.get('files', 0)}",
                    f"  Symbols: {stats.get('nodes', 0)}",
                    f"  Relations: {stats.get('edges', 0)}",
                ]
                for kind, count in stats.get("node_kinds", {}).items():
                    lines.append(f"  - {kind}: {count}")
                return "\n".join(lines)
            except Exception as e:
                return f"Graph stats error: {e}"
        elif parts[0] == "alert" and len(parts) >= 2:
            return self._build_alert(parts[1])
        elif len(parts) >= 2:
            agent_name, resource_type = parts[0], parts[1]
            if resource_type == "health":
                return self._build_agent_health(agent_name)
            elif resource_type == "config":
                return self._build_agent_config(agent_name)
            elif resource_type == "errors":
                return self._build_agent_errors(agent_name)
            elif resource_type == "context":
                return self._build_agent_context(agent_name)
        return f"Unknown resource: {uri}"

    def _handle_request(self, request: dict) -> Optional[dict]:
        method = request.get("method", "")
        params = request.get("params", {})
        rid = request.get("id")
        if method == "initialize":
            return self._make_response(rid, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"resources": {}, "tools": {}},
                "serverInfo": {"name": "observeco-mcp", "version": "0.1.0"},
            })
        elif method == "resources/list":
            agents = self.db.get_agents()
            resources = [
                {"uri": "observeco://fleet", "name": "Fleet Summary",
                 "description": "All agents health summary", "mimeType": "text/plain"},
            ]
            for a in agents:
                name = a.get("agent_name", a.get("name", ""))
                if name:
                    resources.append({"uri": f"observeco://{name}/health", "name": f"{name} Health",
                                       "description": f"Latest health for {name}", "mimeType": "text/plain"})
                    resources.append({"uri": f"observeco://{name}/config", "name": f"{name} Config",
                                       "description": f"Config for {name}", "mimeType": "text/plain"})
                    resources.append({"uri": f"observeco://{name}/errors", "name": f"{name} Errors",
                                       "description": f"Recent errors for {name}", "mimeType": "text/plain"})
                    resources.append({"uri": f"observeco://{name}/context", "name": f"{name} Context",
                                       "description": f"Token breakdown for {name}", "mimeType": "text/plain"})
            resources.append({"uri": "observeco://alert/_default", "name": "Default Alert",
                               "description": "Default alert rule status", "mimeType": "text/plain"})
            # Graph resources
            resources.append({"uri": "observeco://graph/stats", "name": "Graph Stats",
                               "description": "Code graph statistics", "mimeType": "text/plain"})
            return self._make_response(rid, {"resources": resources})
        elif method == "resources/read":
            uri = params.get("uri", "")
            text = self._read_resource(uri)
            return self._make_response(rid, {"contents": [{"uri": uri, "mimeType": "text/plain", "text": text}]})
        elif method == "tools/list":
            return self._make_response(rid, {
                "tools": [
                    {"name": "heal", "description": "Trigger healing on an agent",
                     "inputSchema": {"type": "object", "properties": {"agent_name": {"type": "string"},
                                       "auto_heal": {"type": "boolean"}}, "required": ["agent_name"]}},
                    {"name": "snapshot", "description": "Generate a snapshot",
                     "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}},
                                      "required": ["name"]}},
                    {"name": "pulse", "description": "Run a pulse check",
                     "inputSchema": {"type": "object", "properties": {"agent_name": {"type": "string"}},
                                      "required": ["agent_name"]}},
                    {"name": "graph_search", "description": "Search code graph symbols",
                     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"},
                                                                       "limit": {"type": "number"}},
                                      "required": ["query"]}},
                    {"name": "graph_callers", "description": "Find all functions that call a symbol",
                     "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}},
                                      "required": ["symbol"]}},
                    {"name": "graph_callees", "description": "Find all functions called by a symbol",
                     "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}},
                                      "required": ["symbol"]}},
                    {"name": "graph_impact", "description": "Find transitive callers (impact radius)",
                     "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"},
                                                                       "depth": {"type": "number"}},
                                      "required": ["symbol"]}},
                ]
            })
        elif method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            if name == "heal":
                agent_name = arguments.get("agent_name", "")
                summary = self.db.get_agent_status_summary()
                s = summary.get(agent_name, {})
                return self._make_response(rid, {"content": [{"type": "text", "text": f"heal executed on {agent_name}: status={s.get('status', 'unknown')}"}]})
            elif name == "snapshot":
                snapshot_name = arguments.get("name", "mcp-snapshot")
                try:
                    from observeco.snapshot import run_snapshot
                    run_snapshot(snapshot_name=snapshot_name)
                except Exception:
                    pass
                return self._make_response(rid, {"content": [{"type": "text", "text": f"Snapshot '{snapshot_name}' generated."}]})
            elif name == "pulse":
                agent_name = arguments.get("agent_name", "")
                pulses = self.db.get_recent_pulses(agent_name, limit=3)
                if pulses:
                    return self._make_response(rid, {"content": [{"type": "text", "text": str(pulses[0])}]})
                return self._make_response(rid, {"content": [{"type": "text", "text": f"No pulse data for {agent_name}"}]})
            elif name == "graph_search":
                try:
                    from observeco.graph.db import GraphDB
                    gdb = GraphDB()
                    query = arguments.get("query", "")
                    limit = arguments.get("limit", 10)
                    results = gdb.search_nodes(query, limit=limit)
                    if not results:
                        return self._make_response(rid, {"content": [{"type": "text", "text": f"No results for '{query}'"}]})
                    lines = [f"Graph search: '{query}' ({len(results)} results)"]
                    for r in results:
                        lines.append(f"  {r['kind']}: {r['qualified_name']} [{r['file_path']}:{r['start_line']}]")
                    return self._make_response(rid, {"content": [{"type": "text", "text": "\n".join(lines)}]})
                except Exception as e:
                    return self._make_response(rid, {"content": [{"type": "text", "text": f"Graph search error: {e}"}]})
            elif name == "graph_callers":
                try:
                    from observeco.graph.db import GraphDB
                    gdb = GraphDB()
                    symbol = arguments.get("symbol", "")
                    node = gdb.get_node_by_qualified_name(symbol)
                    if not node:
                        return self._make_response(rid, {"content": [{"type": "text", "text": f"Symbol not found: {symbol}"}]})
                    callers = gdb.get_callers(node["id"])
                    if not callers:
                        return self._make_response(rid, {"content": [{"type": "text", "text": f"No callers for {symbol}"}]})
                    lines = [f"Callers of {symbol}:"]
                    for c in callers:
                        lines.append(f"  ← {c['qualified_name']} [{c['file_path']}:{c['start_line']}]")
                    return self._make_response(rid, {"content": [{"type": "text", "text": "\n".join(lines)}]})
                except Exception as e:
                    return self._make_response(rid, {"content": [{"type": "text", "text": f"Graph callers error: {e}"}]})
            elif name == "graph_callees":
                try:
                    from observeco.graph.db import GraphDB
                    gdb = GraphDB()
                    symbol = arguments.get("symbol", "")
                    node = gdb.get_node_by_qualified_name(symbol)
                    if not node:
                        return self._make_response(rid, {"content": [{"type": "text", "text": f"Symbol not found: {symbol}"}]})
                    callees = gdb.get_callees(node["id"])
                    if not callees:
                        return self._make_response(rid, {"content": [{"type": "text", "text": f"No callees for {symbol}"}]})
                    lines = [f"Callees of {symbol}:"]
                    for c in callees:
                        lines.append(f"  → {c['qualified_name']} [{c['file_path']}:{c['start_line']}]")
                    return self._make_response(rid, {"content": [{"type": "text", "text": "\n".join(lines)}]})
                except Exception as e:
                    return self._make_response(rid, {"content": [{"type": "text", "text": f"Graph callees error: {e}"}]})
            elif name == "graph_impact":
                try:
                    from observeco.graph.db import GraphDB
                    gdb = GraphDB()
                    symbol = arguments.get("symbol", "")
                    depth = arguments.get("depth", 2)
                    node = gdb.get_node_by_qualified_name(symbol)
                    if not node:
                        return self._make_response(rid, {"content": [{"type": "text", "text": f"Symbol not found: {symbol}"}]})
                    impact = gdb.get_impact_radius(node["id"], depth=depth)
                    if not impact:
                        return self._make_response(rid, {"content": [{"type": "text", "text": f"No impact radius for {symbol} (depth={depth})"}]})
                    lines = [f"Impact radius of {symbol} (depth={depth}):"]
                    for i in impact:
                        lines.append(f"  Depth {i['impact_depth']}: {i['qualified_name']} [{i['file_path']}:{i['start_line']}]")
                    return self._make_response(rid, {"content": [{"type": "text", "text": "\n".join(lines)}]})
                except Exception as e:
                    return self._make_response(rid, {"content": [{"type": "text", "text": f"Graph impact error: {e}"}]})
            return self._make_error(rid, -32601, f"Tool not found: {name}")
        else:
            return self._make_error(rid, -32601, f"Method not found: {method}")

    def run_stdio(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self._handle_request(request)
                if response:
                    self._write(response)
            except json.JSONDecodeError as e:
                self._write(self._make_error(None, -32700, f"Parse error: {e}"))
            except Exception as e:
                self._write(self._make_error(None, -32603, f"Internal error: {e}"))

    def run_http(self, port: int) -> None:
        from http.server import BaseHTTPRequestHandler, HTTPServer
        class MCPHTTPHandler(BaseHTTPRequestHandler):
            server_instance = self
            def do_POST(self):
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                try:
                    request = json.loads(body)
                    response = self.server_instance._handle_request(request)
                    resp_body = json.dumps(response) if response else "{}"
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(resp_body.encode())
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
            def log_message(self, format, *args):
                pass
        server = HTTPServer(("127.0.0.1", port), MCPHTTPHandler)
        print(f"ObserveCo MCP server (HTTP) on http://127.0.0.1:{port}/mcp")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nMCP server stopped.")
            server.server_close()

def run_mcp_server(port: Optional[int] = None) -> None:
    server = MCPServer()
    if port:
        server.run_http(port)
    else:
        print("ObserveCo MCP server (stdio mode) - waiting for JSON-RPC on stdin...", file=sys.stderr)
        server.run_stdio()
