# Reference

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
ssh_only = true                         # (Optional) If true, generates ssh:// URLs instead of https://. Defaults to false.
default = true                          # (Optional) Marks this vault as the default for synchronizing packages.

# Declaration of dependencies to synchronize
[tool.uvault.sources]
my-package = { git = "https://github.com/OCA/repository", rev = "refs/pull/100/head", subdirectory = "my_package" }
```

## CLI Commands

### `uvault sync`

Synchronizes remote references to the vault repository and updates `[tool.uv.sources]`.

**Options:**
* `-P, --package <name>` : Synchronize only the specified package. Can be used multiple times. Implies `--update` for the specified packages.
* `-U, --update` : Force update of the reference in the vault even if it already exists (applies to all processed packages).

::: uvault.cli
