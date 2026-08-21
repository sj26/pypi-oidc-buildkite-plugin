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
    def test_requests_pipeline_id_and_exchanges_at_generic_endpoint(self):
        agent_process = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="buildkite-jwt\n", stderr=""
        )
        responses = [
            JSONResponse({"audience": "pypi"}),
            JSONResponse({"token": "pypi-short-lived-token"}),
        ]

        with (
            mock.patch.dict(
                os.environ,
                {
                    "BUILDKITE_PLUGIN_PYPI_OIDC_REPOSITORY_URL": (
                        "https://upload.pypi.org/legacy/"
                    ),
                    "BUILDKITE_PLUGIN_PYPI_OIDC_LIFETIME": "60",
                },
            ),
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
                "pipeline_id",
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


if __name__ == "__main__":
    unittest.main()
