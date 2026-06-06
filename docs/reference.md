# Reference

## `pyproject.toml` Configuration

The intention configuration is located in the `[tool.uvault]` section:

```toml
[tool.uvault]
tag_prefix = "ppr-"  # (Optional) Tag prefix, defaults to "ppr-"
dev_directory = ".src/"

# VCS Vault Configuration
[[tool.uvault.vcs_vaults]]
provider = "github.com"
owner = "my-org"
ssh_only = true
default = true

# Declaration of dependencies to synchronize
[tool.uvault.sources]
my-package = { git = "https://github.com/OCA/my-package", rev = "refs/pull/100/head" }
```

## CLI Commands

### `uvault sync`

Synchronizes remote references to the vault repository and updates `[tool.uv.sources]`.

**Options:**
* `-P, --package <name>` : Synchronize only the specified package. Can be used multiple times. Implies `--update` for the specified packages.
* `-U, --update` : Force update of the reference in the vault even if it already exists (applies to all processed packages).

::: uvault.cli
