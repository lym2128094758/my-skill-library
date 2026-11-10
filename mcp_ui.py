"""Build a self-contained MCP App from the existing graph page."""
import re
from functools import lru_cache

import server


URI = "ui://my-skill-library/graph.html"
MIME = "text/html;profile=mcp-app"
RESOURCE = {"uri": URI, "name": "My Skill Library", "mimeType": MIME}


@lru_cache(maxsize=1)
def graph_html():
    web = server.ROOT / "web"
    page = (web / "index.html").read_text(encoding="utf-8")
    scripts = []

    def script(source):
        code = (web / source).read_text(encoding="utf-8")
        return "<script>" + re.sub(r"</script", r"<\\/script", code, flags=re.I) + "</script>"

    def collect(match):
        scripts.append(script(match[1]))
        return ""

    page = re.sub(r'<script defer src="/([^"?]+)(?:\?[^"]*)?"></script>', collect, page)
    css = (web / "styles.css").read_text(encoding="utf-8")
    page = re.sub(r'<link rel="stylesheet" href="/styles\.css[^"]*"\s*/>', lambda _: f"<style>{css}</style>", page)
    page = page.replace('class="brand" href="/"', 'class="brand"')
    return page.replace("</body>", "\n".join([script("mcp-app.js"), *scripts, "</body>"]))
