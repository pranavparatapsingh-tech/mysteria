import json
import os
import sqlite3
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.path.join(os.path.dirname(__file__), "mysteria.db")
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS progress (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()


class MysteriaHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def _json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            has_ai = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY"))
            return self._json({"status": "ok", "ai_configured": has_ai})
        if self.path == "/api/progress":
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute("SELECT payload FROM progress WHERE id='default'").fetchone()
            conn.close()
            return self._json(json.loads(row[0]) if row else {})
        return super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._json({"error": "Invalid JSON"}, 400)

        if self.path == "/api/progress":
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT OR REPLACE INTO progress (id, payload) VALUES ('default', ?)",
                (json.dumps(data),),
            )
            conn.commit()
            conn.close()
            return self._json({"status": "saved"})
        return self._json({"error": "Not found"}, 404)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 8000))
    print(f"MYSTERIA Bureau Server running at http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), MysteriaHandler).serve_forever()
