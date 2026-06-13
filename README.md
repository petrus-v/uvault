# uvault

[![PyPI version](https://badge.fury.io/py/uvault.svg)](https://badge.fury.io/py/uvault)
[![CI](https://github.com/petrus-v/uvault/actions/workflows/ci.yml/badge.svg)](https://github.com/petrus-v/uvault/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/petrus-v/uvault/branch/main/graph/badge.svg)](https://codecov.io/gh/petrus-v/uvault)

Development and vaulting workflow for [uv](https://github.com/astral-sh/uv) VCS dependencies.

Secure your Python projects against deleted or force-pushed upstream commits. `uvault` automatically vaults transient VCS references (like GitHub PRs) into your organization's own repositories, while allowing developers to instantly switch dependencies into local editable mode—fully integrated with `pyproject.toml` and `uv`.

## Key Features

1. **Vaulting of Commits**: Never lose code again! Upstream pull requests and branches can be force-pushed or deleted. `uvault` fetches the exact commits your project depends on and pushes them as immutable tags to your own organization's vault repository.
2. **Easy Local Development**: Switch any VCS dependency to local "editable" mode in seconds. `uvault develop` clones the package locally and seamlessly configures `uv` to use your local copy so you can test changes and contribute back.
3. **Automatic GitHub Forking**: When a dependency's repository doesn't exist in your vault organization, `uvault` automatically forks the upstream repository using the GitHub API (via the `[github]` extra), making the setup completely transparent.
4. **Status Monitoring**: Instantly check the health of all your VCS dependencies. `uvault status` shows if PRs are merged or closed, flags new remote commits, and automatically detects orphaned commits caused by upstream force-pushes.

## Documentation

The complete documentation is available in the `docs/` folder:

* [Quickstart & Key Features](https://uvault.apycod.com) - Learn what `uvault` is and how to get started quickly.
* [How-To Guides](https://uvault.apycod.com/how-to/) - Step-by-step guides for installing and using `uvault` in your day-to-day workflow.
* [CLI & Configuration Reference](https://uvault.apycod.com/reference/) - Detailed information on `pyproject.toml` configuration (`[tool.uvault]`) and all CLI commands (`sync`, `add`, `develop`).

## Contributing

Contributions are welcome! If you're interested in improving `uvault`, please check out our [Contributing Guide](https://uvault.apycod.com/contributing/) for details on setting up your development environment, running tests, and submitting PRs.

## Credits & Acknowledgements

A huge thank you to [Stéphane Bidoul](https://github.com/sbidoul) for his continuous inspiration, and particularly for the work on [`pip-preserve-requirements`](https://github.com/sbidoul/pip-preserve-requirements) which strongly influenced the vision and design of this project.
