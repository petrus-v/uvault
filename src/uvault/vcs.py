import abc
import subprocess
import re
from pathlib import Path
from dataclasses import dataclass


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
