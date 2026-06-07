# uvault

Development and vaulting workflow for [uv](https://github.com/astral-sh/uv) VCS dependencies.

Secure your Python projects against deleted or force-pushed upstream commits. `uvault` automatically vaults transient VCS references (like GitHub PRs) into your organization's own repositories, while allowing developers to instantly switch dependencies into local editable mode—fully integrated with `pyproject.toml` and `uv`.

## Documentation

The complete documentation is available in the `docs/` folder:

* [Quickstart & Key Features](docs/index.md) - Learn what `uvault` is and how to get started quickly.
* [How-To Guides](docs/how-to.md) - Step-by-step guides for installing and using `uvault` in your day-to-day workflow.
* [CLI & Configuration Reference](docs/reference.md) - Detailed information on `pyproject.toml` configuration (`[tool.uvault]`) and all CLI commands (`sync`, `add`, `develop`).
