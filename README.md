# PyPI Buildkite OIDC support

> [!NOTE]
> Buildkite trusted publishing is not yet generally available on PyPI, but
> [work is in progress](https://github.com/pypi/warehouse/pull/14814).

Securely push [Python packages] from your [Buildkite] pipelines. Exchanges a [Buildkite OIDC token] as a [trusted publisher] on [PyPI], the Python Package Index. Exports `TWINE_USERNAME` and `TWINE_PASSWORD` for use by [Twine].

```yaml
steps:
  - label: ":python: Build and publish to PyPI"
    plugins:
      - sj26/pypi-oidc#buildkite-trusted-publishing: ~
    command: |
      python -m pip install --upgrade build twine
      python -m build
      python -m twine upload dist/*
```

The plugin requests Buildkite's immutable `pipeline_id` as an additional OIDC
claim. This allows a PyPI trusted publisher to pin authorization to one pipeline
without replacing Buildkite's default OIDC subject. Publishers that do not use
pipeline ID pinning remain compatible.

For TestPyPI, point both the plugin and Twine at TestPyPI:

```yaml
steps:
  - label: ":test-tube: Build and publish to TestPyPI"
    plugins:
      - sj26/pypi-oidc#buildkite-trusted-publishing:
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

Python 3 [supported versions], and the standard library. No packages are used outside the standard library.

[supported versions]: https://devguide.python.org/versions/

## Thanks

Inspired by https://github.com/pypa/gh-action-pypi-publish, and with generous guidance by [William Woodruff].

[William Woodruff]: https://yossarian.net
