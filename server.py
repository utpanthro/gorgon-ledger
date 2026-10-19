"""Local server for Gorgon Ledger with file-backed save data."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "src"
PORT = int(os.environ.get("GORGON_PORT", "4173"))
SAVE_PATH = Path(
    os.environ.get("GORGON_SAVE_PATH", str(ROOT / "save-data" / "gorgon-ledger.json"))
).resolve()
MAX_BODY_BYTES = 2 * 1024 * 1024
SAVE_LOCK = threading.Lock()
LEGACY_REDIRECTS = {
    "/food.html": "/foods/",
    "/foods.json": "/foods/data.json",
    "/src/foods/": "/foods/",
    "/src/foods/data.json": "/foods/data.json",
    "/npcs.html": "/npcs/",
    "/npc.html": "/npcs/detail.html",
    "/npc-quests.json": "/npcs/quests.json",
    "/npc-zones.json": "/npcs/zones.json",
    "/src/npcs/": "/npcs/",
    "/src/npcs/detail.html": "/npcs/detail.html",
    "/src/npcs/quests.json": "/npcs/quests.json",
    "/src/npcs/zones.json": "/npcs/zones.json",
    "/quests.html": "/quests/",
    "/src/quests/": "/quests/",
    "/skill.html": "/skills/detail.html",
    "/skill-details.json": "/skills/details.json",
    "/skill-recipes.json": "/skills/recipes.json",
    "/src/skills/": "/skills/",
    "/src/skills/detail.html": "/skills/detail.html",
    "/src/skills/details.json": "/skills/details.json",
    "/src/skills/recipes.json": "/skills/recipes.json",
    "/src/skills/teleport-spots.json": "/skills/teleport-spots.json",
    "/teleport-spots.json": "/skills/teleport-spots.json",
    "/storage.js": "/shared/storage.js",
    "/src/shared/storage.js": "/shared/storage.js",
    "/favicon.svg": "/assets/favicon.svg",
    "/src/assets/favicon.svg": "/assets/favicon.svg",
}


def read_save() -> tuple[bool, dict[str, str]]:
    if not SAVE_PATH.exists():
        return False, {}
    with SAVE_PATH.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    data = document.get("data", {})
    if not isinstance(data, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in data.items()
    ):
        raise ValueError("Save file contains invalid data")
    return True, data


def write_save(data: dict[str, str]) -> str:
    saved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    document = {"version": 1, "savedAt": saved_at, "data": data}
    SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = SAVE_PATH.with_suffix(SAVE_PATH.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, SAVE_PATH)
    return saved_at


class GorgonLedgerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def redirect_legacy_path(self) -> bool:
        parsed = urlparse(self.path)
        if parsed.path not in LEGACY_REDIRECTS:
            return False
        location = LEGACY_REDIRECTS[parsed.path]
        if parsed.query:
            location += f"?{parsed.query}"
        self.send_response(308)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def do_HEAD(self) -> None:
        if self.redirect_legacy_path():
            return
        super().do_HEAD()

    def do_OPTIONS(self) -> None:
        if urlparse(self.path).path != "/api/save":
            self.send_error(404)
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        if self.redirect_legacy_path():
            return
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(200, {"ok": True, "storage": "file"})
            return
        if path == "/api/save":
            try:
                with SAVE_LOCK:
                    exists, data = read_save()
                self.send_json(200, {"version": 1, "exists": exists, "data": data})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(500, {"error": f"Could not read the local save: {error}"})
            return
        if path == "/save-data" or path.startswith("/save-data/"):
            self.send_error(404)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/save":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_BYTES:
                self.send_json(413, {"error": "Save payload is empty or too large"})
                return
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            data = payload.get("data")
            if not isinstance(data, dict):
                raise ValueError("Expected a data object")
            clean = {
                key: value
                for key, value in data.items()
                if isinstance(key, str)
                and key.startswith("gorgon-")
                and isinstance(value, str)
            }
            if len(clean) != len(data):
                raise ValueError("Save data contains unsupported keys or values")
            with SAVE_LOCK:
                saved_at = write_save(clean)
            self.send_json(200, {"ok": True, "savedAt": saved_at})
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": f"Could not save local data: {error}"})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), GorgonLedgerHandler)
    print(f"Gorgon Ledger is running at http://127.0.0.1:{PORT}/", flush=True)
    print(f"Save file: {SAVE_PATH}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
