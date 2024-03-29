# PPG-Log
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ppg-log/0.1.0?logo=python&logoColor=FFD43B)](https://pypi.org/project/ppg-log/)
[![PyPI](https://img.shields.io/pypi/v/ppg-log?logo=Python&logoColor=FFD43B)](https://pypi.org/project/ppg-log/)
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
  db      Interact with a PPG Log database instance.
  single  Single flight log processing pipeline.
```
<!-- [[[end]]] -->

## Usage
### Environment Variables
The following environment variables are provided to help customize pipeline behaviors.

| Variable Name      | Description                       | Default      |
|--------------------|-----------------------------------|--------------|
| `DB_URL`           | Flight log database URL           | `'./tmp.db'` |
| `PROMPT_START_DIR` | Start path for UI file/dir prompt | `'.'`        |

### `ppglog single`
Process a single FlySight log file.
#### Input Parameters
| Parameter              | Description                                                                  | Type         | Default    |
|------------------------|------------------------------------------------------------------------------|--------------|------------|
| `--log-filepath`       | Path to FlySight log to parse.                                               | `Path\|None` | GUI Prompt |
| `--start-trim`         | Seconds to discard from the beginning of the flight log.                     | `int\|float` | `45`       |
| `--airborne-threshold` | Minimum groundspeed, as m/s, required to be considered airborne.             | `int\|float` | `2.235`    |
| `--time-threshold`     | Duration, as seconds, used to characterize flight segments.                  | `int\|float` | `15`       |
| `--midair-start`       | Consider the start of the file as the start of a flight segment.<sup>1</sup> | `bool`       | `False`    |
| `--show-plot`          | Show parsed flight log summary plot.                                         | `bool`       | `True`     |
| `--plot_save_dir`      | Path to save parsed flight log summary plot.<sup>2</sup>                     | `Path\|None` | `None`     |
| `--db-insert`          | Insert flight logs into the currently configured database.                   | `bool`       | `False`    |

1. If `True`, any specificed `--start-trim` will be discarded
2. If `None`, the summary plot will not be saved

### `ppglog batch`
Batch process a directory of FlySight log files.
#### Input Parameters
| Parameter              | Description                                                      | Type         | Default    |
|------------------------|------------------------------------------------------------------|--------------|------------|
| `--log-dir`            | Path to FlySight log directory to parse.                         | `Path\|None` | GUI Prompt |
| `--log-pattern`        | FlySight log file glob pattern.<sup>1,2</sup>                    | `str`        | `"*.CSV"`  |
| `--start-trim`         | Seconds to discard from the beginning of the flight log.         | `int\|float` | `45`       |
| `--airborne-threshold` | Minimum groundspeed, as m/s, required to be considered airborne. | `int\|float` | `2.235`    |
| `--time-threshold`     | Duration, as seconds, used to characterize flight segments.      | `int\|float` | `15`       |
| `--plot-save-dir`      | Path to save parsed flight log summary plot.<sup>3</sup>         | `Path\|None` | `None`     |
| `--db-insert`          | Insert flight logs into the currently configured database.       | `bool`       | `False`    |
| `--verbose`            | Display in-console information on the running parsing operation. | `bool`       | `True`     |

1. Case sensitivity is deferred to the host OS
2. Recursive globbing requires manual specification (e.g. `**/*.CSV`)
3. If `None`, the summary plot will not be saved

### `ppglog db`
Subcommands for interacting with the PPG Log database.
### `ppglog db set-address`
Save the db address to a local `.env` file.

**NOTE:** If a `.env` file does not exist in the current directory, one will be created for you.
#### Input Parameters
| Parameter | Description        | Type  | Default  |
|-----------|--------------------|-------|----------|
| `--value` | db address string. | `str` | Required |

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
