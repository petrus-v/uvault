import subprocess
from pathlib import Path
from uvault.vcs import (
    VcsProvider,
    GitReference,
    RefType,
    get_repo_name,
    compute_vault_urls,
)
from uvault.source import PackageSource
from uvault.project import PyProject, normalize_pkg_name


class PackageSyncer:
    def __init__(
        self,
        pkg: str,
        uvault_source: PackageSource,
        cache_dir: Path,
        vault_config: dict,
        tag_prefix: str,
        force_update: bool,
        project_version: str | None = None,
        include_sha_in_release: bool = True,
        current_sha: str | None = None,
        is_release: bool = False,
    ):
        self.pkg = pkg
        self.uvault_source = uvault_source
        self.vcs = uvault_source.get_vcs()
        self.cache_dir = cache_dir
        self.vault_config = vault_config
        self.tag_prefix = tag_prefix
        self.force_update = force_update
        self.project_version = project_version
        self.include_sha_in_release = include_sha_in_release
        self.current_sha = current_sha
        self.is_release = is_release

    def _do_vaulting(
        self,
        sha: str,
        origin_git: str,
        vault_fetch_url: str,
        vault_push_url: str,
        tag_name: str,
        repo_dir: Path,
    ):
        if self.current_sha:
            self.vcs.vault_release_tag(
                sha, vault_fetch_url, vault_push_url, tag_name, repo_dir
            )
        else:
            self.vcs.vault_reference(
                origin_git, sha, vault_push_url, tag_name, repo_dir
            )

    def process(self) -> PackageSource | None:
        origin_git = self.uvault_source.origin_url
        git_ref = self.uvault_source.get_git_reference()

        if not origin_git or not git_ref:
            print(
                f"Package {self.pkg} is missing 'git' or a valid reference ('rev', 'tag', 'branch') in [tool.uvault.sources]"
            )
            return None

        print(f"Syncing {self.pkg}...")

        if self.current_sha:
            sha = self.current_sha
            print(f"Using existing commit {sha} for release.")
        else:
            sha = self.vcs.get_remote_sha(origin_git, git_ref)
            if not sha:
                print(f"Failed to resolve {git_ref.value} in {origin_git}")
                return None

        tag_name = self.tag_prefix.rstrip("-+")
        if self.is_release and self.project_version:
            if tag_name:
                tag_name += f"-{self.project_version}"
            else:
                tag_name = self.project_version

            if self.include_sha_in_release:
                tag_name += f"+{sha}"
        else:
            if tag_name:
                tag_name += f"+{sha}"
            else:
                tag_name = sha

        repo_name = get_repo_name(origin_git)
        vault_fetch_url, vault_push_url = compute_vault_urls(
            repo_name, self.vault_config
        )

        if not self.force_update and self.vcs.remote_tag_exists(
            vault_push_url, tag_name
        ):
            print(
                f"Tag {tag_name} already exists in vault {vault_push_url}. Skipping vaulting."
            )
        else:
            print(f"Vaulting to {vault_push_url} with tag {tag_name}...")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            repo_dir = self.cache_dir / repo_name
            try:
                self._do_vaulting(
                    sha, origin_git, vault_fetch_url, vault_push_url, tag_name, repo_dir
                )
            except subprocess.CalledProcessError:
                from uvault.github import attempt_github_fork

                if attempt_github_fork(origin_git, self.vault_config):
                    # Retry the vaulting after successful fork
                    self._do_vaulting(
                        sha,
                        origin_git,
                        vault_fetch_url,
                        vault_push_url,
                        tag_name,
                        repo_dir,
                    )
                else:
                    raise

        new_source = PackageSource(self.pkg, {})
        new_source.update(git=vault_fetch_url, tag=tag_name)
        if self.uvault_source.subdirectory:
            new_source.update(subdirectory=self.uvault_source.subdirectory)

        return new_source


