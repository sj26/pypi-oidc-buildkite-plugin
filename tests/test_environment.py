import os
import shutil
import subprocess
import tempfile
import unittest

from pathlib import Path


class EnvironmentHookTests(unittest.TestCase):
    def test_exports_credentials_only_after_success(self):
        result = self.run_hook("printf 'pypi-test-token'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "__token__:pypi-test-token")
        self.assertEqual(result.stderr, "")

    def test_failed_or_empty_exchange_stops_the_job(self):
        for command in (
            "echo 'agent request failed' >&2; exit 42",
            "printf 'partial-token'; exit 42",
            "exit 0",
        ):
            with self.subTest(command=command):
                result = self.run_hook(command)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("PyPI authentication failed", result.stderr)
                self.assertIn("trusted publisher", result.stderr)
                self.assertNotIn("partial-token", result.stderr)

    def run_hook(self, token_command):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "hooks").mkdir()
            shutil.copyfile(
                Path(__file__).parents[1] / "hooks/environment",
                root / "hooks/environment",
            )
            request_token = root / "request-token"
            request_token.write_text("#!/usr/bin/env bash\n" + token_command + "\n")
            request_token.chmod(0o755)
            # Buildkite sources environment hooks. Do not rely on errexit to
            # prevent the command after the hook from using stale credentials.
            return subprocess.run(
                [
                    "bash",
                    "-c",
                    "set +e; source hooks/environment; "
                    'bash -c \'printf "%s:%s" "$TWINE_USERNAME" "$TWINE_PASSWORD"\'',
                ],
                cwd=root,
                env={**os.environ, "TWINE_USERNAME": "old", "TWINE_PASSWORD": "stale"},
                capture_output=True,
                text=True,
            )
