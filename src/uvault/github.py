import os
import time
from typing import TYPE_CHECKING
from uvault.forge import Forge
from uvault.project import read_user_config
from uvault.vcs import RefType
from urllib.parse import urlparse

if TYPE_CHECKING:
    from uvault.status import PackageStatus


#: Environment variables consulted for a token, in order, when the user
#: config does not define one. These are the names the GitHub CLI and
#: GitHub Actions already set, so CI and a shell with `gh` logged in work
#: without writing a token to disk.
_TOKEN_ENV_VARS = ("GH_TOKEN", "GITHUB_TOKEN")


def _token_from_env() -> str | None:
    for name in _TOKEN_ENV_VARS:
        value = os.environ.get(name)
        if value:
            return value
    return None


class GitHubForge(Forge):
    _clients = {}

    @classmethod
    def _get_client(cls, allow_anonymous: bool = True):
        if allow_anonymous in cls._clients:
            return cls._clients[allow_anonymous]

        user_config = read_user_config()
        token = user_config.get("github", {}).get("token") or _token_from_env()
        try:
            from github import Github, Auth  # type: ignore

            if token:
                auth = Auth.Token(token)
                client = Github(auth=auth)
                cls._clients[allow_anonymous] = client
                return client
            elif allow_anonymous:
                print(
                    "WARNING: No GitHub token found in "
                    "~/.config/uvault/config.toml or "
                    f"{' / '.join(_TOKEN_ENV_VARS)}.\n"
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
            from github.GithubException import GithubException  # type: ignore
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

            # Protect the tags on the repository we just created. Advisory:
            # a token that cannot create rulesets must still be able to fork,
            # so this never changes the outcome of the fork itself.
            self.ensure_tag_ruleset(mon_fork_orga.full_name)

            return True
        except GithubException as e:
            print(f"Failed to fork GitHub repository: {e}")
            return False

    #: Name of the ruleset uvault manages. Stable, so re-running is idempotent.
    TAG_RULESET_NAME = "uvault-tags-immutable"

    def ensure_tag_ruleset(self, repo_path: str) -> bool:
        """Make the tags in ``repo_path`` immutable. Idempotent.

        A vault tag is only a promise until something stops it being deleted
        or moved; a plain tag can be force-pushed or removed by anyone with
        push access, which is the very failure mode vaulting exists to avoid.

        Deliberately takes a repository path rather than deriving one, so the
        same primitive serves a per-upstream fork and a single shared vault
        repository. Call it after creating a fork, or after pushing a tag.

        Returns True when the ruleset is present afterwards, False when it
        could not be created. **Never raises**: creating a ruleset needs
        ``Administration: write``, which is strictly more than forking and
        pushing, so a token that cannot do it must still be able to vault.
        """
        g = self._get_client(allow_anonymous=False)
        if not g:
            return False

        try:
            from github.GithubException import GithubException  # type: ignore
        except ImportError:
            return False

        base = f"/repos/{repo_path}/rulesets"
        payload = {
            "name": self.TAG_RULESET_NAME,
            "target": "tag",
            "enforcement": "active",
            "conditions": {"ref_name": {"include": ["~ALL"], "exclude": []}},
            # `update` as well as `non_fast_forward`: the latter alone still
            # permits force-pushing an existing tag, so both are needed for a
            # tag to actually be immutable.
            #
            # `creation` is deliberately absent. It is the obvious fourth rule
            # and it would break every later sync, because the vault has to
            # keep accepting new tags. Blocking `update` costs nothing by
            # comparison: uvault pushes `<sha>:refs/tags/<tag>` with no `+`
            # and no `--force`, so it never moves a tag that already exists.
            "rules": [
                {"type": "deletion"},
                {"type": "non_fast_forward"},
                {"type": "update"},
            ],
        }

        try:
            _, existing = g.requester.requestJsonAndCheck("GET", base)
            for ruleset in existing or []:
                if (
                    ruleset.get("name") == self.TAG_RULESET_NAME
                    and ruleset.get("target") == "tag"
                ):
                    return True
            g.requester.requestJsonAndCheck("POST", base, input=payload)
        except GithubException as e:
            status = getattr(e, "status", None)
            if status == 403:
                print(
                    f"WARNING: not allowed to protect tags on '{repo_path}' "
                    "(creating a ruleset needs Administration: write). "
                    "Tags are vaulted but deletable."
                )
            elif status == 404:
                print(
                    f"WARNING: cannot protect tags on '{repo_path}': rulesets "
                    "are unavailable here. On GitHub Free they require a "
                    "public repository."
                )
            else:
                print(f"WARNING: could not protect tags on '{repo_path}': {e}")
            return False
        except Exception as e:  # noqa: BLE001 - advisory, must not break vaulting
            print(f"WARNING: could not protect tags on '{repo_path}': {e}")
            return False

        print(
            f"Tags on '{repo_path}' are now protected against deletion and force-push."
        )
        return True

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
