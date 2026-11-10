from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
CONFIG_TEMPLATE = None
RELATIONS_PATH = ROOT / "data" / "relations.json"
RELATIONS_LOCK = threading.Lock()
API_VERSION = "1.0.0"
MAX_BODY_BYTES = 65536
STOP_WORDS = {
    "about", "after", "also", "and", "any", "are", "based", "before", "being",
    "between", "both", "can", "could", "does", "each", "from", "have", "into",
    "just", "more", "most", "only", "other", "should", "some", "such", "than",
    "that", "their", "them", "then", "there", "these", "they", "this", "through",
    "under", "using", "when", "where", "which", "while", "with", "within", "would",
    "your", "you", "skill", "skills", "user", "users", "help", "use", "used", "using",
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        template = CONFIG_TEMPLATE or ROOT / "config.example.json"
        CONFIG_PATH.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise OSError("Invalid JSON in config.json") from error
    if not isinstance(config, dict) or not isinstance(config.get("skill_roots", []), list):
        raise OSError("Configuration must be an object with a skill_roots array")
    if any(not isinstance(root, str) or not root for root in config.get("skill_roots", [])):
        raise OSError("skill_roots must contain non-empty path strings")
    return config


def parse_frontmatter(text: str) -> tuple[str | None, str | None]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", text, flags=re.S)
    if not match:
        return None, None
    block = match.group(1)
    name_match = re.search(r"(?m)^name:\s*['\"]?([^\n'\"]+)['\"]?\s*$", block)
    desc_match = re.search(r"(?m)^description:\s*(.*(?:\n(?:[ \t]+.*|[ \t]*$))*)", block)
    name = name_match.group(1).strip() if name_match else None
    description = desc_match.group(1).strip() if desc_match else None
    if description:
        description = re.sub(r"\n[ \t]*", " ", description).strip(" >-\t")
        description = re.sub(r"\s+", " ", description)
    return name, description


def source_label(root: Path, skill_file: Path) -> str:
    normalized = root.as_posix().lower()
    if "/.codex/skills" in normalized:
        return "个人技能"
    if "ducktor" in normalized:
        return "Ducktor 插件"
    if "openai-bundled" in normalized:
        return "OpenAI 内置"
    if "openai-primary-runtime" in normalized:
        return "OpenAI 运行时"
    if "openai-curated-remote" in normalized:
        relative = skill_file.relative_to(root)
        return f"插件 · {relative.parts[0]}" if len(relative.parts) > 2 else "插件"
    return root.name


def token_set(text: str) -> set[str]:
    words = set(re.findall(r"[a-z][a-z0-9_-]{2,}", text.lower())) - STOP_WORDS
    cjk = re.findall(r"[\u3400-\u9fff]+", text)
    for chunk in cjk:
        if len(chunk) <= 4:
            words.add(chunk)
        else:
            words.update(chunk[i : i + 2] for i in range(len(chunk) - 1))
    return words


def reference_edges(entries: dict[str, dict]) -> dict[tuple[str, str], dict]:
    """Resolve explicit skill names, preserving mention direction and ambiguity."""
    aliases: dict[str, set[str]] = {}
    for skill_id, entry in entries.items():
        for name in (entry["name"], entry["slug"]):
            if len(name) >= 4:
                aliases.setdefault(name.casefold(), set()).add(skill_id)
    edges: dict[tuple[str, str], dict] = {}
    for source_id, entry in entries.items():
        body = re.sub(r"\A---\s*\n.*?\n---\s*", "", entry["content"], count=1, flags=re.S).casefold()
        for alias, targets in aliases.items():
            # Generic words such as 'documents' need explicit code/link markup.
            token = re.escape(alias)
            pattern = rf"(?<![\w-]){token}(?![\w-])" if "-" in alias else rf"(?:`{token}`|\[\[{token}(?:\||\]\])|[/(]{token}/)"
            if not re.search(pattern, body):
                continue
            candidates = [target for target in targets if target != source_id and entries[target]["name"].casefold() != entry["name"].casefold()]
            same_group = [target for target in candidates if entries[target]["group"] == entry["group"]]
            candidates = same_group or candidates
            if len(candidates) != 1:
                continue
            target_id = candidates[0]
            left, right = sorted((source_id, target_id))
            edge = edges.setdefault((left, right), {"source": left, "target": right, "kind": "mention", "forward": False, "backward": False})
            edge["forward" if source_id == left else "backward"] = True
    return edges


def scan_skills() -> tuple[list[dict], list[dict]]:
    config = load_config()
    entries: dict[str, dict] = {}
    for root_value in config.get("skill_roots", []):
        root = Path(os.path.expandvars(root_value)).expanduser()
        if not root.is_absolute():
            root = CONFIG_PATH.parent / root
        if not root.exists() or not root.is_dir():
            continue
        root_resolved = root.resolve()
        for file_path in root.rglob("SKILL.md"):
            try:
                resolved = file_path.resolve(strict=True)
                if not resolved.is_relative_to(root_resolved):
                    continue
                content = resolved.read_text(encoding="utf-8", errors="replace")
            except (OSError, RuntimeError):
                continue
            name, description = parse_frontmatter(content)
            folder_slug = file_path.parent.name
            slug = (name or folder_slug).strip()
            skill_id = hashlib.sha1(str(resolved).lower().encode("utf-8")).hexdigest()[:14]
            source = source_label(root, file_path)
            group = "个人技能" if source == "个人技能" else source.split(" · ", 1)[-1]
            entries[skill_id] = {
                "id": skill_id,
                "name": slug,
                "slug": folder_slug,
                "description": description or "暂无说明",
                "source": source,
                "group": group,
                "path": str(resolved),
                "content": content,
                "tokens": token_set(f"{slug} {description or ''}"),
            }

    auto_edges = reference_edges(entries)

    # Shared, specific topic terms make a light-weight, editable starting graph.
    docs = {key: entry["tokens"] for key, entry in entries.items()}
    frequencies: dict[str, int] = {}
    for terms in docs.values():
        for term in terms:
            frequencies[term] = frequencies.get(term, 0) + 1
    ranked: dict[str, list[tuple[float, str]]] = {key: [] for key in entries}
    ids = list(entries)
    for i, left_id in enumerate(ids):
        left_terms = docs[left_id]
        for right_id in ids[i + 1 :]:
            right_terms = docs[right_id]
            shared = left_terms & right_terms
            if not shared:
                continue
            weight = sum(1 / (1 + frequencies.get(term, 1)) for term in shared)
            total = sum(1 / (1 + frequencies.get(term, 1)) for term in left_terms | right_terms)
            score = weight / total if total else 0
            if score >= 0.12 and len(shared) >= 2:
                ranked[left_id].append((score, right_id))
                ranked[right_id].append((score, left_id))
    for node_id, neighbors in ranked.items():
        for score, neighbor_id in sorted(neighbors, reverse=True)[:2]:
            left, right = sorted((node_id, neighbor_id))
            auto_edges.setdefault((left, right), {"source": left, "target": right, "kind": "topic"})

    nodes = [
        {key: value for key, value in entry.items() if key not in {"content", "tokens"}}
        for entry in entries.values()
    ]
    return nodes, list(auto_edges.values())


def read_relations() -> list[dict]:
    try:
        relations = json.loads(RELATIONS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as error:
        raise OSError("Invalid JSON in manual relations file") from error
    if not isinstance(relations, list) or any(
        not isinstance(item, dict) or item.get("kind") != "manual"
        or not isinstance(item.get("source"), str) or not isinstance(item.get("target"), str)
        for item in relations
    ):
        raise OSError("Invalid manual relations file")
    return relations


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def end_headers(self):
        if not urlparse(self.path).path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        try:
            self.get_resource()
        except (OSError, ValueError) as error:
            self.send_json({"ok": False, "error": str(error)}, status=500)

    def get_resource(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "api_version": API_VERSION})
            return
        if parsed.path == "/api/openapi.json":
            self.send_json(json.loads((ROOT / "openapi.json").read_text(encoding="utf-8")))
            return
        if parsed.path == "/api/relations":
            self.send_json({"relations": read_relations()})
            return
        if parsed.path == "/api/skills":
            nodes, edges = scan_skills()
            manual = read_relations()
            self.send_json({"nodes": nodes, "edges": edges + manual, "manual": manual})
            return
        if parsed.path == "/api/skill":
            skill_id = parse_qs(parsed.query).get("id", [""])[0]
            if not skill_id:
                self.send_json({"ok": False, "error": "Missing id"}, status=400)
                return
            nodes, _ = scan_skills()
            node = next((item for item in nodes if item["id"] == skill_id), None)
            if not node:
                self.send_json({"ok": False, "error": "Skill not found"}, status=404)
                return
            content = Path(node["path"]).read_text(encoding="utf-8", errors="replace")
            self.send_json({"node": node, "content": content})
            return
        if parsed.path.startswith("/api/"):
            self.send_json({"ok": False, "error": "Not found"}, status=404)
            return
        super().do_GET()

    def do_POST(self):
        self.change_relation(delete=False)

    def do_DELETE(self):
        self.change_relation(delete=True)

    def change_relation(self, delete: bool):
        if urlparse(self.path).path != "/api/relations":
            self.send_json({"ok": False, "error": "Not found"}, status=404)
            return
        try:
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self.send_json({"ok": False, "error": "Content-Type must be application/json"}, status=415)
                return
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY_BYTES:
                self.send_json({"ok": False, "error": "JSON body must be 1 to 65536 bytes"}, status=413 if size > MAX_BODY_BYTES else 400)
                return
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("JSON body must be an object")
            source = body.get("source")
            target = body.get("target")
            if not isinstance(source, str) or not isinstance(target, str) or not source or not target:
                raise ValueError("source and target must be non-empty strings")
            if source == target:
                raise ValueError("A skill cannot be linked to itself")
            if not delete:
                nodes, _ = scan_skills()
                valid_ids = {node["id"] for node in nodes}
                if source not in valid_ids or target not in valid_ids:
                    raise ValueError("Unknown skill")
            left, right = sorted((source, target))
            relation = {"source": left, "target": right, "kind": "manual"}
            with RELATIONS_LOCK:
                current = read_relations()
                changed = relation in current if delete else relation not in current
                if delete:
                    current = [item for item in current if item != relation]
                elif changed:
                    current.append(relation)
                if changed:
                    RELATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
                    temporary = RELATIONS_PATH.with_suffix(".json.tmp")
                    temporary.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
                    temporary.replace(RELATIONS_PATH)
            self.send_json({"ok": True, "relation": relation, "changed": changed})
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            self.send_json({"ok": False, "error": str(error)}, status=400)
        except OSError as error:
            self.send_json({"ok": False, "error": str(error)}, status=500)

    def send_json(self, payload: dict, status: int = 200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


if __name__ == "__main__":
    config = load_config()
    server = ThreadingHTTPServer((config.get("host", "127.0.0.1"), int(config.get("port", 8765))), Handler)
    print(f"Skill 库已启动：http://{config.get('host', '127.0.0.1')}:{config.get('port', 8765)}")
    print("按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()
