from pathlib import Path
import tomlkit

from uvault.vcs import GitReference, get_repo_name, compute_vault_urls, get_vcs


class DevelopCommand:
    def __init__(
        self,
        package: str,
        branch: str,
        pyproject_path: str = "pyproject.toml",
    ):
        self.package = package
        self.branch = branch
        self.pyproject_path = Path(pyproject_path)

    def _read_user_config(self) -> dict:
        config_path = Path("~/.config/uvault/config.toml").expanduser()
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    return tomlkit.parse(f.read())
                except Exception:
                    pass
        return {}

    def run(self):
        if not self.pyproject_path.exists():
            print("pyproject.toml not found")
            return 1

        with open(self.pyproject_path, "r", encoding="utf-8") as f:
            doc = tomlkit.parse(f.read())

        tool_uvault = doc.get("tool", {}).get("uvault", {})
        sources = tool_uvault.get("sources", {})

        origin_url = None
        git_ref = None
        subdirectory = None

        if self.package in sources:
            source_cfg = sources[self.package]
            origin_url = source_cfg.get("git")
            if not origin_url:
                print(
                    f"Package {self.package} does not have a valid VCS origin (e.g. 'git') configured."
                )
                return 1

            git_ref = GitReference.from_config(source_cfg)
            subdirectory = source_cfg.get("subdirectory")
            vcs = get_vcs(source_cfg)
        else:
            print(
                f"Could not find configuration for {self.package} in [tool.uvault.sources]."
            )
            print("Please run `uvault add` first to declare it.")
            return 1

        dev_directory = tool_uvault.get("dev_directory", ".src")
        dest_dir = self.pyproject_path.parent / dev_directory / self.package

        repo_name = get_repo_name(origin_url)

        vaults = tool_uvault.get("vcs_vaults", [])
        if vaults:
            vault_config = next((v for v in vaults if v.get("default")), vaults[0])
            _, vault_push_url = compute_vault_urls(repo_name, vault_config)
        else:
            vault_push_url = None

        if dest_dir.exists():
            print(f"Directory {dest_dir} already exists. Checking status...")
            # Check if clean
            if not vcs.check_clean_state(dest_dir):
                print(f"Error: {dest_dir} has uncommitted changes. Aborting.")
                return 1
        else:
            print(f"Cloning {origin_url} into {dest_dir}...")
            dest_dir.parent.mkdir(parents=True, exist_ok=True)
            vcs.clone(origin_url, dest_dir)

        # Configure remotes
        vcs.set_remote(dest_dir, "origin", origin_url)

        if vault_push_url:
            vcs.set_remote(dest_dir, "vault", vault_push_url)

        user_config = self._read_user_config()
        remotes = user_config.get("remotes", {})
        for remote_name, remote_prefix in remotes.items():
            if remote_name in ("origin", "vault"):
                continue
            remote_url = f"{remote_prefix.rstrip('/')}/{repo_name}.git"
            # just add the remote without fetching
            vcs.set_remote(dest_dir, remote_name, remote_url)

        # Checkout requested branch or ref
        if not vcs.checkout_reference(dest_dir, origin_url, git_ref, self.branch):
            print(
                f"Could not resolve reference {git_ref.value if git_ref else 'None'} at {origin_url}"
            )
            return 1

        if "uv" not in doc["tool"]:
            doc["tool"].add("uv", tomlkit.table())
        if "sources" not in doc["tool"]["uv"]:
            doc["tool"]["uv"].add("sources", tomlkit.table())

        uv_sources = doc["tool"]["uv"]["sources"]

        new_source = tomlkit.inline_table()
        # Compute relative path
        rel_path = f"./{dev_directory.rstrip('/')}/{self.package}"
        if subdirectory:
            rel_path = f"{rel_path}/{subdirectory}"
        new_source["path"] = rel_path
        new_source["editable"] = True

        uv_sources[self.package] = new_source

        with open(self.pyproject_path, "w", encoding="utf-8") as f:
            f.write(tomlkit.dumps(doc))

        print(f"Updated pyproject.toml to use local editable path for {self.package}")
        print("Please run `uv sync` or `uv lock` to update your uv.lock file.")

        return 0
