from pathlib import Path
import tomlkit
from uvault.vcs import (
    GitVcs,
    VcsProvider,
    GitReference,
    get_repo_name,
    compute_vault_urls,
)


class PackageSyncer:
    def __init__(
        self,
        pkg: str,
        source_cfg: dict,
        vcs: VcsProvider,
        cache_dir: Path,
        vault_config: dict,
        tag_prefix: str,
        force_update: bool,
        project_version: str | None = None,
        include_project_version: bool = True,
    ):
        self.pkg = pkg
        self.source_cfg = source_cfg
        self.vcs = vcs
        self.cache_dir = cache_dir
        self.vault_config = vault_config
        self.tag_prefix = tag_prefix
        self.force_update = force_update
        self.project_version = project_version
        self.include_project_version = include_project_version

    def process(self) -> dict | None:
        origin_git = self.source_cfg.get("git")
        git_ref = GitReference.from_config(self.source_cfg)

        if not origin_git or not git_ref:
            print(
                f"Package {self.pkg} is missing 'git' or a valid reference ('rev', 'tag', 'branch') in [tool.uvault.sources]"
            )
            return None

        print(f"Syncing {self.pkg}...")

        sha = self.vcs.get_remote_sha(origin_git, git_ref)
        if not sha:
            print(f"Failed to resolve {git_ref.value} in {origin_git}")
            return None

        tag_name = self.tag_prefix
        if self.include_project_version and self.project_version:
            tag_name += f"{self.project_version}+"
        tag_name += sha
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
        packages=None,
        update=False,
        delete_extra=False,
        pyproject_path="pyproject.toml",
        cache_dir="~/.cache/uvault/repos",
        vcs=None,
    ):
        self.packages = packages or []
        self.update = update
        self.delete_extra = delete_extra
        self.pyproject_path = Path(pyproject_path)
        self.cache_dir = Path(cache_dir).expanduser()
        self.vcs = vcs or GitVcs()

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
        include_project_version = tool_uvault.get("include_project_version", True)

        sources = tool_uvault.get("sources", {})

        if "uv" not in doc["tool"]:
            uv_table = tomlkit.table()
            uv_table.add("sources", tomlkit.table())
            tool_table = doc["tool"]
            tool_table.add("uv", uv_table)

            body = getattr(tool_table.value, "_body", [])
            uv_idx = -1
            uvault_idx = -1
            for i, (k, v) in enumerate(body):
                if k and getattr(k, "key", None) == "uv":
                    uv_idx = i
                if k and getattr(k, "key", None) == "uvault":
                    uvault_idx = i

            if uvault_idx != -1 and uv_idx != -1 and uv_idx > uvault_idx:
                item = body.pop(uv_idx)
                body.insert(uvault_idx + 1, item)

        if "sources" not in doc["tool"]["uv"]:
            doc["tool"]["uv"].add("sources", tomlkit.table())

        uv_sources = doc["tool"]["uv"]["sources"]

        packages_to_sync = self.packages if self.packages else list(sources.keys())

        has_changes = False

        for pkg in packages_to_sync:
            if pkg not in sources:
                print(f"Package {pkg} not found in [tool.uvault.sources]")
                continue

            force_update = self.update or (self.packages and pkg in self.packages)

            if pkg in uv_sources and not force_update:
                print(
                    f"Package {pkg} is already in [tool.uv.sources]. Skipping (use --update to force)."
                )
                continue

            syncer = PackageSyncer(
                pkg=pkg,
                source_cfg=sources[pkg],
                vcs=self.vcs,
                cache_dir=self.cache_dir,
                vault_config=vault_config,
                tag_prefix=tag_prefix,
                force_update=force_update,
                project_version=project_version,
                include_project_version=include_project_version,
            )

            new_source = syncer.process()
            if new_source is not None:
                uv_sources[pkg] = new_source
                has_changes = True

        if self.delete_extra:
            for pkg in list(uv_sources.keys()):
                if pkg not in sources:
                    del uv_sources[pkg]
                    print(f"Removed extra package {pkg} from [tool.uv.sources].")
                    has_changes = True

        if has_changes:
            with open(self.pyproject_path, "w", encoding="utf-8") as f:
                f.write(tomlkit.dumps(doc))
            print("Updated pyproject.toml")
            print("Please run `uv sync` or `uv lock` to update your uv.lock file.")

        return 0
