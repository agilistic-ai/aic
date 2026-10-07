"""Installed app + real SDKs + local HTTP fixtures. No live inference or paid calls."""

from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from ai_cookbook.note_to_task import note_to_task
from ai_cookbook.settings import load_settings

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads((ROOT / "examples/room_request.expected.json").read_text())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append((self.path, request))
        scenario = self.server.scenario
        if scenario == "timeout":
            time.sleep(0.4)
        if scenario == "http_error":
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"PRIVATE PROVIDER DETAILS","type":"server_error"}}')
            return
        task = dict(EXPECTED)
        if scenario == "bad_date":
            task["due_date"] = "2026-02-30"
        elif scenario == "invented_date":
            task["due_date"] = "2026-11-09"
        elif scenario == "extra_field":
            task["approved"] = True
        elif scenario == "missing_date":
            task["due_date"] = None
        text = "{" if scenario == "invalid_json" else json.dumps(task)
        stream = request.get("stream", False)
        if self.path == "/v1/responses":
            content = ([{"type": "refusal", "refusal": "PRIVATE REFUSAL TEXT"}]
                       if scenario == "refusal" else
                       [{"type": "output_text", "text": text, "annotations": []}])
            response = {"id": "resp_fixture", "object": "response", "created_at": 1,
                        "model": request["model"], "status": "incomplete" if scenario == "incomplete" else "completed",
                        "output": [{"type": "message", "id": "msg_fixture", "role": "assistant", "status": "completed", "content": content}],
                        "usage": {"input_tokens": 100, "output_tokens": 40, "total_tokens": 140}}
            if stream:
                events = [{"type": "response.output_text.delta", "delta": text[:8],
                           "item_id": "msg_fixture", "output_index": 0, "content_index": 0, "sequence_number": 1}]
                if scenario != "truncated_stream":
                    events.append({"type": "response.incomplete" if scenario == "incomplete" else "response.completed",
                                   "response": response, "sequence_number": 2})
                data = "".join("event: " + e["type"] + "\ndata: " + json.dumps(e) + "\n\n" for e in events).encode()
                content_type = "text/event-stream"
            else:
                data, content_type = json.dumps(response).encode(), "application/json"
        elif self.path == "/api/chat":
            response = {"model": request["model"], "created_at": "2026-10-03T00:00:00Z",
                        "message": {"role": "assistant", "content": text}, "done": True,
                        "done_reason": "length" if scenario == "incomplete" else "stop",
                        "prompt_eval_count": 100, "eval_count": 40}
            if stream:
                first = {**response, "message": {"role": "assistant", "content": text[:8]}, "done": False}
                last = {**response, "message": {"role": "assistant", "content": text[8:]}}
                data = (json.dumps(first) + "\n" + ("" if scenario == "truncated_stream" else json.dumps(last) + "\n")).encode()
                content_type = "application/x-ndjson"
            else:
                data, content_type = json.dumps(response).encode(), "application/json"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


class SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.server.scenario, self.server.requests = "normal", []
        base = f"http://127.0.0.1:{self.server.server_port}"
        self.environment = {**os.environ, "AIC_API_KEY": "smoke-only-key",
                            "AIC_OPENAI_BASE_URL": base + "/v1", "AIC_OLLAMA_HOST": base,
                            "NO_PROXY": "127.0.0.1,localhost,::1", "no_proxy": "127.0.0.1,localhost,::1"}

    def config(self, provider, timeout=2):
        path = self.folder / (provider + ".toml")
        path.write_text(f'[model]\nprovider="{provider}"\nname="fixture-model"\ntimeout_seconds={timeout}\n')
        return path

    def cli(self, provider="openai", *, scenario="normal", extra=(), note=None, timeout=2, environment=None, console=False):
        self.server.scenario = scenario
        source = ROOT / "examples/room_request.txt"
        if note is not None:
            source = self.folder / "input.txt"
            source.write_bytes(note if isinstance(note, bytes) else note.encode())
        entry = ([str(Path(sys.executable).with_name("note-to-task.exe" if os.name == "nt" else "note-to-task"))]
                 if console else [sys.executable, "-m", "ai_cookbook.note_to_task"])
        return subprocess.run([*entry,
                               "--input", str(source), "--config", str(self.config(provider, timeout)), *extra],
                              cwd=self.folder, env=environment or self.environment,
                              capture_output=True, text=True, timeout=15)

    def test_01_cli_both_sdks_and_stream_modes(self):
        for provider in ("openai", "ollama"):
            for stream in (False, True):
                with self.subTest(provider=provider, stream=stream):
                    result = self.cli(provider, extra=("--usage", "--stream") if stream else ("--usage",),
                                      console=provider == "openai" and not stream)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout), EXPECTED)
                    usage = json.loads(result.stderr)
                    self.assertEqual(usage["input_tokens"], 100)
                    self.assertNotIn("text", usage)
                    path, request = self.server.requests[-1]
                    if provider == "openai":
                        self.assertEqual(path, "/v1/responses")
                        self.assertFalse(request["store"])
                        self.assertEqual(request["truncation"], "disabled")
                        self.assertTrue(request["text"]["format"]["strict"])
                    else:
                        self.assertEqual(path, "/api/chat")
                        self.assertEqual(request["options"]["num_ctx"], 4096)

    def test_02_reusable_function(self):
        with patch.dict(os.environ, self.environment):
            task = note_to_task((ROOT / "examples/room_request.txt").read_text(), settings=load_settings(self.config("openai")))
        self.assertEqual(task.model_dump(), EXPECTED)

    def test_03_validation_rejects_provider_output(self):
        for scenario in ("bad_date", "invented_date", "extra_field", "invalid_json"):
            with self.subTest(scenario=scenario):
                result = self.cli(scenario=scenario)
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)

    def test_04_failure_and_partial_stream_never_print_task(self):
        for provider in ("openai", "ollama"):
            for scenario in ("incomplete", "truncated_stream"):
                with self.subTest(provider=provider, scenario=scenario):
                    result = self.cli(provider, scenario=scenario, extra=("--stream",))
                    self.assertEqual(result.returncode, 3, result.stderr)
                    self.assertEqual(result.stdout, "")
        result = self.cli(scenario="refusal")
        self.assertEqual(result.returncode, 3)
        self.assertNotIn("PRIVATE", result.stderr)

    def test_05_bad_input_before_model_call(self):
        for note in ("", " " * 5, "a" * 2001, "é" * 1001, b"\xff"):
            with self.subTest(note_bytes=len(note)):
                result = self.cli(note=note)
                self.assertEqual(result.returncode, 4)
                self.assertEqual(result.stdout, "")
        self.assertEqual(self.server.requests, [])

    def test_06_configuration_and_help_need_no_model(self):
        env = {**self.environment, "AIC_API_KEY": ""}
        result = self.cli(environment=env)
        self.assertEqual(result.returncode, 2)
        result = subprocess.run([sys.executable, "-m", "ai_cookbook.note_to_task", "--help"],
                                cwd=self.folder, env=env, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.server.requests, [])

    def test_07_network_failures_are_bounded_and_not_retried(self):
        for provider in ("openai", "ollama"):
            for scenario in ("timeout", "http_error"):
                with self.subTest(provider=provider, scenario=scenario):
                    before = len(self.server.requests)
                    result = self.cli(provider, scenario=scenario, timeout=0.1)
                    self.assertEqual(result.returncode, 3, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertNotIn("PRIVATE", result.stderr)
                    self.assertEqual(len(self.server.requests) - before, 1)

    def test_08_missing_deadline_stays_null(self):
        result = self.cli(scenario="missing_date", note=(ROOT / "examples/no_date.txt").read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(json.loads(result.stdout)["due_date"])

    def test_09_evaluation_runner_preserves_review_requirement(self):
        cases = self.folder / "cases.jsonl"
        cases.write_text(json.dumps({"id": "room", "note": (ROOT / "examples/room_request.txt").read_text(),
                                    "due_date": "2026-11-06", "review": "Check the prohibition."}) + "\n")
        output = self.folder / "evaluation.jsonl"
        command = [sys.executable, "-m", "ai_cookbook.evaluation", "--cases", str(cases),
                   "--output", str(output), "--config", str(self.config("openai"))]
        result = subprocess.run(command, cwd=self.folder, env=self.environment, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in output.read_text().splitlines()]
        self.assertTrue(records[1]["mechanical_pass"])
        self.assertEqual(records[1]["semantic_review"], "pending")
        before = len(self.server.requests)
        result = subprocess.run(command, cwd=self.folder, env=self.environment, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(self.server.requests), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
