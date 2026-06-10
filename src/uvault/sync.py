from pathlib import Path
import tomlkit
import re
from uvault.vcs import (
    VcsProvider,
    GitReference,
    get_repo_name,
    compute_vault_urls,
    get_vcs,
)


def normalize_pkg_name(name: str) -> str:
    """Normalize a Python package name for comparison."""
    return re.sub(r"[-_.]+", "-", name).lower()


class PackageSyncer:
    def __init__(
        self,
        pkg: str,
        source_cfg: dict,
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
        self.source_cfg = source_cfg
        self.vcs = get_vcs(source_cfg)
        self.cache_dir = cache_dir
        self.vault_config = vault_config
        self.tag_prefix = tag_prefix
        self.force_update = force_update
        self.project_version = project_version
        self.include_sha_in_release = include_sha_in_release
        self.current_sha = current_sha
        self.is_release = is_release

    def process(self) -> dict | None:
        origin_git = self.source_cfg.get("git")
        git_ref = GitReference.from_config(self.source_cfg)

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
            if self.current_sha:
                self.vcs.vault_release_tag(
                    sha, vault_fetch_url, vault_push_url, tag_name, repo_dir
                )
            else:
                self.vcs.vault_reference(
                    origin_git, sha, vault_push_url, tag_name, repo_dir
                )

        new_source = tomlkit.inline_table()
        new_source["git"] = vault_fetch_url
        new_source["tag"] = tag_name
        if "subdirectory" in self.source_cfg:
            new_source["subdirectory"] = self.source_cfg["subdirectory"]

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
        uv_pkg_cfg: dict,
        sources: dict,
        actual_source_key: str,
        vault_config: dict,
        vcs: VcsProvider,
    ) -> str | None:
        if not isinstance(uv_pkg_cfg, dict) or "tag" not in uv_pkg_cfg:
            return None

        tag_str = uv_pkg_cfg["tag"]
        current_sha = None

        origin_git = sources[actual_source_key].get("git")
        if origin_git:
            repo_name = get_repo_name(origin_git)
            vault_fetch_url, _ = compute_vault_urls(repo_name, vault_config)
            current_sha = vcs.get_remote_sha(
                vault_fetch_url, GitReference("tag", tag_str)
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
        if not self.pyproject_path.exists():
            print("pyproject.toml not found")
            return 1

        with open(self.pyproject_path, "r", encoding="utf-8") as f:
            doc = tomlkit.parse(f.read())

        tool_uvault = doc.get("tool", {}).get("uvault", {})
        if not tool_uvault:
            print("No [tool.uvault] section in pyproject.toml")
            return 1

        tag_prefix = tool_uvault.get("tag_prefix", "")
        vaults = tool_uvault.get("vcs_vaults", [])
        if not vaults:
            print("No [[tool.uvault.vcs_vaults]] configured.")
            return 1

        vault_config = next((v for v in vaults if v.get("default")), vaults[0])

        project_version = doc.get("project", {}).get("version")
        include_sha_in_release = tool_uvault.get("include_sha_in_release", True)

        sources = tool_uvault.get("sources", {})

        if "uv" not in doc["tool"]:
            doc["tool"].add("uv", tomlkit.table())

        if "sources" not in doc["tool"]["uv"]:
            doc["tool"]["uv"].add("sources", tomlkit.table())

        uv_sources = doc["tool"]["uv"]["sources"]

        packages_to_sync = self.packages if self.packages else list(sources.keys())

        has_changes = False

        normalized_sources = {normalize_pkg_name(k): k for k in sources.keys()}
        normalized_uv_sources = {normalize_pkg_name(k): k for k in uv_sources.keys()}
        normalized_packages = {normalize_pkg_name(p) for p in self.packages}

        for pkg in packages_to_sync:
            norm_pkg = normalize_pkg_name(pkg)
            if norm_pkg not in normalized_sources:
                print(f"Package {pkg} not found in [tool.uvault.sources]")
                continue

            actual_source_key = normalized_sources[norm_pkg]
            force_update = (
                self.update or self.release or norm_pkg in normalized_packages
            )

            is_develop = False
            if norm_pkg in normalized_uv_sources:
                uv_pkg_key = normalized_uv_sources[norm_pkg]
                uv_pkg_cfg = uv_sources.get(uv_pkg_key)
                if isinstance(uv_pkg_cfg, dict):
                    is_develop = (
                        uv_pkg_cfg.get("editable") is True or "path" in uv_pkg_cfg
                    )

            if is_develop:
                if self.keep_develop:
                    print(
                        f"Package {pkg} is in develop mode. Skipping (--keep-develop is set)."
                    )
                    continue
                else:
                    force_update = True
                    print(
                        f"Package {pkg} is in develop mode. Restoring to vaulted state."
                    )

            current_sha = None
            if not is_develop and self.release:
                uv_pkg_key = normalized_uv_sources.get(norm_pkg)
                if uv_pkg_key:
                    uv_pkg_cfg = uv_sources.get(uv_pkg_key)
                    vcs_instance = get_vcs(sources[actual_source_key])
                    current_sha = self._get_release_sha(
                        pkg,
                        uv_pkg_cfg,
                        sources,
                        actual_source_key,
                        vault_config,
                        vcs_instance,
                    )

            if norm_pkg in normalized_uv_sources and not force_update:
                print(
                    f"Package {pkg} is already in [tool.uv.sources]. Skipping (use --update to force)."
                )
                continue

            syncer = PackageSyncer(
                pkg=actual_source_key,
                source_cfg=sources[actual_source_key],
                cache_dir=self.cache_dir,
                vault_config=vault_config,
                tag_prefix=tag_prefix,
                force_update=force_update,
                project_version=project_version,
                include_sha_in_release=include_sha_in_release,
                current_sha=current_sha,
                is_release=self.release,
            )

            new_source = syncer.process()
            if new_source is not None:
                # Remove the old unnormalized key from uv_sources if it exists
                if (
                    norm_pkg in normalized_uv_sources
                    and normalized_uv_sources[norm_pkg] != actual_source_key
                ):
                    del uv_sources[normalized_uv_sources[norm_pkg]]

                uv_sources[actual_source_key] = new_source
                normalized_uv_sources[norm_pkg] = actual_source_key
                has_changes = True

        if self.delete_extra:
            for uv_pkg in list(uv_sources.keys()):
                if normalize_pkg_name(uv_pkg) not in normalized_sources:
                    del uv_sources[uv_pkg]
                    print(f"Removed extra package {uv_pkg} from [tool.uv.sources].")
                    has_changes = True

        if has_changes:
            with open(self.pyproject_path, "w", encoding="utf-8") as f:
                f.write(tomlkit.dumps(doc))
            print("Updated pyproject.toml")
            print("Please run `uv sync` or `uv lock` to update your uv.lock file.")

        return 0
