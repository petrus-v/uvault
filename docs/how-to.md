# Tutorials / How-To

## How to manage and vault dependencies

`uvault` is built around a typical workflow: declaring a dependency intention, synchronizing it to your vault, and (optionally) switching to local development mode.

### Installation (Recommended)

To get the most out of `uvault`, especially its ability to automatically discover repository URLs via package metadata when using the `uvault add` command, we highly recommend installing it as a development dependency in your project:

```bash
uv add --dev uvault
```

By installing it within your project's environment, `uvault` gains access to the local site-packages, allowing it to easily read the metadata of your project's existing dependencies.

### Step 1: Add a new dependency (`uvault add`)

Instead of manually editing the `pyproject.toml` file, use the `uvault add` command to declare an intention in `[tool.uvault.sources]`.

```bash
uvault add my-addon https://github.com/OCA/my-addon --pr 123 --subdirectory my_addon
```

If the repository URL is already known (published package), you can omit it and `uvault` will try to guess it from the package metadata:
```bash
uvault add my-addon --branch 16.0
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
