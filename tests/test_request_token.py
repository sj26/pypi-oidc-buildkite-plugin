import io
import json
import os
import runpy
import subprocess
import unittest

from pathlib import Path
from unittest import mock


class JSONResponse(io.BytesIO):
    status = 200

    def __init__(self, value):
        super().__init__(json.dumps(value).encode())


class RequestTokenTests(unittest.TestCase):
    def test_requests_publisher_ids_and_exchanges_at_generic_endpoint(self):
        agent_process = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="buildkite-jwt\n", stderr=""
        )
        responses = [
            JSONResponse({"audience": "pypi"}),
            JSONResponse({"token": "pypi-short-lived-token"}),
        ]

        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("urllib.request.urlopen", side_effect=responses) as urlopen,
            mock.patch("subprocess.run", return_value=agent_process) as run,
            mock.patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            runpy.run_path(Path(__file__).parents[1] / "request-token")

        run.assert_called_once_with(
            [
                "buildkite-agent",
                "oidc",
                "request-token",
                "--audience",
                "pypi",
                "--lifetime",
                "60",
                "--claim",
                "organization_id,pipeline_id,jti",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            urlopen.call_args_list[0].args[0],
            "https://upload.pypi.org/_/oidc/audience",
        )
        token_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(
            token_request.full_url,
            "https://upload.pypi.org/_/oidc/mint-token",
        )
        self.assertEqual(json.loads(token_request.data), {"token": "buildkite-jwt"})
        self.assertEqual(stdout.getvalue(), "pypi-short-lived-token")

    def test_agent_failures_stop_before_exchange_with_guidance(self):
        for agent_result, error in (
            (
                subprocess.CompletedProcess(
                    [], 1, "sensitive-partial-token", "unknown flag: --claim"
                ),
                "unknown flag: --claim",
            ),
            (subprocess.CompletedProcess([], 0, " \n", ""), "empty token"),
            (FileNotFoundError("buildkite-agent not found"), "on PATH"),
        ):
            with self.subTest(agent_result=agent_result):
                with (
                    mock.patch.dict(os.environ, {}, clear=True),
                    mock.patch(
                        "urllib.request.urlopen",
                        return_value=JSONResponse({"audience": "pypi"}),
                    ) as urlopen,
                    mock.patch("subprocess.run", side_effect=[agent_result]),
                    mock.patch("sys.stdout", new_callable=io.StringIO) as stdout,
                    mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
                    self.assertRaises(SystemExit) as raised,
                ):
                    runpy.run_path(Path(__file__).parents[1] / "request-token")

                self.assertEqual(raised.exception.code, 1)
                urlopen.assert_called_once_with(
                    "https://upload.pypi.org/_/oidc/audience"
                )
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn(error, stderr.getvalue())
                self.assertIn("v3.45.0+", stderr.getvalue())
                self.assertIn("Buildkite job", stderr.getvalue())
                self.assertNotIn("sensitive-partial-token", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
