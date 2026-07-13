# Tutorials / How-To

## How to manage and vault dependencies

`uvault` is built around a typical workflow: declaring a dependency intention, synchronizing it to your vault, and (optionally) switching to local development mode.

### Installation (Recommended)

To get the most out of `uvault`, especially its ability to automatically discover repository URLs via package metadata when using the `uvault add` command, we highly recommend installing it as a development dependency in your project:

```bash
uv add --dev uvault
```

By installing it within your project's environment, `uvault` gains access to the local site-packages, allowing it to easily read the metadata of your project's existing dependencies.

!!! tip "Using `uvault` via `uv run`"
    When `uvault` is installed as a project dependency, running `uv run uvault <command>` triggers an automatic environment synchronization by `uv`. If you are adding a new dependency to your project, this automatic sync might fail because the new dependency isn't vaulted/resolved yet.

    To avoid this, use the `--frozen` flag when invoking `uvault` (e.g., `uv run --frozen uvault add ...` and `uv run --frozen uvault sync`), or ensure you run the `uvault` commands *before* adding the dependency to your `pyproject.toml`.

### Step 1: Add a new dependency (`uvault add`)

Instead of manually editing the `pyproject.toml` file, use the `uvault add` command to declare an intention in `[tool.uvault.sources]`.

```bash
uvault add my-package https://github.com/OCA/my-repo --pr 123 --subdirectory my_package
```

If the repository URL is already known (published package), you can omit it and `uvault` will try to guess it from the package metadata:
```bash
uvault add my-package --branch 16.0
```

*Note: This command only configures your intention. It does not update your `uv` lockfile.*

### Step 2: Synchronize and Vault (`uvault sync`)

Once you have declared your dependencies, run the synchronization command to fetch them and push them to your organization's vault repository.

```bash
uvault sync
```

The command will:

1. Fetch the exact commit of the targeted branch or PR.
2. Clone this repository into the local cache (if necessary).
3. Push this commit to your vault repository as a frozen tag (e.g. `ppr-<sha>`).
4. Automatically update the `[tool.uv.sources]` block in `pyproject.toml` to point to this immutable reference.

**Crucial Step:** After syncing, you must instruct `uv` to resolve the new dependencies:
```bash
uv lock
# or
uv sync
```

#### Update an existing reference

If the original PR has been updated (new commits):

```bash
uvault sync --update
```

This will force the retrieval of new changes and update the vault reference. You can also target specific packages (which automatically implies an update):

```bash
uvault sync --package my-addon
uvault sync -P my-addon -P another-addon
```

### Step 3: Develop Locally (`uvault develop`)

When you need to make modifications to a vaulted dependency, you can switch it into local editable mode in seconds.

```bash
uvault develop my-addon my-feature-branch
```

This command will:

1. Clone the repository into your local workspace (e.g., `./.src/my-addon`).
2. Automatically configure your custom vault remotes (defined in `~/.config/uvault/config.toml`) so you can push your work easily.
3. Replace the remote reference in `[tool.uv.sources]` with a local, editable path (`editable = true`).
4. Creates and checks out the new branch (`git checkout -b <branch>`), or simply switches to it if it already exists.

**Crucial Step:** Once the local path is set, make sure to synchronize your environment:
```bash
uv sync
```

### Step 4: Releasing with `bump-my-version`

When releasing your project, the versions of vaulted dependencies' tags should ideally track the new release version without pulling potentially unstable, newer commits from the upstream source.

Use the `uvault release` command in combination with tools like `bump-my-version`.

> **Crucial Warning:** `bump-my-version` must be configured to only change the main project version in `pyproject.toml`. It should **not** automatically search and replace > version strings in dependency tags (`[tool.uv.sources]`), as this can break the reference.

Instead, use the `pre_commit_hooks` from `bump-my-version` to automatically run `uvault release` and update the lockfile before the release commit is made.

Here is an example `bump-my-version` configuration in `pyproject.toml`, assuming you have also configured a custom `release_tag_template` to omit the commit SHA:

```toml
[tool.uvault]
tag_prefix = "apycod"
release_tag_template = "{project_version}+{tag_prefix_normalized}.{pkg_normalized}"

[tool.bumpversion]
current_version = "1.0.0"
commit = true
tag = true
message = "chore: bump version {current_version} → {new_version}"
pre_commit_hooks = [
    "uv run uvault release",
    "uv sync",
    "git add pyproject.toml uv.lock"
]

# Files where the version should be bumped
[[tool.bumpversion.files]]
filename = "pyproject.toml"
search = 'version = "{current_version}"'
replace = 'version = "{new_version}"'
```