class SyncCommand:
    def __init__(
        self,
        packages: str | list[str] | None = None,
        update: bool = False,
        delete_extra: bool = False,
        keep_develop: bool = False,
        pyproject_path: str = "pyproject.toml",
        cache_dir: str = "~/.cache/uvault",
        release: bool = False,
    ):
        if isinstance(packages, str):
            self.packages = [packages]
        else:
            self.packages = packages or []
        self.update = update
        self.delete_extra = delete_extra
        self.keep_develop = keep_develop
        self.pyproject_path = Path(pyproject_path)
        self.cache_dir = Path(cache_dir).expanduser()
        self.release = release

    def _get_release_sha(
        self,
        pkg: str,
        uv_source: PackageSource,
        uvault_source: PackageSource,
        vault_config: dict,
        vcs: VcsProvider,
    ) -> str | None:
        tag_str = uv_source.tag
        if not tag_str:
            return None
        current_sha = None

        origin_git = uvault_source.origin_url
        if origin_git:
            repo_name = get_repo_name(origin_git)
            vault_fetch_url, _ = compute_vault_urls(repo_name, vault_config)
            current_sha = vcs.get_remote_sha(
                vault_fetch_url, GitReference(RefType.TAG, tag_str)
            )

        if current_sha:
            return current_sha

        # Fallback
        if "+" in tag_str:
            current_sha = tag_str.split("+")[-1]

        if current_sha:
            print(
                f"Note: Tag '{tag_str}' not found in vault for package {pkg}. "
                f"Falling back to extracted commit {current_sha} (assuming commit still exists)."
            )
        else:
            print(
                f"Warning: Could not extract SHA from tag '{tag_str}' for package {pkg}. "
                f"Falling back to latest commit from upstream source."
            )

        return current_sha

    def run(self):
        project = PyProject(self.pyproject_path)
        try:
            project.read()
        except FileNotFoundError:
            print("pyproject.toml not found")
            return 1

        if not project.tool_uvault:
            print("No [tool.uvault] section in pyproject.toml")
            return 1

        tag_prefix = project.tag_prefix
        vault_config = project.get_vault_config()
        if not vault_config:
            print("No [[tool.uvault.vcs_vaults]] configured.")
            return 1

        uvault_sources_dict = project.uvault_sources

        # Ensure uv_sources exists
        project.ensure_uv_sources()
        uv_sources_dict = project.uv_sources

        normalized_packages = {normalize_pkg_name(p) for p in self.packages}
        packages_to_sync = (
            normalized_packages if self.packages else list(uvault_sources_dict.keys())
        )

        has_changes = False

        for norm_pkg in packages_to_sync:
            if norm_pkg not in uvault_sources_dict:
                print(f"Package {norm_pkg} not found in [tool.uvault.sources]")
                continue

            uvault_source = uvault_sources_dict[norm_pkg]
            force_update = (
                self.update or self.release or norm_pkg in normalized_packages
            )

            is_develop = False
            uv_source = uv_sources_dict.get(norm_pkg)
            if uv_source:
                is_develop = uv_source.is_develop

            if is_develop:
                if self.keep_develop:
                    print(
                        f"Package {uvault_source.name} is in develop mode. Skipping (--keep-develop is set)."
                    )
                    continue
                else:
                    force_update = True
                    print(
                        f"Package {uvault_source.name} is in develop mode. Restoring to vaulted state."
                    )

            current_sha = None
            if not is_develop and self.release:
                if uv_source:
                    vcs_instance = uvault_source.get_vcs()
                    current_sha = self._get_release_sha(
                        uvault_source.name,
                        uv_source,
                        uvault_source,
                        vault_config,
                        vcs_instance,
                    )

            if norm_pkg in uv_sources_dict and not force_update:
                print(
                    f"Package {uvault_source.name} is already in [tool.uv.sources]. Skipping (use --update to force)."
                )
                continue

            syncer = PackageSyncer(
                pkg=uvault_source.name,
                uvault_source=uvault_source,
                cache_dir=self.cache_dir,
                vault_config=vault_config,
                tag_prefix=tag_prefix,
                force_update=force_update,
                project_version=project.project_version,
                include_sha_in_release=project.include_sha_in_release,
                current_sha=current_sha,
                is_release=self.release,
            )

            new_source = syncer.process()
            if new_source is not None:
                project.set_uv_source(uvault_source.name, new_source)
                uv_sources_dict[norm_pkg] = new_source
                has_changes = True

        if self.delete_extra:
            for norm_pkg in list(uv_sources_dict.keys()):
                if norm_pkg not in uvault_sources_dict:
                    project.delete_uv_source(norm_pkg)
                    print(
                        f"Removed extra package {uv_sources_dict[norm_pkg].name} from [tool.uv.sources]."
                    )
                    has_changes = True

        if has_changes:
            project.write()
            print("Updated pyproject.toml")
            print("Please run `uv sync` or `uv lock` to update your uv.lock file.")

        return 0
