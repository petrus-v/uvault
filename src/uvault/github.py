import time
from urllib.parse import urlparse
from uvault.project import read_user_config


def get_github_client(allow_anonymous: bool = True):
    user_config = read_user_config()
    token = user_config.get("github", {}).get("token")
    try:
        from github import Github, Auth

        if token:
            auth = Auth.Token(token)
            return Github(auth=auth)
        elif allow_anonymous:
            print(
                "WARNING: No GitHub token configured in ~/.config/uvault/config.toml.\n"
                "Using unauthenticated access. You may hit rate limits."
            )
            return Github()
        else:
            return None
    except ImportError:
        return None


def get_github_repo_path(origin_git: str) -> str | None:
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


def attempt_github_fork(origin_git: str, vault_config: dict) -> bool:
    """
    Attempts to fork a GitHub repository into the vault organization.
    Returns True if successful, False otherwise.
    """
    provider = vault_config.get("provider", "github.com")
    if provider != "github.com":
        return False

    g = get_github_client(allow_anonymous=False)
    if not g:
        return False

    try:
        from github.GithubException import GithubException
    except ImportError:
        return False

    path = get_github_repo_path(origin_git)
    if not path:
        return False

    target_org_name = vault_config.get("owner")
    if not target_org_name:
        return False

    try:
        repo_original = g.get_repo(path)
        orga = g.get_organization(target_org_name)

        print(f"Requesting fork of '{path}' into organization '{target_org_name}'...")
        mon_fork_orga = orga.create_fork(repo_original)
        print(f"Fork created successfully in org '{target_org_name}'!")
        print(f"URL: {mon_fork_orga.html_url}")

        # Wait a moment for GitHub to make the fork available for git operations
        time.sleep(2)

        return True
    except GithubException as e:
        print(f"Failed to fork GitHub repository: {e}")
        return False