**What happens during `uvault release`?**

1. It reads the newly bumped version in `pyproject.toml`.
2. It extracts the current commit SHA from the existing tag in `[tool.uv.sources]` for each vaulted dependency.
3. It pushes a new tag to the vault pointing to the exact same commit, without pulling new updates from the upstream repository. The tag name will be formatted according to the PEP 440 default (e.g. `1.0.1+apycod.my.package.abcdef1`) or your customized template (e.g. `1.0.1+apycod.my.package`).
4. It updates `[tool.uv.sources]` with the newly generated tags.
5. If any package is currently in `develop` mode (meaning it doesn't have a vaulted tag in `uv.sources`), `uvault` will revert it to a standard vaulted state before tagging (unless you run it with `--keep-develop`, which would skip the package).

### Step 5: Monitoring dependencies (`uvault status`)

The `uvault status` command allows you to inspect the current state of all your vaulted dependencies, helping you keep track of pull requests, identify merged code, and detect potential force-pushes or commit lag.

#### Prerequisites: GitHub Integration

To get the most out of the `status` command when working with GitHub repositories, you should install the `github` optional dependencies. This allows `uvault` to fetch pull request metadata directly from the GitHub API.

```bash
uv tool install uvault[github]
# or run directly with uvx
uvx --from uvault[github] uvault status
```

**Crucial Step:** To avoid GitHub API rate limits (which will cause `uvault` to automatically retry requests, significantly slowing down the command), you should configure a GitHub Personal Access Token in your `~/.config/uvault/config.toml`:

```toml
[github]
token = "ghp_your_personal_access_token_here"
```

#### Understanding the Output

When you run `uvault status`, the tool compares the commit currently vaulted in your `pyproject.toml` against the latest state of the target branch or pull request.

The command reports several key metrics:
- **Status**: The state of the pull request (if applicable). It can be `ACTIVE` (open), `MERGED` (code is in the base branch), `CLOSED` (rejected/closed), or `UNKNOWN` (cannot determine, e.g. for simple branch references).
- **Lag**: The number of commits your vaulted reference is behind the latest remote head.
- **Diverged**: A warning flag (`True`/`False`) indicating if a force-push occurred on the remote branch, meaning your vaulted commit is no longer part of the remote history.

#### Formatting and Sorting

You can customize the output using the `--format` and `--sort-by` options:

- **Formatting (`--format`)**:
  - `table` (Default): Displays a rich, aligned table with all metrics.
  - `list`: A detailed, multi-line format perfect for reading complete descriptions.
  - `inline`: A concise, single-line per package format, useful for quick scanning or piping to other tools.

- **Sorting (`--sort-by`)**:
  - `name` (Default): Alphabetical order by package name.
  - `status`: Groups packages by their pull request status (e.g., all `MERGED` packages together), making it easy to identify dependencies that need cleanup.

Example:
```bash
uvx --from uvault[github] uvault status --format table --sort-by status
```

### Step 6: Ensuring reproducibility in CI and development (`pre-commit`)

To guarantee that developers do not accidentally commit packages left in local `develop` mode (editable paths) and that the `uv.lock` file is always up-to-date, we recommend configuring `pre-commit` hooks.

!!! important "Hook Ordering"
    It is important to place the `uvault-check` hook **before** the `uv-lock` hook. Since `uvault-check` can automatically fix mismatches in `pyproject.toml` (auto-fix is enabled by default), running it first allows `uv-lock` to subsequently detect the changes and automatically regenerate `uv.lock`. If you want to disable the auto-fix feature, you can pass the `--no-auto-fix` argument.

Here is an example `.pre-commit-config.yaml` configuration:

```yaml
repos:
  # Verify that no vaulted dependencies are left in develop/editable mode and auto-fix if possible
  - repo: https://github.com/petrus-v/uvault
    rev: v0.5.1  # Use the latest version
    hooks:
      - id: uvault-check

  # Verify that uv.lock is synchronized with pyproject.toml (and auto-fix/regenerate uv.lock)
  - repo: https://github.com/astral-sh/uv-pre-commit
    rev: 0.11.28  # Use the latest version
    hooks:
      - id: uv-lock
```
