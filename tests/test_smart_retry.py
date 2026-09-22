import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "smart_retry", Path(__file__).resolve().parents[1] / "src" / "smart_retry.py"
)
smart_retry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smart_retry)


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self, *_):
        return json.dumps({
            "answers": {
                "retryable": {"type": "noul", "noul": 0.96},
                "category": {"type": "choice", "choice": "network", "confidence": 0.89},
            }
        }).encode()


class SmartRetryTests(unittest.TestCase):
    def test_api_payload_and_response(self):
        def fake_open(req, timeout):
            self.assertEqual(timeout, 8)
            self.assertEqual(req.full_url, smart_retry.API_URL)
            self.assertEqual(req.headers["Authorization"], "Bearer test-key")
            body = json.loads(req.data)
            self.assertEqual(body["model"], "jev-latest")
            self.assertIn("connection reset", body["state"]["failure_log_tail"])
            self.assertEqual(body["questions"]["retryable"]["type"], "noul")
            return FakeResponse()

        with patch.object(smart_retry.urllib.request, "urlopen", side_effect=fake_open):
            self.assertEqual(smart_retry.judge("connection reset", 1, "test-key"), (0.96, "network", 0.89))

    def test_retry_then_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "attempts"
            output = Path(directory) / "output"
            command = f'test -e "{marker}" || {{ touch "{marker}"; echo "connection reset"; exit 7; }}'
            env = {
                "SMART_RETRY_COMMAND": command,
                "SMART_RETRY_API_KEY": "test-key",
                "SMART_RETRY_DELAY": "0",
                "GITHUB_OUTPUT": str(output),
            }
            with patch.dict(os.environ, env), patch.object(
                smart_retry, "judge", return_value=(0.96, "network", 0.89)
            ) as judge, patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(smart_retry.main(), 0)
            self.assertEqual(judge.call_count, 1)
            self.assertIn("attempts=2\nrecovered=true\ncategory=network", output.read_text())

    def test_deterministic_failure_preserves_exit_code(self):
        env = {
            "SMART_RETRY_COMMAND": "echo 'AssertionError'; exit 23",
            "SMART_RETRY_API_KEY": "test-key",
            "SMART_RETRY_DELAY": "0",
        }
        with patch.dict(os.environ, env), patch.object(
            smart_retry, "judge", return_value=(0.99, "code_regression", 0.99)
        ), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(smart_retry.main(), 23)

    def test_invalid_jev_response_fails_closed(self):
        env = {"SMART_RETRY_COMMAND": "exit 4", "SMART_RETRY_API_KEY": "test-key"}
        with patch.dict(os.environ, env), patch.object(
            smart_retry, "judge", side_effect=ValueError("bad response")
        ), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(smart_retry.main(), 4)

    def test_missing_key_does_not_retry(self):
        env = {"SMART_RETRY_COMMAND": "exit 6", "SMART_RETRY_API_KEY": ""}
        with patch.dict(os.environ, env), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(smart_retry.main(), 6)

    def test_redacts_api_key_from_model_input(self):
        with patch.dict(os.environ, {"SMART_RETRY_API_KEY": "secret-key-123"}):
            self.assertEqual(smart_retry.redact("failed secret-key-123"), "failed [REDACTED]")


if __name__ == "__main__":
    unittest.main()
