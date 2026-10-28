"""Vertex proxy safeguards (no network: the upstream call and the token source are faked)."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from quantedge.behavioral import vertex_proxy as vp


class _FakeTokens:
    project = "proj"

    def token(self):
        return "tok"


class _FakeResponse:
    ok, status_code = True, 200
    headers = {"Content-Type": "application/json"}
    content = json.dumps({"choices": [{"message": {"content": "OK"}}],
                          "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6}}).encode()

    def json(self):
        return json.loads(self.content)


@pytest.fixture
def server(tmp_path, monkeypatch):
    seen = {}

    def fake_post(url, json=None, timeout=None, headers=None):
        seen.update(url=url, payload=json, headers=headers)
        return _FakeResponse()

    monkeypatch.setattr(vp.requests, "post", fake_post)
    budget = vp.Budget(10, tmp_path / "usage.jsonl")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), vp.make_handler(_FakeTokens(), budget, "local", "global",
                                                                  "google/gemini-2.5-flash"))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, seen, budget, tmp_path / "usage.jsonl"
    srv.shutdown()


def _post(srv, key, body):
    req = urllib.request.Request(f"http://127.0.0.1:{srv.server_port}/v1/chat/completions",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=10)


def test_requests_need_the_local_key(server):
    srv, *_ = server
    with pytest.raises(urllib.error.HTTPError) as e:
        _post(srv, "wrong", {"messages": []})
    assert e.value.code == 401


def test_forwards_with_google_token_normalised_model_and_logs_usage(server):
    srv, seen, budget, log = server
    r = _post(srv, "local", {"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status == 200
    assert seen["headers"]["Authorization"] == "Bearer tok"
    assert seen["payload"]["model"] == "google/gemini-2.5-flash"
    assert seen["payload"]["extra_body"]["google"]["thinking_config"]["thinking_budget"] == 0
    assert seen["url"].endswith("/projects/proj/locations/global/endpoints/openapi/chat/completions")
    assert budget.used == 6 and json.loads(log.read_text().splitlines()[0])["total_tokens"] == 6


def test_budget_is_enforced(server):
    srv, _, budget, _ = server
    _post(srv, "local", {"messages": []})
    _post(srv, "local", {"messages": []})          # 12 tokens used > budget 10
    with pytest.raises(urllib.error.HTTPError) as e:
        _post(srv, "local", {"messages": []})
    assert e.value.code == 429
