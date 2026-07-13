# Reference

## Installation & Usage Modes

`uvault` can be executed in two different ways depending on your needs:

### 1. As an Independent Tool via `uvx` (Recommended)

Running `uvault` via `uvx` is the cleanest and most robust method. It executes `uvault` in an isolated, ephemeral environment, which prevents `uv` from attempting to sync your project's dependencies before they are fully vaulted.

```bash
uvx --with uvault[github] uvault sync
```

*Note: The `[github]` extra installs `pygithub`, which enables automatic forking into your GitHub organization during `uvault sync` and status checks.*

### 2. As a Project Development Dependency

If you want `uvault add` to automatically resolve repository URLs by reading the metadata of packages already installed in your local virtual environment, you can install it as a dev dependency:

```bash
uv add --dev uvault[github]
```

When installed as a dependency, run commands using `uv run --frozen` to prevent environment sync failures when dependencies are unresolved:
```bash
uv run --frozen uvault sync
```


## `pyproject.toml` Configuration

The intention configuration is located in the `[tool.uvault]` section:

```toml
[tool.uvault]
tag_prefix = "apycod"                   # (Optional) Prefix for generated tags. Defaults to "".
tag_template = "..."                    # (Optional) Template for tags in sync mode. Defaults to PEP 440 compatible format.
release_tag_template = "..."            # (Optional) Template for tags in release mode. Defaults to PEP 440 compatible format.
dev_directory = ".src/"                 # (Optional) Directory for developed sources. Defaults to ".src/".
ignore_labels = ["mod:", "series:"]     # (Optional) PR labels prefixes to ignore in 'uvault status'. Defaults to ["mod:", "series:"].

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

## Tag Nomenclature & Templating

`uvault` uses PEP 440-compatible templates for the tags it pushes to your vault. You can customize the tags generated during standard synchronization (`uvault sync`) and during releases (`uvault release`) using custom templates in your `pyproject.toml`.

### Default Nomenclature (PEP 440 Compliant)

By default, to avoid tag collisions when multiple packages share the same Git repository (monorepo), the generated tags are structured as PEP 440 local version identifiers:

* **`uvault sync`** (default template):
  - With a tag prefix: `{project_version_dev}+{tag_prefix_normalized}.{pkg_normalized}.{sha}` (e.g., `1.0.0.dev0+apycod.my.package.abcdef1`)
  - Without a tag prefix: `{project_version_dev}+{pkg_normalized}.{sha}` (e.g., `1.0.0.dev0+my.package.abcdef1`)
* **`uvault release`** (default template):
  - With a tag prefix: `{project_version}+{tag_prefix_normalized}.{pkg_normalized}.{sha}` (e.g., `1.0.0+apycod.my.package.abcdef1`)
  - Without a tag prefix: `{project_version}+{pkg_normalized}.{sha}` (e.g., `1.0.0+my.package.abcdef1`)

### Template Placeholders

The following placeholders can be used in both `tag_template` and `release_tag_template`:

* `{project_version}`: The version of the project defined in `pyproject.toml` (e.g., `1.0.0`). Defaults to `0.0.0` if not set.
* `{project_version_dev}`: The version of the project with a `.dev0` suffix appended (e.g., `1.0.0.dev0`), or untouched if the version already contains a `dev` suffix. Defaults to `0.0.0.dev0` if not set.
* `{tag_prefix}`: The raw `tag_prefix` string (e.g., `apycod-`).
* `{tag_prefix_normalized}`: The `tag_prefix` normalized to be PEP 440 local version segment compliant (replacing non-alphanumeric chars with dots, e.g. `apycod`).
* `{pkg_name}`: The raw package name (e.g., `my-package`).
* `{pkg_normalized}`: The package name normalized to be PEP 440 local version segment compliant (e.g. `my.package`).
* `{sha}`: The git commit SHA of the package (e.g., `abcdef1`).

### Custom Template Examples

If you prefer a non-PEP 440 structure (for example, standard namespaced tags for monorepos):

```toml
[tool.uvault]
# Namespaced release tag: my-package-1.0.0+apycod.abcdef1
release_tag_template = "{pkg_name}-{project_version}+{tag_prefix_normalized}.{sha}"

# Simple prefixed sync tag: apycod-my-package-abcdef1
tag_template = "{tag_prefix}{pkg_name}-{sha}"
```

## User Configuration

You can define local machine-specific configurations, such as custom git remotes and your GitHub token, in `~/.config/uvault/config.toml`.

```toml
[remotes]
myorg = "https://gitlab.com/myorg/"
perso = "ssh://git@github.com/personal/"

