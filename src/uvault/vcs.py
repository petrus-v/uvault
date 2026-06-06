import abc
import subprocess
import re
from pathlib import Path


class VcsProvider(abc.ABC):
    @abc.abstractmethod
    def get_remote_sha(self, origin_url: str, rev: str) -> str | None:
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
    def get_remote_sha(self, origin_url: str, rev: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "ls-remote", origin_url, rev],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.strip()
            if output:
                return output.split()[0]
        except subprocess.CalledProcessError:
            pass

        if re.match(r"^[0-9a-f]{40}$", rev):
            return rev
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
        else:
            subprocess.run(["git", "-C", str(repo_dir), "fetch", "origin"], check=True)

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
