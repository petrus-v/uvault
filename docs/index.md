# uvault

[![PyPI version](https://badge.fury.io/py/uvault.svg)](https://badge.fury.io/py/uvault)
[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/petrus-v/uvault)
[![CI](https://github.com/petrus-v/uvault/actions/workflows/ci.yml/badge.svg)](https://github.com/petrus-v/uvault/actions/workflows/ci.yml)

Development and vaulting workflow for [uv](https://github.com/astral-sh/uv) VCS dependencies.

Secure your Python projects against deleted or force-pushed upstream commits.

`uvault` automatically vaults transient VCS references (like GitHub PRs)
into your organization's own repositories, while allowing developers to instantly
switch dependencies into local editable mode—fully integrated with `pyproject.toml` and `uv`.

## Key Features

1. **Vaulting of Commits**: Never lose code again! Upstream pull requests and branches can be force-pushed or deleted. `uvault` fetches the exact commits your project depends on and pushes them as immutable tags to your own organization's vault repository.
2. **Easy Local Development**: Switch any VCS dependency to local "editable" mode in seconds. `uvault develop` clones the package locally and seamlessly configures `uv` to use your local copy so you can test changes and contribute back.
3. **Automatic GitHub Forking**: When a dependency's repository doesn't exist in your vault organization, `uvault` automatically forks the upstream repository using the GitHub API (via the `[github]` extra), making the setup completely transparent.
4. **Status Monitoring**: Instantly check the health of all your VCS dependencies. `uvault status` shows if PRs are merged or closed, flags new remote commits, and automatically detects orphaned commits caused by upstream force-pushes.

## Quickstart

### Add a Dependency

Use `uvault add` to register an intention for a dependency. You can pass a PEP 508 URL or rely on automatic URL guessing if the package is already published.

```bash
uvault add odoo-addon-my-package https://github.com/OCA/my-repo --pr 123 --subdirectory my_package
```

### Develop Locally

Need to edit the dependency? Clone it instantly and set it as an editable dependency in `[tool.uv.sources]`.

```bash
uvault develop my-package feat-branch
uv sync
```

### Vault and Lock

Synchronize the dependency with your vault and lock it in `uv`.

```bash
uvault sync
uv lock
```

### Check Dependency Status

Review the status of your VCS dependencies at a glance to see if PRs are merged, or if your vaulted commits are lagging behind or orphaned due to a force-push.

```bash
uvault status --format inline --sort-by status
```

### Semantic Release Tagging

When you release a new version of your project, use `uvault release` to semantically tag all your vaulted dependencies with your project's new version. This updates the tags in `[tool.uv.sources]` while keeping the exact same commit references, making it easy to introspect exactly which code was used for any given release.

```bash
uvault release
uv sync
```
