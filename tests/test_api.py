import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import server


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        (root / "config.example.json").write_text(json.dumps({"skill_roots": ["skills"]}), encoding="utf-8")
        (root / "openapi.json").write_text((server.ROOT / "openapi.json").read_text(encoding="utf-8"), encoding="utf-8")
        for name, text in [("alpha-skill", "Use beta-skill."), ("beta-skill", "Example.")]:
            folder = root / "skills" / name
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Example\n---\n{text}", encoding="utf-8")
        self.globals = patch.multiple(server, ROOT=root, CONFIG_PATH=root / "config.json", RELATIONS_PATH=root / "data" / "relations.json")
        self.globals.start()
        self.http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.worker = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.worker.start()
        self.base = f"http://127.0.0.1:{self.http.server_port}"

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.worker.join()
        self.globals.stop()
        self.directory.cleanup()

    def request(self, path, method="GET", body=None, content_type="application/json"):
        payload = body if isinstance(body, bytes) else None if body is None else json.dumps(body).encode()
        request = Request(self.base + path, data=payload, method=method, headers={"Content-Type": content_type})
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            self.assertIn("application/json", response.headers["Content-Type"])
            return response.status, json.load(response)

    def test_bootstrap_relative_roots_graph_and_detail(self):
        status, graph = self.request("/api/skills")
        self.assertEqual(status, 200)
        self.assertTrue(server.CONFIG_PATH.exists())
        self.assertEqual(len(graph["nodes"]), 2)
        self.assertEqual(graph["edges"][0]["kind"], "mention")
        node = graph["nodes"][0]
        self.assertNotIn("content", node)
        status, detail = self.request("/api/skill?id=" + node["id"])
        self.assertEqual(status, 200)
        self.assertEqual(detail["node"], node)
        self.assertIn("---", detail["content"])

    def test_relation_lifecycle_is_undirected_and_idempotent(self):
        nodes = self.request("/api/skills")[1]["nodes"]
        body = {"source": nodes[0]["id"], "target": nodes[1]["id"]}
        self.assertTrue(self.request("/api/relations", "POST", body)[1]["changed"])
        reverse = {"source": body["target"], "target": body["source"]}
        self.assertFalse(self.request("/api/relations", "POST", reverse)[1]["changed"])
        self.assertEqual(len(self.request("/api/relations")[1]["relations"]), 1)
        self.assertEqual(len(self.request("/api/skills")[1]["manual"]), 1)
        self.assertTrue(self.request("/api/relations", "DELETE", reverse)[1]["changed"])
        self.assertFalse(self.request("/api/relations", "DELETE", body)[1]["changed"])

    def test_can_delete_stale_relation_without_source_files(self):
        server.RELATIONS_PATH.parent.mkdir()
        server.RELATIONS_PATH.write_text(json.dumps([{"source": "old-a", "target": "old-b", "kind": "manual"}]), encoding="utf-8")
        status, result = self.request("/api/relations", "DELETE", {"source": "old-a", "target": "old-b"})
        self.assertEqual(status, 200)
        self.assertTrue(result["changed"])

    def test_invalid_requests_return_json_and_do_not_write(self):
        for body in [b"{broken", [], None, {}, {"source": {}, "target": "b"}, {"source": "a", "target": "a"}, {"source": "a", "target": "b"}]:
            with self.subTest(body=body):
                status, result = self.request("/api/relations", "POST", body)
                self.assertEqual(status, 400)
                self.assertFalse(result["ok"])
        self.assertEqual(self.request("/api/relations", "POST", {}, "text/plain")[0], 415)
        self.assertEqual(self.request("/api/relations", "POST", {"source": "x" * 70000, "target": "b"})[0], 413)
        self.assertFalse(server.RELATIONS_PATH.exists())
        self.assertEqual(self.request("/api/skill")[0], 400)
        self.assertEqual(self.request("/api/skill?id=missing")[0], 404)
        self.assertEqual(self.request("/api/missing")[0], 404)

    def test_health_and_openapi_version_match(self):
        health = self.request("/api/health")[1]
        spec = self.request("/api/openapi.json")[1]
        self.assertTrue(health["ok"])
        self.assertEqual(health["api_version"], spec["info"]["version"])
        self.assertIn("delete", spec["paths"]["/api/relations"])

    def test_corrupt_storage_is_reported_without_overwrite(self):
        server.RELATIONS_PATH.parent.mkdir()
        server.RELATIONS_PATH.write_text("{broken", encoding="utf-8")
        self.assertEqual(self.request("/api/relations")[0], 500)
        self.assertEqual(self.request("/api/relations", "DELETE", {"source": "old-a", "target": "old-b"})[0], 500)
        self.assertEqual(server.RELATIONS_PATH.read_text(encoding="utf-8"), "{broken")


if __name__ == "__main__":
    unittest.main()
