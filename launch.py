"""Start the local library and open its UI, or reuse a running instance."""
from __future__ import annotations

import json
import threading
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen

from server import API_VERSION, Handler, ThreadingHTTPServer, load_config


def main() -> None:
    config = load_config()
    host, port = config.get("host", "127.0.0.1"), int(config.get("port", 8765))
    browser_host = "127.0.0.1" if host in ("0.0.0.0", "", "::") else host
    if ":" in browser_host:
        browser_host = f"[{browser_host}]"
    url = f"http://{browser_host}:{port}"
    try:
        with urlopen(url + "/api/health", timeout=2) as response:
            health = json.load(response)
        running = isinstance(health, dict) and health.get("ok") is True and health.get("api_version") == API_VERSION
    except (OSError, URLError, ValueError):
        running = False
    if running:
        print(f"Skill library is already running: {url}")
        webbrowser.open(url)
        return
    try:
        service = ThreadingHTTPServer((host, port), Handler)
    except OSError as error:
        raise SystemExit(f"Cannot start on {host}:{port}: {error}") from error
    worker = threading.Thread(target=service.serve_forever, daemon=True)
    worker.start()
    print(f"Skill library: {url}")
    print("Keep this window open. Press Ctrl+C to stop the service.")
    try:
        webbrowser.open(url)
        worker.join()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        service.shutdown()
        service.server_close()


if __name__ == "__main__":
    main()
