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

Here is an example `bump-my-version` configuration in `pyproject.toml`, assuming you have also configured `include_sha_in_release = false` in your `[tool.uvault]` section:

```toml
[tool.uvault]
tag_prefix = "apycod"
include_sha_in_release = false

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
3. It pushes a new tag to the vault pointing to the exact same commit, without pulling new updates from the upstream repository. The tag name will be cleaner (e.g. `apycod-1.0.1`) if `include_sha_in_release` is `false`, or it will include the SHA (e.g. `apycod-1.0.1+<sha>`) if left to its default `true`.
4. It updates `[tool.uv.sources]` with the newly generated tags.
5. If any package is currently in `develop` mode (meaning it doesn't have a vaulted tag in `uv.sources`), `uvault` will revert it to a standard vaulted state before tagging (unless you run it with `--keep-develop`, which would skip the package).
