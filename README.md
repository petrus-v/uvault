# uvault

Development and vaulting workflow for [uv](https://github.com/astral-sh/uv) VCS dependencies.

Secure your Python projects against deleted or force-pushed upstream commits.

`uvault` automatically vaults transient VCS references (like GitHub PRs)
into your organization's own repositories, while allowing developers to instantly
switch dependencies into local editable mode—fully integrated with pyproject.toml and uv.

## Key Features

1. **Vaulting of Commits**: Never lose code again! Upstream pull requests and branches can be force-pushed or deleted. `uvault` fetches the exact commits your project depends on and pushes them as immutable tags to your own organization's vault repository.
2. **Easy Local Development**: Switch any VCS dependency to local "editable" mode in seconds. `uvault develop` clones the package locally and seamlessly configures `uv` to use your local copy so you can test changes and contribute back.

## Quickstart

### 1. Add a Dependency

Use `uvault add` to register an intention for a dependency. You can pass a PEP 508 URL or rely on automatic URL guessing if the package is already published.

```bash
uvault add odoo-addon-my-package https://github.com/OCA/my-repo --pr 123 --subdirectory my_package
```

### 2. Vault and Lock

Synchronize the dependency with your vault and lock it in `uv`.

```bash
uvault sync
uv lock
```

### 3. Develop Locally

Need to edit the dependency? Clone it instantly and set it as an editable dependency in `[tool.uv.sources]`.

```bash
uvault develop my-addon
uv sync
```
