# Reference

## Installation & Usage Modes

`uvault` can be executed in two different ways depending on your needs:

### 1. As a Project Development Dependency (Recommended)

Installing `uvault` as a dev dependency gives it access to your project's environment. This is crucial if you want `uvault add` to automatically guess repository URLs based on the metadata of your installed packages.

```bash
uv add --dev uvault
uv run uvault --help
```

### 2. As an Independent Tool via `uvx`

If you prefer keeping your dependencies minimal and don't need the automatic URL resolution feature, you can run `uvault` purely as an isolated, ephemeral tool using `uvx`.

```bash
uvx uvault sync
```

## `pyproject.toml` Configuration

The intention configuration is located in the `[tool.uvault]` section:

```toml
[tool.uvault]
tag_prefix = "apycod-"               # (Optional) Prefix for generated tags. Defaults to "".
include_project_version = true          # (Optional) Includes the current project's version in the vault tag. Defaults to true.
dev_directory = ".src/"                 # (Optional) Directory for developed sources. Defaults to ".src/".

# VCS Vault Configuration
[[tool.uvault.vcs_vaults]]
provider = "github.com"                 # (Required) The git hosting provider (e.g., "github.com" or "gitlab.com").
owner = "petrus-v"                      # (Optional) The user or organization owning the vault repository.
fetch_ssh = true                        # (Optional) If true, generates ssh:// URLs in [tool.uv.sources] instead of https://. Defaults to false.
push_ssh = true                         # (Optional) If true, pushes tags to the vault using ssh://. Defaults to true.
default = true                          # (Optional) Marks this vault as the default for synchronizing packages.

# Declaration of dependencies to synchronize
[tool.uvault.sources]
my-package = { git = "https://github.com/OCA/repository", rev = "refs/pull/100/head", subdirectory = "my_package" }
```

## User Configuration

You can define local machine-specific configurations, such as custom git remotes, in `~/.config/uvault/config.toml`. These remotes will be automatically added to the repository when running `uvault develop`.

```toml
[remotes]
myorg = "https://gitlab.com/myorg/"
perso = "ssh://git@github.com/personal/"
```

## CLI Commands

### `uvault sync`

Synchronizes remote references to the vault repository and updates `[tool.uv.sources]`.

**Note:** By default, `uvault sync` will skip any package that is already declared in `[tool.uv.sources]`.

**Options:**
* `-P, --package <name>` : Synchronize only the specified package. Can be used multiple times. Implies `--update` for the specified packages.
* `-U, --update` : Force update of the reference in the vault and in `[tool.uv.sources]` even if it already exists.
* `--delete-extra` : Removes any package from `[tool.uv.sources]` that is not declared in `[tool.uvault.sources]`.

### `uvault add`

Adds a new dependency intention directly into `[tool.uvault.sources]` without manual file editing.

**Arguments:**
* `<package>` : The name of the package to add.
* `[url]` : (Optional) The VCS URL (e.g. `https://github.com/OCA/my-addon`). If omitted, `uvault` will attempt to guess it from PyPI metadata.

**Options:**
* `--branch <name>` : Target a specific branch.
* `--tag <name>` : Target a specific tag.
* `--pr <number>` : Target a pull/merge request number.
* `--rev <hash>` : Target a specific commit hash or exact reference.
* `--subdirectory <path>` : The subdirectory within the repository where the Python package is located.

### `uvault develop`

Switches a vaulted dependency into local editable mode for active development.

**Arguments:**
* `<package>` : The name of the package to develop locally (must be declared in `[tool.uvault.sources]`).
* `<branch>` : The name of the branch to checkout or create.

**Workflow Details:**
1. Clones (using a fast partial blobless clone) or fetches the repository into your `.src/` directory.
2. Creates and checks out the new branch (`git checkout -b <branch>`), or switches to it if it exists (`git checkout <branch>`).
3. Sets up remotes, including `origin`, `vault`, and any other custom remotes defined in `~/.config/uvault/config.toml`.
4. Modifies `[tool.uv.sources]` to use `{ path = "./.src/<package>", editable = true }`.

::: uvault.cli
