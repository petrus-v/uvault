from pathlib import Path

from uvault.vcs import get_repo_name, compute_vault_urls
from uvault.source import PackageSource
from uvault.project import PyProject, read_user_config, normalize_pkg_name


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

    def run(self):
        project = PyProject(self.pyproject_path)
        try:
            project.read()
        except FileNotFoundError:
            print("pyproject.toml not found")
            return 1

        uvault_sources = project.uvault_sources

        origin_url = None
        git_ref = None
        subdirectory = None

        norm_package = normalize_pkg_name(self.package)

        if norm_package in uvault_sources:
            uvault_source = uvault_sources[norm_package]
            canonical_name = uvault_source.name
            origin_url = uvault_source.origin_url
            if not origin_url:
                print(
                    f"Package {canonical_name} does not have a valid VCS origin (e.g. 'git') configured."
                )
                return 1

            git_ref = uvault_source.get_git_reference()
            subdirectory = uvault_source.subdirectory
            vcs = uvault_source.get_vcs()
        else:
            print(
                f"Could not find configuration for {self.package} in [tool.uvault.sources]."
            )
            print("Please run `uvault add` first to declare it.")
            return 1

        dev_directory = project.dev_directory
        dest_dir = self.pyproject_path.parent / dev_directory / canonical_name

        repo_name = get_repo_name(origin_url)

        vault_config = project.get_vault_config()
        if vault_config:
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

        user_config = read_user_config()
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

        new_source = PackageSource(canonical_name, {})
        # Compute relative path
        rel_path = f"./{dev_directory.rstrip('/')}/{canonical_name}"
        if subdirectory:
            rel_path = f"{rel_path}/{subdirectory}"
        new_source.update(path=rel_path, editable=True)

        project.set_uv_source(canonical_name, new_source)
        project.write()

        print(f"Updated pyproject.toml to use local editable path for {canonical_name}")
        print("Please run `uv sync` or `uv lock` to update your uv.lock file.")

        return 0
