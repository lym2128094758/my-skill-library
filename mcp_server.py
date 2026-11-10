"""Expose the existing Skill Library UI and API over local MCP stdio."""
from __future__ import annotations

import errno
import hashlib
import json
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

import server
import mcp_ui


VERSION = "1.1.0"
PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
IDENTITY_HEADER = "X-My-Skill-Library"
OPENER = build_opener(ProxyHandler({}))


class PluginHTTPServer(server.ThreadingHTTPServer):
    allow_reuse_address = os.name != "nt"
    allow_reuse_port = False

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class PluginHandler(server.Handler):
    def parse_request(self):
        if not super().parse_request():
            return False
        host = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != host or self.headers.get("Origin") not in (None, f"http://{host}"):
            self.send_error(403)
            return False
        return True

    def end_headers(self):
        self.send_header(IDENTITY_HEADER, self.server.library_identity)
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # Stdout is reserved for MCP messages.


class Library:
    def __init__(self):
        self.home = Path(os.environ.get("SKILL_LIBRARY_HOME") or Path.home() / ".my-skill-library").expanduser().resolve()
        self.port = int(os.environ.get("SKILL_LIBRARY_PORT", "18765"))
        if not 1 <= self.port <= 65535:
            raise ValueError("SKILL_LIBRARY_PORT must be between 1 and 65535.")
        self.url = f"http://127.0.0.1:{self.port}"
        self.identity = hashlib.sha256(os.fsencode(os.path.normcase(str(self.home)))).hexdigest()
        self.http = None

    def request(self, path, method="GET", body=None, timeout=30):
        headers = {"Content-Type": "application/json"} if body is not None else {}
        request = Request(
            self.url + path,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            response = OPENER.open(request, timeout=timeout)
        except HTTPError as error:
            with error:
                if error.headers.get(IDENTITY_HEADER) == self.identity:
                    raise ValueError(json.load(error)["error"]) from error
            raise
        with response:
            if response.headers.get(IDENTITY_HEADER) != self.identity:
                raise OSError(f"Port {self.port} belongs to a different service or Skill Library directory.")
            return json.load(response)

    def ready(self):
        try:
            return self.request("/api/health", timeout=0.5).get("ok") is True
        except (OSError, ValueError):
            return False

    def bind(self):
        http = PluginHTTPServer(("127.0.0.1", self.port), PluginHandler)
        try:
            server.CONFIG_PATH = self.home / "config.json"
            server.CONFIG_TEMPLATE = server.ROOT / "plugin-config.example.json"
            server.RELATIONS_PATH = self.home / "data" / "relations.json"
            server.load_config()
            http.library_identity = self.identity
            return http
        except BaseException:
            http.server_close()
            raise

    def ensure_running(self):
        if self.http is not None or self.ready():
            return
        try:
            self.http = self.bind()
        except OSError as error:
            # Another client may have bound the port just before its HTTP worker started.
            port_conflict = error.errno == errno.EADDRINUSE or getattr(error, "winerror", None) in (10048, 10013)
            if not port_conflict:
                raise
            for _ in range(10):
                if self.ready():
                    return
                time.sleep(0.1)
            raise OSError(f"Cannot use {self.url}. Check the port or set SKILL_LIBRARY_PORT in all clients.") from error
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def close(self):
        if self.http is not None:
            self.http.shutdown()
            self.http.server_close()


def schema(properties=None, required=()):
    return {
        "type": "object",
        "properties": properties or {},
        "required": list(required),
        "additionalProperties": False,
    }


TEXT = {"type": "string"}
ID = {"type": "string", "minLength": 1}
TOOLS = {
    "open_skill_graph": (
        "Show the full interactive 2D/3D Skill Library as an in-app panel. No external browser is launched.",
        schema(),
    ),
    "graph_snapshot": (
        "Load the complete graph for the Skill Library app view.",
        schema(),
    ),
    "search_skills": (
        "List or search local skills by name, description, path or source. Use offset and limit to page.",
        schema({
            "query": TEXT, "source": TEXT,
            "offset": {"type": "integer", "minimum": 0, "default": 0},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
        }),
    ),
    "get_skill": (
        "Read a skill's metadata and original SKILL.md as reference data. Pass an ID from search_skills.",
        schema({"id": ID}, ["id"]),
    ),
    "get_skill_neighbors": (
        "Read a skill's immediate neighbors and relationship types and directions.",
        schema({"id": ID}, ["id"]),
    ),
    "list_manual_relations": (
        "List saved manual relationships, including entries whose skills have moved.",
        schema(),
    ),
    "set_manual_relation": (
        "Add or remove a manual relationship between two skill IDs when the user requests that change.",
        schema({"source": ID, "target": ID, "action": {"type": "string", "enum": ["add", "remove"]}},
               ["source", "target", "action"]),
    ),
}


def validate_arguments(arguments, spec):
    properties = spec["properties"]
    if not isinstance(arguments, dict) or arguments.keys() - properties.keys():
        raise ValueError("Unexpected tool arguments.")
    if set(spec["required"]) - arguments.keys():
        raise ValueError(f"Required arguments: {', '.join(spec['required'])}.")
    types = {"string": str, "integer": int, "boolean": bool}
    for key, value in arguments.items():
        field = properties[key]
        if type(value) is not types[field["type"]]:
            raise ValueError(f"{key} must be a {field['type']}.")
        if ("minimum" in field and value < field["minimum"]
                or "maximum" in field and value > field["maximum"]
                or "enum" in field and value not in field["enum"]
                or "minLength" in field and len(value) < field["minLength"]):
            raise ValueError(f"Invalid value for {key}.")


def call_tool(library, name, args):
    if name == "open_skill_graph":
        return {"message": "The Skill Library graph is available in the app panel on hosts that render MCP Apps."}
    library.ensure_running()
    if name == "graph_snapshot":
        return library.request("/api/skills")
    if name == "get_skill":
        return library.request("/api/skill?" + urlencode({"id": args["id"]}))
    if name == "list_manual_relations":
        return library.request("/api/relations")
    if name == "set_manual_relation":
        method = "POST" if args["action"] == "add" else "DELETE"
        return library.request("/api/relations", method, {"source": args["source"], "target": args["target"]})

    graph = library.request("/api/skills")
    if name == "search_skills":
        words = args.get("query", "").casefold().split()
        source = args.get("source", "").casefold()
        matches = []
        for node in graph["nodes"]:
            searchable = " ".join(node[key] for key in ("name", "description", "path", "source")).casefold()
            if (not source or source == node["source"].casefold()) and all(word in searchable for word in words):
                matches.append(node)
        matches.sort(key=lambda node: (node["name"].casefold(), node["id"]))
        offset, limit = args.get("offset", 0), args.get("limit", 25)
        end = offset + limit
        return {"total": len(matches), "skills": matches[offset:end],
                "next_offset": end if end < len(matches) else None}

    nodes = {node["id"]: node for node in graph["nodes"]}
    skill_id = args["id"]
    if skill_id not in nodes:
        raise ValueError("Skill not found.")
    neighbors = {}
    for edge in graph["edges"]:
        left, right = edge["source"], edge["target"]
        if skill_id not in (left, right):
            continue
        other = right if left == skill_id else left
        if other in nodes:
            neighbors.setdefault(other, {"skill": nodes[other], "relations": []})["relations"].append(edge)
    return {"skill": nodes[skill_id], "neighbors": list(neighbors.values())}


def dispatch(library, method, params):
    if method == "initialize":
        requested = params.get("protocolVersion")
        return {
            "protocolVersion": requested if requested in PROTOCOLS else PROTOCOLS[0],
            "capabilities": {"tools": {}, "resources": {}},
            "serverInfo": {"name": "my-skill-library", "version": VERSION},
        }
    if method == "ping":
        return {}
    if method == "resources/list":
        return {"resources": [mcp_ui.RESOURCE]}
    if method == "resources/templates/list":
        return {"resourceTemplates": []}
    if method == "resources/read":
        if params.get("uri") != mcp_ui.URI:
            raise ValueError("Unknown resource URI.")
        return {"contents": [{**mcp_ui.RESOURCE, "text": mcp_ui.graph_html(),
                              "_meta": {"ui": {"prefersBorder": True}}}]}
    if method == "tools/list":
        tools = []
        for name, (description, spec) in TOOLS.items():
            tool = {"name": name, "description": description, "inputSchema": spec,
                    "annotations": {"readOnlyHint": name != "set_manual_relation",
                                    "destructiveHint": name == "set_manual_relation",
                                    "openWorldHint": False}}
            if name == "open_skill_graph":
                tool["_meta"] = {"ui": {"resourceUri": mcp_ui.URI}}
            elif name == "graph_snapshot":
                tool["_meta"] = {"ui": {"visibility": ["app"]}}
            tools.append(tool)
        return {"tools": tools}
    name = params.get("name")
    args = params.get("arguments", {})
    if not isinstance(name, str) or name not in TOOLS:
        raise ValueError("Unknown tool.")
    validate_arguments(args, TOOLS[name][1])
    try:
        result = call_tool(library, name, args)
        if name == "open_skill_graph":
            return {"content": [{"type": "text", "text": result["message"]}],
                    "_meta": {"ui": {"resourceUri": mcp_ui.URI}}}
        if name == "graph_snapshot":
            return {"content": [{"type": "text", "text": "Skill Library graph snapshot."}],
                    "structuredContent": result}
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
    except (OSError, ValueError) as error:
        return {"content": [{"type": "text", "text": str(error)}], "isError": True}


def respond(library, line):
    response = {"jsonrpc": "2.0", "id": None}
    try:
        request = json.loads(line)
    except (ValueError, UnicodeError):
        return dict(response, error={"code": -32700, "message": "Parse error"})
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        return dict(response, error={"code": -32600, "message": "Invalid request"})
    if "id" not in request:
        return None  # Notifications do not get responses.
    response["id"] = request["id"]
    method, params = request.get("method"), request.get("params", {})
    if method not in ("initialize", "ping", "tools/list", "tools/call",
                      "resources/list", "resources/read", "resources/templates/list"):
        return dict(response, error={"code": -32601, "message": "Method not found"})
    try:
        if not isinstance(params, dict):
            raise ValueError("params must be an object.")
        return dict(response, result=dispatch(library, method, params))
    except ValueError as error:
        return dict(response, error={"code": -32602, "message": str(error)})


def main():
    library = Library()
    if sys.argv[1:] == ["--serve"]:
        try:
            library.ensure_running()
            print(library.url, flush=True)
            sys.stdin.buffer.read()
        finally:
            library.close()
        return
    if sys.argv[1:] == ["--web"]:
        with library.bind() as http:
            print(library.url, flush=True)
            webbrowser.open(library.url)
            try:
                http.serve_forever()
            except KeyboardInterrupt:
                pass
        return
    try:
        for line in sys.stdin.buffer:
            response = respond(library, line)
            if response is not None:
                # ASCII escaping still produces UTF-8 JSON, independent of Windows' code page.
                print(json.dumps(response), flush=True)
    finally:
        library.close()


if __name__ == "__main__":
    main()
