import io
import json
import os
import runpy
import subprocess
import unittest

from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError


class JSONResponse(io.BytesIO):
    def __init__(self, value, status=200):
        self.status = status
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

    def test_custom_repository_audience_and_lifetime(self):
        with (
            mock.patch.dict(
                os.environ,
                {
                    "BUILDKITE_PLUGIN_PYPI_OIDC_REPOSITORY_URL": "https://test.pypi.org/legacy/",
                    "BUILDKITE_PLUGIN_PYPI_OIDC_LIFETIME": "120",
                },
                clear=True,
            ),
            mock.patch(
                "urllib.request.urlopen",
                side_effect=[
                    JSONResponse({"audience": "testpypi"}),
                    JSONResponse({"token": "testpypi-token"}),
                ],
            ) as urlopen,
            mock.patch(
                "subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, "testpypi-jwt\n", ""),
            ) as run,
            mock.patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            runpy.run_path(Path(__file__).parents[1] / "request-token")

        self.assertEqual(
            run.call_args.args[0],
            [
                "buildkite-agent",
                "oidc",
                "request-token",
                "--audience",
                "testpypi",
                "--lifetime",
                "120",
                "--claim",
                "organization_id,pipeline_id,jti",
            ],
        )
        self.assertEqual(
            urlopen.call_args_list[0].args[0], "https://test.pypi.org/_/oidc/audience"
        )
        self.assertEqual(
            urlopen.call_args.args[0].full_url,
            "https://test.pypi.org/_/oidc/mint-token",
        )
        self.assertEqual(
            json.loads(urlopen.call_args.args[0].data), {"token": "testpypi-jwt"}
        )
        self.assertEqual(stdout.getvalue(), "testpypi-token")

    def test_repository_errors_stop_with_diagnostics(self):
        for stage, failure, diagnostic in (
            (
                "audience",
                JSONResponse({"audience": "pypi"}, status=204),
                "expected HTTP 200, got 204",
            ),
            (
                "audience",
                HTTPError("", 403, "Forbidden", {}, None),
                "trusted publishing disabled",
            ),
            (
                "audience",
                HTTPError("", 404, "Not Found", {}, None),
                "does not indicate trusted publishing support",
            ),
            ("audience", HTTPError("", 503, "Service Unavailable", {}, None), "503"),
            ("audience", URLError("connection refused"), "network access"),
            ("exchange", URLError("connection refused"), "network access"),
            (
                "exchange",
                HTTPError("", 403, "Forbidden", {}, io.BytesIO(b"forbidden")),
                "403",
            ),
            (
                "exchange",
                HTTPError(
                    "",
                    422,
                    "Unprocessable Entity",
                    {},
                    JSONResponse(
                        {
                            "errors": [
                                {
                                    "code": "invalid-reuse-token",
                                    "description": "Token already used",
                                }
                            ]
                        }
                    ),
                ),
                "invalid-reuse-token",
            ),
        ):
            with self.subTest(stage=stage, diagnostic=diagnostic):
                responses = (
                    [failure]
                    if stage == "audience"
                    else [
                        JSONResponse({"audience": "pypi"}),
                        failure,
                    ]
                )
                with (
                    mock.patch.dict(os.environ, {}, clear=True),
                    mock.patch(
                        "urllib.request.urlopen", side_effect=responses
                    ) as urlopen,
                    mock.patch(
                        "subprocess.run",
                        return_value=subprocess.CompletedProcess([], 0, "test-jwt", ""),
                    ) as run,
                    mock.patch("sys.stdout", new_callable=io.StringIO) as stdout,
                    mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
                    self.assertRaises(SystemExit) as raised,
                ):
                    runpy.run_path(Path(__file__).parents[1] / "request-token")

                self.assertEqual(raised.exception.code, 1)
                self.assertIn(diagnostic, stderr.getvalue())
                self.assertEqual(stdout.getvalue(), "")
                self.assertNotIn("test-jwt", stderr.getvalue())
                self.assertEqual(urlopen.call_count, len(responses))
                self.assertEqual(run.call_count, 0 if stage == "audience" else 1)


if __name__ == "__main__":
    unittest.main()
