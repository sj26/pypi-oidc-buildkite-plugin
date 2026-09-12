# PyPI Buildkite OIDC support

> [!NOTE]
> Buildkite trusted publishing is not yet generally available on PyPI, but
> [work is in progress](https://github.com/pypi/warehouse/pull/14814).

Securely push [Python packages] from your [Buildkite] pipelines. Exchanges a [Buildkite OIDC token] as a [trusted publisher] on [PyPI], the Python Package Index. Exports `TWINE_USERNAME` and `TWINE_PASSWORD` for use by [Twine].

```yaml
steps:
  - label: ":python: Build and publish to PyPI"
    plugins:
      - sj26/pypi-oidc#v0.1.0: ~
    command: |
      python -m pip install --upgrade build twine
      python -m build
      python -m twine upload dist/*
```

The plugin requests Buildkite's immutable `organization_id` and `pipeline_id`
as additional OIDC claims. This allows a PyPI trusted publisher to independently
trust-on-first-use pin authorization to one organization and pipeline without
replacing Buildkite's default OIDC subject.

The plugin also requests `jti` (JWT ID), enabling Warehouse's existing
replay protection to reject a second exchange of the same OIDC token. This does
not make the returned PyPI upload token single-use.

For TestPyPI, point both the plugin and Twine at TestPyPI:

```yaml
steps:
  - label: ":test-tube: Build and publish to TestPyPI"
    plugins:
      - sj26/pypi-oidc#v0.1.0:
          repository_url: https://test.pypi.org/legacy/
    command: |
      python -m pip install --upgrade build twine
      python -m build
      python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

[Python packages]: https://packaging.python.org
[Buildkite]: https://buildkite.com
[Buildkite OIDC token]: https://buildkite.com/docs/agent/v3/cli-oidc
[trusted publisher]: https://docs.pypi.org/trusted-publishers/using-a-publisher/
[PyPI]: https://pypi.org
[Twine]: https://twine.readthedocs.io

## Configuration

### `repository_url` (optional, string)

The repository's upload URL. Defaults to `https://upload.pypi.org/legacy/`.
Use a trusted HTTPS endpoint: the plugin sends its Buildkite OIDC token to this
repository. Set Twine's repository URL separately, as in the TestPyPI example.

### `lifetime` (optional, integer or string)

The requested Buildkite OIDC token lifetime in seconds. Defaults to `60`.
This does not set the lifetime of the PyPI token returned by the repository.

## Troubleshooting

The environment hook stops the job if authentication fails or produces no token,
before the publish command runs. Read the preceding error in the Buildkite log:

- **Agent cannot run, rejects `--claim`, or cannot issue a token:** ensure
  `buildkite-agent` v3.45.0+ is on `PATH`. Run the plugin inside an active Buildkite
  job, not a local shell, and check the agent's connectivity to Buildkite. See
  the [OIDC command documentation][Buildkite OIDC token].
- **Audience discovery or token exchange fails:** check `repository_url` and
  network access to the repository. It must support and enable Buildkite trusted
  publishing; this is not yet generally available on PyPI or TestPyPI.
- **The repository rejects the publisher:** check the project's trusted publisher
  registration against the job's organization, pipeline, and any configured step
  or ref restrictions. A publisher pinned to an old organization or pipeline ID
  requires an authorized maintainer to review and update its registration.

Do not print OIDC tokens or `TWINE_PASSWORD` while debugging. Do not continue a
failed publishing job with empty or stale credentials.

## Requirements

- Buildkite agent v3.45.0 or newer, which supports additional OIDC claims.
- Bash and Python 3.10 or newer ([supported versions]), using only the standard library.

[supported versions]: https://devguide.python.org/versions/

## Development and releases

Run the tests and lint checks:

```sh
python3 -B -m unittest discover -s tests -v
shellcheck hooks/*
docker run --rm -v "$PWD:/plugin:ro" buildkite/plugin-linter --id sj26/pypi-oidc
```

The tests use Python's standard library and Bash, with no live credentials or
package uploads. They exercise token exchange and the sourced environment hook,
including failure with Bash `errexit` disabled. `.buildkite/pipeline.yml` runs
the tests on Python 3.10, Plugin Linter, and ShellCheck.

Releases use immutable `vMAJOR.MINOR.PATCH` tags. Before publishing a GitHub
Release from `main`, run the tests and update the README examples to the new
version. Never move an existing version tag; publish a new version for fixes.

### Adoption and CI setup

The repository is being prepared for `buildkite-plugins` ownership. The staged
Plugin Engineering `CODEOWNERS` entry requires the repository transfer and team
permissions before it becomes effective. After transfer, update the author in
`plugin.yml`, the linter ID, and README examples to the official namespace.

Configure a **trusted pipeline bootstrap** to require approval of fork builds
before checking out or executing untrusted repository code and uploading
`.buildkite/pipeline.yml`. A block step added only to a contributor-editable
pipeline file is not a security boundary. Provision the pipeline in the
OpenSource cluster with Support access; do not expose publishing credentials
to its test jobs.

Before claiming stack compatibility, smoke-test in real Buildkite jobs on each
target stack and record the results in the
[plugin compatibility repository](https://github.com/buildkite-plugins/compatibility).
The local test suite does not establish end-to-end PyPI or stack compatibility.

## Thanks

Inspired by https://github.com/pypa/gh-action-pypi-publish, and with generous guidance by [William Woodruff].

[William Woodruff]: https://yossarian.net
