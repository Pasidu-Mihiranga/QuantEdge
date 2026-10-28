"""Local OpenAI-compatible proxy to Gemini on Vertex AI (Step 19 infrastructure).

MiroFish speaks the OpenAI SDK with a fixed API key; Vertex needs OAuth tokens that expire hourly.
This proxy holds the service-account file, mints and refreshes tokens, and forwards
/v1/chat/completions requests unchanged to Vertex's OpenAI-compatible endpoint.

    python -m quantedge.behavioral.vertex_proxy --key <service-account.json> --local-key <random>

Safeguards:
- binds to 127.0.0.1 only (Docker Desktop containers reach it as host.docker.internal);
- every request must carry `Authorization: Bearer <local-key>` (the value given to MiroFish as
  LLM_API_KEY), so no other process can spend the budget;
- a hard token budget per session (`--budget`): requests are refused with HTTP 429 once exceeded;
- a usage log (one JSON line per request: time, model, tokens) for cost tracking and the
  reproducibility record. The service-account file never leaves this machine.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class TokenSource:
    """Cached Google access token, refreshed five minutes before expiry (thread-safe)."""

    def __init__(self, key_file: str):
        from google.oauth2 import service_account

        self.creds = service_account.Credentials.from_service_account_file(key_file, scopes=SCOPES)
        self.project = json.loads(Path(key_file).read_text(encoding="utf-8"))["project_id"]
        self._lock = threading.Lock()

    def token(self) -> str:
        from google.auth.transport.requests import Request

        with self._lock:
            expiry = self.creds.expiry
            if not self.creds.token or expiry is None or (expiry - datetime.now(UTC).replace(tzinfo=None)).total_seconds() < 300:
                self.creds.refresh(Request())
            return self.creds.token


class Budget:
    def __init__(self, max_tokens: int, log_file: Path):
        self.max_tokens, self.used, self.log_file = max_tokens, 0, log_file
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            return self.used < self.max_tokens

    def record(self, model: str, usage: dict) -> None:
        total = int(usage.get("total_tokens", 0) or 0)
        with self._lock:
            self.used += total
            line = {"utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "model": model,
                    "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": total, "session_total": self.used}
            with self.log_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(line) + "\n")


def vertex_url(project: str, region: str) -> str:
    host = "aiplatform.googleapis.com" if region == "global" else f"{region}-aiplatform.googleapis.com"
    return f"https://{host}/v1/projects/{project}/locations/{region}/endpoints/openapi/chat/completions"


def normalise_model(name: str | None, default: str) -> str:
    """Vertex expects 'google/<model>'; accept bare Gemini names from MiroFish's configuration."""
    name = name or default
    return name if "/" in name else f"google/{name}"


def make_handler(tokens: TokenSource, budget: Budget, local_key: str, region: str, default_model: str):
    url = vertex_url(tokens.project, region)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorised(self) -> bool:
            if self.headers.get("Authorization", "") != f"Bearer {local_key}":
                self._send(401, b'{"error": {"message": "invalid local key"}}')
                return False
            return True

        def do_GET(self):  # noqa: N802
            if not self._authorised():
                return
            if self.path.rstrip("/").endswith("/models"):
                body = {"object": "list", "data": [{"id": default_model, "object": "model", "owned_by": "google"}]}
                return self._send(200, json.dumps(body).encode())
            self._send(404, b'{"error": {"message": "not found"}}')

        def do_POST(self):  # noqa: N802
            if not self._authorised():
                return
            if not self.path.rstrip("/").endswith("/chat/completions"):
                return self._send(404, b'{"error": {"message": "only chat/completions is proxied"}}')
            if not budget.allow():
                return self._send(429, json.dumps({"error": {"message": f"token budget of {budget.max_tokens} reached"}}).encode())
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            payload["model"] = normalise_model(payload.get("model"), default_model)
            for attempt in range(4):
                r = requests.post(url, json=payload, timeout=300,
                                  headers={"Authorization": f"Bearer {tokens.token()}"})
                if r.status_code not in (429, 500, 502, 503, 504):
                    break
                time.sleep(2 ** attempt)
            if r.ok:
                try:
                    budget.record(payload["model"], r.json().get("usage", {}))
                except ValueError:
                    pass
            self._send(r.status_code, r.content, r.headers.get("Content-Type", "application/json"))

        def log_message(self, fmt, *args):  # quieter console: one line per request
            print(f"[proxy] {self.address_string()} {fmt % args}")

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser(description="OpenAI-compatible local proxy to Gemini on Vertex AI")
    ap.add_argument("--key", required=True, help="path to the service-account JSON (kept outside the repo)")
    ap.add_argument("--local-key", required=True, help="shared secret MiroFish sends as LLM_API_KEY")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--region", default="global")
    ap.add_argument("--model", default="google/gemini-2.5-flash")
    ap.add_argument("--budget", type=int, default=5_000_000, help="max total tokens this session")
    ap.add_argument("--log", default="data/behavioral/llm_usage.jsonl")
    args = ap.parse_args()
    log = Path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    tokens = TokenSource(args.key)
    server = ThreadingHTTPServer(("127.0.0.1", args.port),
                                 make_handler(tokens, Budget(args.budget, log), args.local_key, args.region, args.model))
    print(f"Vertex proxy on http://127.0.0.1:{args.port}/v1 -> {args.model} ({args.region}), budget {args.budget:,} tokens")
    server.serve_forever()


if __name__ == "__main__":
    main()
