import abc
import subprocess
import re
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urlparse
from importlib.metadata import metadata, PackageNotFoundError


def guess_repository_url(package_name: str) -> str | None:
    try:
        meta = metadata(package_name)
    except PackageNotFoundError:
        return None

    urls = []
    homepage = meta.get("Home-page")
    if homepage:
        urls.append(("Home-page", homepage))

    project_urls = meta.get_all("Project-URL") or []
    for purl in project_urls:
        if "," in purl:
            name, url = purl.split(",", 1)
            urls.append((name.strip(), url.strip()))

    best_score = -1
    best_url = None

    for name, url in urls:
        score = 0
        name_lower = name.lower()
        if "source" in name_lower or "repository" in name_lower:
            score += 20
        elif "home" in name_lower:
            score += 10

        url_lower = url.lower()
        if "github.com" in url_lower:
            score += 5
        elif "gitlab.com" in url_lower:
            score += 5
        elif "git" in url_lower:
            score += 2

        if score > best_score:
            best_score = score
            best_url = url

    return best_url


def get_repo_name(git_url: str) -> str:
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


def compute_vault_urls(repo_name: str, vault_config: dict) -> tuple[str, str]:
    provider = vault_config.get("provider", "github.com")
    owner = vault_config.get("owner", "")
    fetch_ssh = vault_config.get("fetch_ssh", False)
    push_ssh = vault_config.get("push_ssh", True)

    path = f"{owner}/{repo_name}.git" if owner else f"{repo_name}.git"

    fetch_url = (
        f"ssh://git@{provider}/{path}" if fetch_ssh else f"https://{provider}/{path}"
    )
    push_url = (
        f"ssh://git@{provider}/{path}" if push_ssh else f"https://{provider}/{path}"
    )

    return fetch_url, push_url


@dataclass
class GitReference:
    ref_type: str
    value: str

    @classmethod
    def from_config(cls, source_cfg: dict) -> "GitReference | None":
        for key in ["rev", "tag", "branch"]:
            if key in source_cfg:
                return cls(key, source_cfg[key])
        return None

    def get_ls_remote_args(self) -> list[str]:
        if self.ref_type == "tag":
            return ["--tags", self.value]
        elif self.ref_type == "branch":
            return ["--heads", self.value]
        else:
            return [self.value]


class VcsProvider(abc.ABC):
    @abc.abstractmethod
    def get_remote_sha(self, origin_url: str, ref: GitReference) -> str | None:
        pass  # pragma: no cover

    @abc.abstractmethod
    def remote_tag_exists(self, vault_url: str, tag_name: str) -> bool:
        pass  # pragma: no cover

    @abc.abstractmethod
    def vault_reference(
        self, origin_url: str, sha: str, vault_url: str, tag_name: str, repo_dir: Path
    ) -> None:
        pass  # pragma: no cover

    @abc.abstractmethod
    def check_clean_state(self, repo_dir: Path) -> bool:
        pass  # pragma: no cover

    @abc.abstractmethod
    def fetch_remote(
        self, repo_dir: Path, remote: str = "origin", ref: str | None = None
    ) -> None:
        pass  # pragma: no cover

    @abc.abstractmethod
    def checkout(self, repo_dir: Path, ref: str, create_branch: bool = False) -> None:
        pass  # pragma: no cover

    @abc.abstractmethod
    def clone(self, url: str, dest: Path) -> None:
        pass  # pragma: no cover

    @abc.abstractmethod
    def set_remote(self, repo_dir: Path, name: str, url: str) -> None:
        pass  # pragma: no cover


class GitVcs(VcsProvider):
    def get_remote_sha(self, origin_url: str, ref: GitReference) -> str | None:
        args = ["git", "ls-remote", origin_url] + ref.get_ls_remote_args()
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.strip()
            if output:
                return output.split()[0]
        except subprocess.CalledProcessError:
            pass

        if ref.ref_type == "rev" and re.match(r"^[0-9a-f]{40}$", ref.value):
            return ref.value
        return None

    def remote_tag_exists(self, vault_url: str, tag_name: str) -> bool:
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--tags", vault_url, tag_name],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.strip()
            if output:
                return True
        except subprocess.CalledProcessError:
            pass
        return False

    def vault_reference(
        self, origin_url: str, sha: str, vault_url: str, tag_name: str, repo_dir: Path
    ) -> None:
        if not repo_dir.exists():
            subprocess.run(
                ["git", "clone", "--bare", origin_url, str(repo_dir)], check=True
            )
        print(f"fetching {sha} in {repo_dir}")
        subprocess.run(["git", "-C", str(repo_dir), "fetch", "origin", sha], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "push",
                vault_url,
                f"{sha}:refs/tags/{tag_name}",
            ],
            check=True,
        )

    def check_clean_state(self, repo_dir: Path) -> bool:
        res = subprocess.run(
            ["git", "-C", str(repo_dir), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        return not bool(res.stdout.strip())

    def fetch_remote(
        self, repo_dir: Path, remote: str = "origin", ref: str | None = None
    ) -> None:
        args = ["git", "-C", str(repo_dir), "fetch", remote]
        if ref:
            args.append(ref)
        subprocess.run(args, check=True)

    def checkout(self, repo_dir: Path, ref: str, create_branch: bool = False) -> None:
        args = ["git", "-C", str(repo_dir), "checkout"]
        if create_branch:
            args.append("-b")
        args.append(ref)
        subprocess.run(args, check=True)

    def clone(self, url: str, dest: Path) -> None:
        subprocess.run(["git", "clone", url, str(dest)], check=True)

    def set_remote(self, repo_dir: Path, name: str, url: str) -> None:
        subprocess.run(
            ["git", "-C", str(repo_dir), "remote", "add", name, url],
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "remote", "set-url", name, url],
            check=False,
            capture_output=True,
        )
