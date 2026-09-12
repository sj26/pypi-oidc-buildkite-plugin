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

## Requirements

- Buildkite agent v3.45.0 or newer, which supports additional OIDC claims.
- Bash and Python 3.10 or newer ([supported versions]), using only the standard library.

[supported versions]: https://devguide.python.org/versions/

## Development and releases

Run the tests with `python3 -m unittest discover -s tests -v`.

Releases use immutable `vMAJOR.MINOR.PATCH` tags. Before publishing a GitHub
Release from `main`, run the tests and update the README examples to the new
version. Never move an existing version tag; publish a new version for fixes.

## Thanks

Inspired by https://github.com/pypa/gh-action-pypi-publish, and with generous guidance by [William Woodruff].

[William Woodruff]: https://yossarian.net
