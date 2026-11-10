"""Resolve skill directories from the current user's agent environment."""
from __future__ import annotations

import json
import os
from pathlib import Path


AGENTS = ("codex", "claude-code", "claude-desktop", "dsh")
PORTS = {"codex": 18766, "claude-code": 18767, "claude-desktop": 18768, "dsh": 18769, "unknown": 18770}
LABELS = {"codex": "Codex", "claude-code": "Claude Code", "claude-desktop": "Claude Desktop",
          "dsh": "DeepSeek Harness", "unknown": "未识别宿主"}


def detect_agent(client_name=""):
    explicit = os.environ.get("SKILL_LIBRARY_AGENT")
    if explicit:
        if explicit not in AGENTS:
            raise ValueError("SKILL_LIBRARY_AGENT must be codex, claude-code, claude-desktop or dsh.")
        return explicit
    name = client_name.casefold() if isinstance(client_name, str) else ""
    if "codex" in name:
        return "codex"
    if "claude" in name:
        return "claude-code" if "code" in name else "claude-desktop"
    if "deepseek" in name or name.startswith("dsh"):
        return "dsh"
    if os.environ.get("DSH_PROFILE_DIR"):
        return "dsh"
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        return "claude-code"
    return "unknown"


def configured_path(variable, default):
    return Path(os.path.expandvars(os.environ.get(variable) or str(default))).expanduser().resolve()


def project_path():
    value = os.environ.get("SKILL_LIBRARY_PROJECT") or os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(value).expanduser().resolve() if value else Path.cwd().resolve()


def agent_roots(agent, project):
    home = Path.home()
    shared = configured_path("DSH_AGENTS_HOME", home / ".agents") if agent == "dsh" else home / ".agents"
    if agent == "codex":
        agent_home = configured_path("CODEX_HOME", home / ".codex")
        roots = [agent_home / "skills", shared / "skills"]
        project_folders = (".agents/skills", ".codex/skills")
    elif agent in ("claude-code", "claude-desktop"):
        agent_home = configured_path("CLAUDE_CONFIG_DIR", home / ".claude")
        roots = [agent_home / "skills"]
        project_folders = (".claude/skills",) if agent == "claude-code" else ()
    elif agent == "dsh":
        agent_home = configured_path("DSH_HOME", home / ".dsh")
        roots = [agent_home / "skills", shared / "skills"]
        project_folders = (".dsh/skills", ".agents/skills")
        bundled = os.environ.get("DSH_BUNDLED_SKILL_DIR")
        if bundled:
            roots.append(Path(bundled).expanduser().resolve())
    else:
        return []

    # Installed plugin paths come from this user's host registry, never a bundled snapshot.
    registry = agent_home / "plugins" / "installed_plugins.json"
    try:
        installed = json.loads(registry.read_text(encoding="utf-8"))
        for entries in installed.get("plugins", {}).values():
            for entry in entries if isinstance(entries, list) else []:
                if isinstance(entry, dict) and isinstance(entry.get("installPath"), str):
                    plugin_path = Path(entry["installPath"]).expanduser()
                    if plugin_path.is_absolute():
                        roots.append(plugin_path / "skills")
    except (OSError, ValueError, AttributeError):
        pass

    ancestors = (project, *project.parents)
    boundary = next((folder for folder in ancestors if (folder / ".git").exists()), project)
    for folder in ancestors:
        roots.extend(folder / relative for relative in project_folders)
        if folder == boundary:
            break
    return list(dict.fromkeys(str(root.resolve()) for root in roots if root.is_dir()))


def resolve_config(config, agent, project):
    """Explicit manual mode is required to replace host discovery with a fixed list."""
    result = dict(config)
    mode = result.get("discovery", "agent")
    if mode not in ("agent", "manual"):
        raise ValueError("discovery must be agent or manual.")
    if mode == "agent":
        result["skill_roots"] = agent_roots(agent, project)
    result["discovery"] = mode
    result["agent"] = agent
    result["agent_label"] = LABELS[agent]
    return result
