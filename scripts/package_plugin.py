"""Package the Claude Desktop extension without local configuration or data."""
import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "manifest.json", "mcp_server.py", "mcp_ui.py", "server.py",
    "config.example.json", "plugin-config.example.json", "openapi.json", "D3-LICENSE.txt",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Directory for the installable .mcpb")
    args = parser.parse_args()
    version = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["version"]
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f"my-skill-library-{version}.mcpb"
    files = [ROOT / name for name in FILES]
    files.extend(path for path in (ROOT / "web").rglob("*") if path.is_file())
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for path in sorted(files):
            bundle.write(path, path.relative_to(ROOT).as_posix())
    print(archive.resolve())


if __name__ == "__main__":
    main()
