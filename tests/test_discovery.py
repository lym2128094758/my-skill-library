import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mcp_server
import server
from skill_discovery import agent_roots, detect_agent, resolve_config


class HostDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.project = self.home / "work"
        self.project.mkdir()
        (self.project / ".git").mkdir()
        self.environment = patch.dict(os.environ, {
            "SKILL_LIBRARY_PROJECT": str(self.project),
            "SKILL_LIBRARY_HOME": str(self.home / "library"),
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        home_patch = patch("pathlib.Path.home", return_value=self.home)
        home_patch.start()
        self.addCleanup(home_patch.stop)
        for relative in (".codex/skills", ".claude/skills", ".dsh/skills", ".agents/skills",
                         "work/.dsh/skills", "work/.claude/skills", "work/.agents/skills"):
            directory = self.home / relative
            directory.mkdir(parents=True)
            skill = directory / "example"
            skill.mkdir()
            (skill / "SKILL.md").write_text("---\nname: sample-skill\n---\nExample.", encoding="utf-8")

    def test_agent_roots_never_fall_back_to_another_host(self):
        for agent in ("codex", "claude-code", "claude-desktop", "dsh"):
            roots = agent_roots(agent, self.project)
            expected = ".claude" if agent.startswith("claude") else "." + agent
            self.assertIn(str((self.home / expected / "skills").resolve()), roots)
            for other in (".codex", ".claude", ".dsh"):
                if other != expected:
                    self.assertNotIn(str((self.home / other / "skills").resolve()), roots)
        self.assertEqual(agent_roots("unknown", self.project), [])

    def test_installer_user_and_host_home_overrides_are_used(self):
        custom = self.home / "custom-dsh"
        (custom / "skills").mkdir(parents=True)
        with patch.dict(os.environ, {"DSH_HOME": str(custom)}):
            roots = agent_roots("dsh", self.project)
        self.assertIn(str(custom / "skills"), roots)
        self.assertNotIn(str(self.home / ".dsh/skills"), roots)

    def test_old_fixed_publisher_configuration_requires_explicit_manual_mode(self):
        publisher = {"skill_roots": ["C:/publisher/.codex/skills"]}
        roots = resolve_config(publisher, "dsh", self.project)["skill_roots"]
        self.assertNotIn(publisher["skill_roots"][0], roots)
        manual = resolve_config(dict(publisher, discovery="manual"), "dsh", self.project)
        self.assertEqual(manual["skill_roots"], publisher["skill_roots"])

    def test_profiles_and_service_identities_do_not_mix(self):
        libraries = []
        for agent in ("codex", "claude-code", "claude-desktop", "dsh"):
            with patch.dict(os.environ, {"SKILL_LIBRARY_AGENT": agent}):
                libraries.append(mcp_server.Library())
        self.assertEqual(len({library.home for library in libraries}), 4)
        self.assertEqual(len({library.identity for library in libraries}), 4)
        self.assertEqual(len({library.port for library in libraries}), 4)
        with patch.dict(os.environ, {"SKILL_LIBRARY_AGENT": "codex", "SKILL_LIBRARY_PROJECT": str(self.home)}):
            other_project = mcp_server.Library()
        self.assertNotEqual(libraries[0].identity, other_project.identity)
        self.assertNotEqual(libraries[0].port, other_project.port)

    def test_client_identity_is_used_when_no_manifest_host_was_set(self):
        library = mcp_server.Library()
        self.assertEqual(library.agent, "unknown")
        library.identify("DeepSeek Harness")
        self.assertEqual(library.agent, "dsh")
        with patch.dict(os.environ, {"SKILL_LIBRARY_AGENT": "claude-code"}):
            self.assertEqual(detect_agent("Codex"), "claude-code")

    def test_project_without_git_does_not_walk_into_another_home_configuration(self):
        project = self.home / "no-repo" / "project"
        project.mkdir(parents=True)
        own = self.home / "custom-dsh"
        shared = self.home / "custom-agents"
        (own / "skills").mkdir(parents=True)
        (shared / "skills").mkdir(parents=True)
        with patch.dict(os.environ, {"DSH_HOME": str(own), "DSH_AGENTS_HOME": str(shared)}):
            roots = agent_roots("dsh", project)
        self.assertEqual(set(roots), {str(own / "skills"), str(shared / "skills")})

    def test_scanner_uses_the_selected_host_even_with_old_codex_roots(self):
        config = self.home / "config.json"
        config.write_text(json.dumps({"skill_roots": ["C:/publisher/.codex/skills"]}), encoding="utf-8")
        resolver = lambda value: resolve_config(value, "dsh", self.project)
        with patch.multiple(server, CONFIG_PATH=config, CONFIG_RESOLVER=resolver):
            nodes, _ = server.scan_skills()
        self.assertTrue(nodes)
        self.assertTrue(all(".codex" not in node["path"] and ".claude" not in node["path"] for node in nodes))


if __name__ == "__main__":
    unittest.main()
