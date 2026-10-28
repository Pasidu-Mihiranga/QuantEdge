"""Scripted MiroFish run (Step 19 §3.2): seed -> ontology -> graph -> simulation -> report -> questionnaire.

The MiroFish service runs separately (mirofish-service/, Docker, unmodified, AGPL-3.0). Endpoints
were read from its backend route definitions (commit pinned in config.yaml -> behavioral.mirofish_commit):

    POST /api/graph/ontology/generate   multipart: files, simulation_requirement, project_name -> project_id
    POST /api/graph/build               {project_id}                          -> task_id
    GET  /api/graph/task/<task_id>      status: pending | processing | completed | failed
    POST /api/simulation/create         {project_id}                          -> simulation_id
    POST /api/simulation/prepare        {simulation_id}                       -> task_id
    POST /api/simulation/prepare/status {task_id, simulation_id}
    POST /api/simulation/start          {simulation_id, max_rounds, enable_graph_memory_update}
    GET  /api/simulation/<id>/run-status  runner_status: ... | completed | stopped | failed
    POST /api/simulation/close-env      {simulation_id, timeout}  (after both platforms finish)
    POST /api/report/generate           {simulation_id}                       -> task_id / report_id
    POST /api/report/generate/status    {task_id, simulation_id}
    GET  /api/report/by-simulation/<id> markdown_content
    POST /api/report/chat               {simulation_id, message}              -> response

Every artifact is written into the run directory and hashed; the app never calls the service.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

from quantedge.behavioral.schema import QUESTIONNAIRE, SchemaError, parse_json_answer
from quantedge.behavioral.seed import write_manifest

# MiroFish picks the prompt and report language from this header (exact match, default 'zh');
# English output is needed for the human coders and the report.
HEADERS = {"Accept-Language": "en"}
DONE = {"completed", "ready"}
FAILED = {"failed", "stopped", "error"}


class MiroFishError(RuntimeError):
    pass


class MiroFishClient:
    def __init__(self, base_url: str = "http://localhost:5001", timeout_s: int = 45 * 60, poll_s: float = 10.0):
        self.base, self.deadline_s, self.poll_s = base_url.rstrip("/"), timeout_s, poll_s
        self.t0 = time.monotonic()
        self._closed: dict[str, bool] = {}

    # --- helpers -------------------------------------------------------------------------------
    def _check_time(self, stage: str) -> None:
        if time.monotonic() - self.t0 > self.deadline_s:
            raise MiroFishError(f"run exceeded {self.deadline_s / 60:.0f} minutes at stage '{stage}' (feasibility gate)")

    def _json(self, r: requests.Response, stage: str) -> dict:
        try:
            body = r.json()
        except ValueError as e:
            raise MiroFishError(f"{stage}: non-JSON response ({r.status_code})") from e
        if not r.ok or body.get("success") is False:
            raise MiroFishError(f"{stage}: {body.get('error') or r.status_code}")
        return body.get("data", body)

    def post(self, path: str, stage: str, **kw) -> dict:
        self._check_time(stage)
        return self._json(requests.post(self.base + path, timeout=600, headers=HEADERS, **kw), stage)

    def get(self, path: str, stage: str) -> dict:
        self._check_time(stage)
        return self._json(requests.get(self.base + path, timeout=120, headers=HEADERS), stage)

    def wait(self, stage: str, poll) -> dict:
        while True:
            data = poll()
            status = str(data.get("status") or data.get("runner_status") or "").lower()
            if status in DONE or data.get("already_prepared") or data.get("is_completed"):
                return data
            if status in FAILED:
                raise MiroFishError(f"{stage} failed: {data.get('error') or data.get('message') or status}")
            self._check_time(stage)
            time.sleep(self.poll_s)

    def run_status(self, sim_id: str) -> dict:
        """Run status; once both platforms finish, close the environment.

        The simulation process stays alive in "wait for commands" mode after its last round, and
        MiroFish publishes `completed` (required before a report) only after the process exits and
        the Zep graph writes have drained, so the client sends close-env once.
        """
        data = self.get(f"/api/simulation/{sim_id}/run-status", "simulation run")
        if data.get("twitter_completed") and data.get("reddit_completed") and not self._closed.get(sim_id):
            self.post("/api/simulation/close-env", "simulation close", json={"simulation_id": sim_id, "timeout": 60})
            self._closed[sim_id] = True
        return data

    # --- pipeline ------------------------------------------------------------------------------
    def run(self, run_dir: Path, seed_text: str, prompt: str, name: str, max_rounds: int = 40) -> dict:
        timings = {}

        def mark(stage):
            timings[stage] = round(time.monotonic() - self.t0, 1)

        files = {"files": ("seed.md", seed_text.encode("utf-8"), "text/markdown")}
        proj = self.post("/api/graph/ontology/generate", "ontology", files=files,
                         data={"simulation_requirement": prompt, "project_name": name})
        project_id = proj["project_id"]
        mark("ontology")
        task = self.post("/api/graph/build", "graph build", json={"project_id": project_id})
        self.wait("graph build", lambda: self.get(f"/api/graph/task/{task['task_id']}", "graph build"))
        mark("graph")
        sim = self.post("/api/simulation/create", "simulation create", json={"project_id": project_id})
        sim_id = sim["simulation_id"]
        prep = self.post("/api/simulation/prepare", "simulation prepare", json={"simulation_id": sim_id})
        self.wait("simulation prepare", lambda: self.post(
            "/api/simulation/prepare/status", "simulation prepare",
            json={"task_id": prep.get("task_id"), "simulation_id": sim_id}))
        mark("prepare")
        # As MiroFish's own frontend does: agent activity is written to the Zep graph the report agent reads.
        self.post("/api/simulation/start", "simulation start",
                  json={"simulation_id": sim_id, "max_rounds": max_rounds, "enable_graph_memory_update": True})
        self.wait("simulation run", lambda: self.run_status(sim_id))
        mark("simulate")
        rep = self.post("/api/report/generate", "report", json={"simulation_id": sim_id})
        self.wait("report", lambda: self.post("/api/report/generate/status", "report",
                                              json={"task_id": rep.get("task_id"), "simulation_id": sim_id}))
        report = self.get(f"/api/report/by-simulation/{sim_id}", "report")
        (run_dir / "raw_report.md").write_text(report.get("markdown_content", ""), encoding="utf-8")
        (run_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        mark("report")

        attempts = []
        answer_text = ""
        for _ in range(5):                              # gate: >= 4 of 5 schema-valid answers
            reply = self.post("/api/report/chat", "questionnaire", json={"simulation_id": sim_id, "message": QUESTIONNAIRE})
            answer_text = reply.get("response", "")
            try:
                parse_json_answer(answer_text)
                attempts.append(True)
                break
            except (SchemaError, ValueError):
                attempts.append(False)
        (run_dir / "report_agent_answers.json").write_text(answer_text, encoding="utf-8")
        mark("questionnaire")
        info = {"project_id": project_id, "simulation_id": sim_id, "max_rounds": max_rounds,
                "timings_s": timings, "questionnaire_attempts": attempts,
                "finished_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
        cfg_path = run_dir / "run_config.json"
        base = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        cfg_path.write_text(json.dumps({**base, **info}, indent=2), encoding="utf-8")
        write_manifest(run_dir)
        return info