[github]
token = "ghp_YOUR_GITHUB_TOKEN"
```

* Remotes will be automatically added to the repository when running `uvault develop`.
* The github token is used for automatically forking repositories when running `uvault sync`. For this to work, you need to have the `pygithub` optional dependency installed (e.g., `uv pip install uvault[github]`). In GitHub the token needs `fork` permissions.

## CLI Commands

### `uvault sync`

Synchronizes remote references to the vault repository and updates `[tool.uv.sources]`.

**Note:** By default, `uvault sync` will skip any package that is already declared in `[tool.uv.sources]`.

**Flags:**

* `-P <package>, --package <package>` : Only sync the specified package. Can be used multiple times.
* `--update` : Forces an update of the package(s) even if they are already present in `[tool.uv.sources]`.
* `--delete-extra` : Removes any package found in `[tool.uv.sources]` that is not declared in `[tool.uvault.sources]`.
* `--keep-develop` : By default, packages in develop mode (`editable = true` or using `path`) are restored to their vaulted state during sync. Use this flag to keep them in develop mode.

**Automatic Forking (GitHub):**

If `uvault sync` attempts to vault a repository that does not exist in your organization, it will automatically attempt to fork the original repository.
To enable this feature:

1. Ensure the optional dependency `pygithub` is installed (e.g., `uv pip install uvault[github]`).
2. The source repository must be hosted on GitHub (`provider = "github.com"`).
3. You must provide a valid token in your user configuration (`~/.config/uvault/config.toml`) under the `[github]` section (key `token`).

**How to create a secure Fine-grained GitHub Token for forking:**

If you want to restrict your token so it can *only* fork repositories into your target organization (e.g., `apycod`) and nothing else:

1. Go to your GitHub **Settings** > **Developer settings** > **Personal access tokens** > **Fine-grained tokens**.
2. Click **Generate new token**.
3. **Resource owner**: Select your target organization (e.g., `apycod`). *Note: You must have sufficient privileges in the organization, and it must allow fine-grained PATs.*
4. **Repository access**: Select **All repositories** (required because the token needs permission to create new repositories that do not exist yet).
5. **Permissions**:
   - Under **Repository permissions**, set **Administration** to **Read and write** (required to create the fork).
   - Set **Contents** to **Read and write**.
6. Generate the token and paste it into your `~/.config/uvault/config.toml` file.
*(Note: Fine-grained tokens have implicit read access to all public repositories, which allows them to read the upstream source repository before forking it into your organization).*

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

### `uvault release`

Updates the tags in `[tool.uv.sources]` with the new project version, keeping the exact same commit references.

**Workflow Details:**

When releasing a project (e.g., via `bump-my-version`), this command extracts the existing commit SHA from each vaulted package's tag in `[tool.uv.sources]`. It then constructs a new tag with the new project version and pushes it directly to the vault. This avoids fetching any new, unexpected commits from the source repository. Packages currently in develop mode will fall back to a standard sync.

**Flags:**

* `-P <package>, --package <package>` : Apply the release tag only to the specified vaulted package. Can be used multiple times.
* `--keep-develop` : By default, packages in develop mode are restored to their vaulted state before tagging. Use this flag to keep them in develop mode (skipping their release).

!!! note "Development Version Lifecycle (PEP 440)"
    Under PEP 440, developmental versions (e.g., `1.0.1.dev0`) are ordered *prior* to their corresponding final release (`1.0.1`). When running `uvault release`, ensure your project version has been bumped to the final release version. To learn how to configure `bump-my-version` to manage this cycle automatically, see [Step 4 of the How-To guide](./how-to.md#step-4-releasing-and-version-lifecycle-with-bump-my-version).

### `uvault status`

Displays a real-time summary of your VCS dependencies (branches, pull requests) to quickly identify packages that need syncing, reviewing, or updating.

**Options:**

* `-P <package>, --package <package>` : Only check the specified package. Can be used multiple times.
* `--format {list,inline,table}` : Output format (`list`, `inline`, `table`). Default is `list`.
* `--sort-by {status,date,name}` : Sort the results by status, date (last activity), or name. Default is `name`.

**Workflow Details:**

For each package configured in `[tool.uvault.sources]`, `uvault status` queries the GitHub API to fetch the state of the targeted reference:

- **PRs**: Indicates whether they are `OPEN`, `MERGED`, or `CLOSED`. Also surfaces relevant PR labels (excluding prefixes defined in `ignore_labels`, by default `mod:` and `series:`).
- **Branches**: Displays an `ACTIVE` status.

It then compares the commit currently vaulted locally (via `[tool.uv.sources]`) against the remote tip to show:

- The number of **new commits** available (`behind`).
- Whether a **history rewrite (Force-Push)** occurred on the remote branch, leaving your vaulted commit orphaned.

> **Note:** The `status` functionality requires the `pygithub` optional dependency (`uv pip install uvault[github]`) and a valid token configured in `~/.config/uvault/config.toml`.

### `uvault check`

Verifies that your project's dependencies are in a clean, reproducible state. This is especially useful when integrated as a `pre-commit` hook.

**Options:**

* `--no-auto-fix` : Disable automatic fixing of `pyproject.toml`. By default, `uvault check` will automatically restore develop packages to their vaulted state and add missing packages (without pushing/vaulting to the remote vault).
* `--delete-extra` : Ensure that any extra packages in `[tool.uv.sources]` that are not declared in `[tool.uvault.sources]` are removed.

**Workflow Details:**

It performs the following checks on your `pyproject.toml` file:

1. Ensures that every package defined under `[tool.uvault.sources]` is present in `[tool.uv.sources]`.
2. Verifies that none of these dependencies are left in local `develop` mode (e.g., using `path = ...` or `editable = true`).
3. If `--delete-extra` is specified, ensures that no extra packages exist in `[tool.uv.sources]` that are not defined in `[tool.uvault.sources]`.

If any check fails or if any auto-fixes/modifications are made to `pyproject.toml`, the command exits with code `1` (which blocks the commit in a `pre-commit` setup so you can review and add the changes). If all checks pass and no changes are needed, it exits with code `0`.

::: uvault.cli
