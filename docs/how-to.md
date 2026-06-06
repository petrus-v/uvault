# Tutorials / How-To

## How to synchronize and lock dependencies

Once you have declared your dependencies in the `[tool.uvault.sources]` section, you can use the `uvault sync` command to lock them and share them via your own vault.

### Step 1: Declare the dependency
In `pyproject.toml`, add or verify your dependency:

```toml
[tool.uvault.sources]
my-addon = { git = "https://github.com/OCA/my-addon", rev = "refs/pull/123/head", subdirectory = "my_addon" }
```

### Step 2: Run synchronization
Simply run the `uvault sync` command:

```bash
uvault sync
```

The command will:
1. Fetch the exact commit of the targeted branch or PR.
2. Clone this repository into the local cache (if necessary).
3. Push this commit to your vault repository as a frozen tag (e.g. `ppr-<sha>`).
4. Automatically update the `[tool.uv.sources]` block in `pyproject.toml` to point to this immutable reference.

### Step 3: Update an existing reference
If the original PR has been updated (new commits):

```bash
uvault sync --update
```

This will force the retrieval of new changes and update the vault reference. You can also target specific packages. When you specify a package, the update is forced automatically:

```bash
uvault sync --package my-addon
```

You can also specify multiple packages:

```bash
uvault sync -P my-addon -P another-addon
```
