# Tutorials / How-To

## How to manage and vault dependencies

`uvault` is built around a typical workflow: declaring a dependency intention, synchronizing it to your vault, and (optionally) switching to local development mode.

### Installation & Execution (Recommended)

The recommended way to use `uvault` is as an independent tool via `uvx`. Running it through `uvx` runs `uvault` in an isolated environment, avoiding version conflicts and preventing `uv run` from attempting to synchronize your project's environment when a dependency is not yet resolved.

```bash
# To run any uvault command:
uvx --with uvault[github] uvault <command>
```

#### Alternative: Installing as a Project Development Dependency

While running via `uvx` is the recommended approach, you can also install `uvault` as a development dependency inside your project:

```bash
uv add --dev uvault[github]
```

!!! tip "Using `uvault` via `uv run` with `--frozen`"
    If you install `uvault` as a project dependency, running `uv run uvault <command>` triggers an automatic environment synchronization by `uv`. If you are in the middle of adding or updating a vaulted dependency, this sync might fail.

    To bypass this, always run with the `--frozen` flag:
    ```bash
    uv run --frozen uvault <command>
    ```


### Step 1: Add a new dependency (`uvault add`)

Instead of manually editing the `pyproject.toml` file, use the `uvault add` command to declare an intention in `[tool.uvault.sources]`.

```bash
uvault add my-package https://github.com/OCA/my-repo --pr 123 --subdirectory my_package
```

If the repository URL is already known (published package), you can omit it and `uvault` will try to guess it from the local package metadata or by querying the PyPI JSON API:
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

### Step 4: Releasing and Version Lifecycle with `bump-my-version`

When managing a project's release lifecycle, understanding how development versions and final releases relate is crucial under **PEP 440**.

#### The PEP 440 Version Ordering Constraint

Under PEP 440, developmental releases (e.g., `.dev0`, `.dev1`) are considered **pre-releases** and are ordered *prior* to their corresponding final release.

```python
from packaging.version import Version
Version("1.0.1.dev0") > Version("1.0.1")  # False
Version("1.0.2.dev0") > Version("1.0.1")  # True
```

This means that if you release version `1.0.1`, you should **not** configure your next development iteration version to be `1.0.1.dev0`, as it would be considered older than the version you just released. Instead, immediately after releasing `1.0.1`, you must bump the project version to `1.0.2.dev0` (or `1.1.0.dev0`).

#### The Role of `uvault` in Bumping Versions

`uvault` is not a version manager. It reads the version of your project defined in `pyproject.toml` to name the vaulted tags (using `{project_version}` or `{project_version_dev}`).

It is **not** the role of `uvault` to take the initiative to automatically increment version numbers. `uvault` cannot guess whether your next release will be a patch, minor, or major bump. The version lifecycle should be managed by you (or your CI/CD pipeline) using a tool like `bump-my-version`.

#### Recommended `bump-my-version` Configuration

To support transitioning from a development version (e.g., `1.0.1.dev0`) to a final release (e.g., `1.0.1`), and then automatically preparing the next development version (e.g., `1.0.2.dev0`), configure your `pyproject.toml` as follows:

```toml
[tool.uvault]
tag_prefix = "apycod"
release_tag_template = "{project_version}+{tag_prefix_normalized}.{pkg_normalized}"

[tool.bumpversion]
current_version = "1.0.0.dev0"
parse = "(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)(\\.(?P<release>dev)(?P<build>\\d+))?"
serialize = [
    "{major}.{minor}.{patch}.{release}{build}",
    "{major}.{minor}.{patch}"
]
commit = true
tag = true
tag_name = "v{new_version}"
message = "chore: bump version {current_version} → {new_version}"
allow_shell_hooks = true

pre_commit_hooks = [
    # Conditionally execute uvault release only if the new version is a final release (does not contain 'dev')
    "[[ \"$BVHOOK_NEW_VERSION\" =~ dev ]] || uvx --with uvault[github] uvault release",
    "uv sync",
    "git add pyproject.toml uv.lock"
]

[tool.bumpversion.parts.release]
values = ["dev", "final"]
optional_value = "final"

# Files where the version should be bumped
[[tool.bumpversion.files]]
filename = "pyproject.toml"
search = 'version = "{current_version}"'
replace = 'version = "{new_version}"'
```

#### Workflow and Commands

With the configuration above, here is how you run your release cycle:

1. **Working in Dev Mode:**
   Your version in `pyproject.toml` is currently `1.0.1.dev0`. Any `uvault sync` commands will use this version for tagging dependencies (e.g., `1.0.1.dev0+apycod.my.package.abcdef1`).

2. **Publishing the Final Release:**
   When you are ready to publish, bump the `release` part:
   ```bash
   uvx bump-my-version bump release
   ```
   * **What happens:**
     * The version becomes `1.0.1`.
     * The `pre_commit_hooks` detect that the version is final (doesn't contain `dev`) and execute `uvx --with uvault[github] uvault release`.
     * `uvault release` freezes the current commits of your vaulted dependencies under the release version tag `1.0.1`.
     * `bump-my-version` commits the changes and creates the Git tag `v1.0.1`.

3. **Preparing the Next Development Iteration:**
   Immediately after the release, bump the version to start the next dev cycle:
   ```bash
   uvx bump-my-version bump patch --no-tag
   ```
   * **What happens:**
     * The version increments the patch number and resets the release part, becoming `1.0.2.dev0`.
     * The `pre_commit_hooks` detect the `dev` suffix and skip the `uvault release` call, leaving your vaulted dependencies untouched.
     * `bump-my-version` commits the update to `1.0.2.dev0` (e.g. "Bump version: 1.0.1 → 1.0.2.dev0") but does **not** create a Git tag (due to `--no-tag`).
     * You are now ready to continue standard development.


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
