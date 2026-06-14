from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from uvault.status import PackageStatus


class Forge(ABC):
    def __init__(self, origin_url: str):
        self.origin_url = origin_url

    @abstractmethod
    def fork(self, target_org: str) -> bool: ...

    @abstractmethod
    def enrich_package_status(
        self, pkg_status: "PackageStatus", ignore_labels: list[str]
    ) -> str | None:
        """Fetch metadata from forge and update pkg_status. Returns the remote SHA."""
        ...

    @abstractmethod
    def get_remote_sha(self, ref_type: str, ref_value: str) -> str | None:
        """Get the commit SHA for a specific reference."""
        ...

    @abstractmethod
    def get_divergence(self, base_sha: str, head_sha: str) -> tuple[int, bool] | None:
        """Returns (behind, diverged) tuple if successful, else None."""
        ...


def create_forge(origin_url: str | None) -> Forge | None:
    if not origin_url:
        return None

    urlparse(origin_url)
    if "github.com" in origin_url:
        from uvault.github import GitHubForge

        return GitHubForge(origin_url)

    # Future: GitLabForge, etc.
    return None
