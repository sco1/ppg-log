# PPG-Log
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ppg-log)](https://pypi.org/project/ppg-log/)
[![PyPI](https://img.shields.io/pypi/v/ppg-log)](https://pypi.org/project/ppg-log/)
[![PyPI - License](https://img.shields.io/pypi/l/ppg-log?color=magenta)](https://github.com/sco1/ppg-log/blob/main/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/ppg-log/main.svg)](https://results.pre-commit.ci/latest/github/sco1/ppg-log/main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![Open in Visual Studio Code](https://img.shields.io/badge/Open%20in-VSCode.dev-blue)](https://vscode.dev/github.com/sco1/ppg-log)

Helper Tools for PPG FlySight Flight Log Management

🚨 This is an alpha project. User-facing functionality is still under development 🚨

## Installation
Install from PyPi with your favorite `pip` invocation:

```bash
$ pip install ppg-log
```

You can confirm proper installation via the `ppglog` CLI:
<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["ppglog", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"```bash\n$ ppglog --help\n{out.stdout.rstrip()}\n```"
)
]]] -->
```bash
$ ppglog --help
Usage: ppglog [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  batch   Batch flight log processing pipeline.
  single  Single flight log processing pipeline.
```
<!-- [[[end]]] -->

## Usage
🚧 🚧 🚧

## Contributing
### Development Environment
This project uses [Poetry](https://python-poetry.org/) to manage dependencies. With your fork cloned to your local machine, you can install the project and its dependencies to create a development environment using:

```bash
$ poetry install
```

A [pre-commit](https://pre-commit.com) configuration is also provided to create a pre-commit hook so linting errors aren't committed:

```bash
$ pre-commit install
```

### Testing & Coverage
A [pytest](https://docs.pytest.org/en/latest/) suite is provided, with coverage reporting from [pytest-cov](https://github.com/pytest-dev/pytest-cov). A [tox](https://github.com/tox-dev/tox/) configuration is provided to test across all supported versions of Python. Testing will be skipped for Python versions that cannot be found.

```bash
$ tox
```

Details on missing coverage, including in the test suite, is provided in the report to allow the user to generate additional tests for full coverage.
