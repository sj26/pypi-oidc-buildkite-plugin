# PyPI Buildkite OIDC support

Securely push [Python packages] from your [Buildkite] pipelines. Exchanges a [Buildkite OIDC token] as a [trusted publisher] on [PyPI], the Python Package Index. Exports `TWINE_USERNAME` and `TWINE_PASSWORD` for use by [Twine].

```yaml
steps:
- label: ":python: Build and push to PyPI"
  plugins:
  - sj26/pypi-oidc
  command: |
    python3 setup.py sdist
    python3 -m pip install --upgrade twine
    twine upload dist/*
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
