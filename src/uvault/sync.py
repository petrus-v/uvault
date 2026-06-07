from pathlib import Path
from urllib.parse import urlparse
import tomlkit
from uvault.vcs import GitVcs, VcsProvider


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
        origin_rev = self.source_cfg.get("rev")

        if not origin_git or not origin_rev:
            print(
                f"Package {self.pkg} is missing 'git' or 'rev' in [tool.uvault.sources]"
            )
            return None

        print(f"Syncing {self.pkg}...")

        sha = self.vcs.get_remote_sha(origin_git, origin_rev)
        if not sha:
            print(f"Failed to resolve {origin_rev} in {origin_git}")
            return None

        tag_name = self.tag_prefix
        if self.include_project_version and self.project_version:
            tag_name += f"{self.project_version}+"
        tag_name += sha
        repo_name = self._get_repo_name(origin_git)
        vault_url = self._compute_vault_url(repo_name)

        if not self.force_update and self.vcs.remote_tag_exists(vault_url, tag_name):
            print(
                f"Tag {tag_name} already exists in vault {vault_url}. Skipping vaulting."
            )
        else:
            print(f"Vaulting to {vault_url} with tag {tag_name}...")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            repo_dir = self.cache_dir / repo_name
            self.vcs.vault_reference(origin_git, sha, vault_url, tag_name, repo_dir)

        new_source = tomlkit.inline_table()
        new_source["git"] = vault_url
        new_source["tag"] = tag_name
        if "subdirectory" in self.source_cfg:
            new_source["subdirectory"] = self.source_cfg["subdirectory"]

        return new_source

    def _get_repo_name(self, git_url: str) -> str:
        if git_url.startswith("git@"):
            path = git_url.split(":")[-1]
        elif git_url.startswith("ssh://"):
            parsed = urlparse(git_url)
            path = parsed.path
        else:
            parsed = urlparse(git_url)
            path = parsed.path

        repo_name = path.split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        return repo_name

    def _compute_vault_url(self, repo_name: str) -> str:
        provider = self.vault_config.get("provider", "github.com")
        owner = self.vault_config.get("owner", "")
        ssh_only = self.vault_config.get("ssh_only", False)

        path = f"{owner}/{repo_name}.git" if owner else f"{repo_name}.git"

        if ssh_only:
            return f"ssh://git@{provider}/{path}"
        else:
            return f"https://{provider}/{path}"


class SyncCommand:
    def __init__(
        self,
        packages=None,
        update=False,
        pyproject_path="pyproject.toml",
        cache_dir="~/.cache/uvault/repos",
        vcs=None,
    ):
        self.packages = packages or []
        self.update = update
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
            doc["tool"].add("uv", tomlkit.table())
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

        if has_changes:
            with open(self.pyproject_path, "w", encoding="utf-8") as f:
                f.write(tomlkit.dumps(doc))
            print("Updated pyproject.toml")

        return 0
