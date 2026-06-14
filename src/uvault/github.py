import time
from typing import TYPE_CHECKING
from uvault.forge import Forge
from uvault.project import read_user_config
from uvault.vcs import RefType
from urllib.parse import urlparse

if TYPE_CHECKING:
    from uvault.status import PackageStatus


class GitHubForge(Forge):
    _clients = {}

    @classmethod
    def _get_client(cls, allow_anonymous: bool = True):
        if allow_anonymous in cls._clients:
            return cls._clients[allow_anonymous]

        user_config = read_user_config()
        token = user_config.get("github", {}).get("token")
        try:
            from github import Github, Auth

            if token:
                auth = Auth.Token(token)
                client = Github(auth=auth)
                cls._clients[allow_anonymous] = client
                return client
            elif allow_anonymous:
                print(
                    "WARNING: No GitHub token configured in ~/.config/uvault/config.toml.\n"
                    "Using unauthenticated access. You may hit rate limits."
                )
                client = Github()
                cls._clients[allow_anonymous] = client
                return client
            else:
                return None
        except ImportError:
            return None

    @staticmethod
    def _get_repo_path(origin_git: str) -> str | None:
        if origin_git.startswith("git@"):
            path = origin_git.split(":")[-1]
        elif origin_git.startswith("ssh://"):
            parsed = urlparse(origin_git)
            path = parsed.path.lstrip("/")
        else:
            parsed = urlparse(origin_git)
            path = parsed.path.lstrip("/")

        if path.endswith(".git"):
            path = path[:-4]

        if not path or "/" not in path:
            return None

        return path

    def __init__(self, origin_url: str):
        super().__init__(origin_url)
        self.path = self._get_repo_path(origin_url)

    def fork(self, target_org: str) -> bool:
        g = self._get_client(allow_anonymous=False)
        if not g:
            return False

        try:
            from github.GithubException import GithubException
        except ImportError:
            return False

        if not self.path:
            return False

        try:
            repo_original = g.get_repo(self.path)
            orga = g.get_organization(target_org)

            print(
                f"Requesting fork of '{self.path}' into organization '{target_org}'..."
            )
            mon_fork_orga = orga.create_fork(repo_original)
            print(f"Fork created successfully in org '{target_org}'!")
            print(f"URL: {mon_fork_orga.html_url}")

            # Wait a moment for GitHub to make the fork available for git operations
            time.sleep(2)

            return True
        except GithubException as e:
            print(f"Failed to fork GitHub repository: {e}")
            return False

    def enrich_package_status(
        self, pkg_status: "PackageStatus", ignore_labels: list[str]
    ) -> str | None:
        from uvault.status import PullRequestStatus

        g = self._get_client()
        if not g or not self.path:
            return None

        try:
            repo = g.get_repo(self.path)
        except Exception:
            return None

        remote_sha = None

        if pkg_status.ref_type == RefType.PR:
            try:
                pr_num = int(pkg_status.ref_value)
                pr = repo.get_pull(pr_num)

                if pr.merged:
                    pkg_status.status = PullRequestStatus.MERGED
                elif pr.state == "closed":
                    pkg_status.status = PullRequestStatus.CLOSED
                else:
                    pkg_status.status = PullRequestStatus.OPEN

                pkg_status.labels = [
                    label.name
                    for label in pr.labels
                    if not any(
                        label.name.startswith(prefix) for prefix in ignore_labels
                    )
                ]
                pkg_status.last_activity = pr.updated_at
                remote_sha = pr.head.sha
            except Exception:
                pass

        elif pkg_status.ref_type == RefType.BRANCH:
            try:
                branch = repo.get_branch(pkg_status.ref_value)
                pkg_status.status = PullRequestStatus.ACTIVE
                commit = branch.commit.commit
                pkg_status.last_activity = commit.author.date
                remote_sha = branch.commit.sha
            except Exception:
                pkg_status.status = PullRequestStatus.UNKNOWN

        return remote_sha

    def get_remote_sha(self, ref_type: str, ref_value: str) -> str | None:
        g = self._get_client()
        if not g or not self.path:
            return None

        try:
            repo = g.get_repo(self.path)
            if ref_type == RefType.TAG:
                gh_ref = repo.get_git_ref(f"tags/{ref_value}")
                return gh_ref.object.sha
            elif ref_type == RefType.BRANCH:
                gh_branch = repo.get_branch(ref_value)
                return gh_branch.commit.sha
        except Exception:
            pass
        return None

    def get_divergence(self, base_sha: str, head_sha: str) -> tuple[int, bool] | None:
        g = self._get_client()
        if not g or not self.path:
            return None

        try:
            repo = g.get_repo(self.path)
            comp = repo.compare(base_sha, head_sha)
            behind = comp.ahead_by
            diverged = comp.status == "diverged" or comp.behind_by > 0
            return behind, diverged
        except Exception:
            return None
