import pytest
from unittest.mock import patch, MagicMock
from uvault.github import GitHubForge

try:
    import github  # type: ignore # noqa: F401

    HAS_GITHUB = True
except ImportError:
    HAS_GITHUB = False

requires_github = pytest.mark.skipif(not HAS_GITHUB, reason="pygithub not installed")


@pytest.fixture(autouse=True)
def reset_github_cache():
    GitHubForge._clients.clear()


@patch("uvault.github.read_user_config")
def test_github_forge_fork_no_token(mock_read_user_config):
    mock_read_user_config.return_value = {}
    # Simulate missing github to ensure it doesn't crash even if installed, or just let it run.
    # Actually, we want to test that if token is missing, it returns False.
    # But wait, fork() calls _get_client(allow_anonymous=False). Without token, it returns None.
    # So fork returns False immediately.
    forge = GitHubForge("https://github.com/foo/bar.git")
    assert not forge.fork("myorg")


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_github_forge_fork_success(mock_github_class, mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    mock_github = mock_github_class.return_value
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo
    mock_org = MagicMock()
    mock_github.get_organization.return_value = mock_org
    mock_fork = MagicMock()
    mock_fork.html_url = "https://github.com/myorg/bar"
    mock_org.create_fork.return_value = mock_fork

    with patch("time.sleep"):  # speed up
        forge = GitHubForge("https://github.com/foo/bar.git")
        assert forge.fork("myorg")
        mock_org.create_fork.assert_called_once_with(mock_repo)


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_github_forge_fork_ssh_url(mock_github_class, mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    mock_github = mock_github_class.return_value

    with patch("time.sleep"):
        forge = GitHubForge("git@github.com:foo/bar.git")
        assert forge.fork("myorg")
        mock_github.get_repo.assert_called_once_with("foo/bar")


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_github_forge_fork_ssh_scheme_url(mock_github_class, mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    mock_github = mock_github_class.return_value

    with patch("time.sleep"):
        forge = GitHubForge("ssh://git@github.com/foo/bar.git")
        assert forge.fork("myorg")
        mock_github.get_repo.assert_called_once_with("foo/bar")


@requires_github
@patch("uvault.github.read_user_config")
def test_github_forge_fork_invalid_path(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    forge = GitHubForge("https://github.com/invalidpath")
    assert not forge.fork("myorg")


@requires_github
@patch("uvault.github.read_user_config")
def test_github_forge_fork_empty_path(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    forge = GitHubForge("https://github.com/")
    assert not forge.fork("myorg")


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_github_forge_fork_github_exception(mock_github_class, mock_read_user_config):
    from github.GithubException import GithubException  # type: ignore

    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    mock_github = mock_github_class.return_value
    mock_github.get_repo.side_effect = GithubException(404, "Not Found", None)

    forge = GitHubForge("https://github.com/foo/bar.git")
    assert not forge.fork("myorg")


@patch("uvault.github.read_user_config")
def test_github_forge_fork_missing_pygithub(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    with patch.dict(
        "sys.modules", {"github": MagicMock(), "github.GithubException": None}
    ):
        forge = GitHubForge("https://github.com/foo/bar.git")
        assert not forge.fork("myorg")


def test_get_github_repo_path():
    assert GitHubForge._get_repo_path("https://github.com/org/repo") == "org/repo"
    assert GitHubForge._get_repo_path("https://github.com/org/repo.git") == "org/repo"
    assert GitHubForge._get_repo_path("git@github.com:org/repo.git") == "org/repo"
    assert GitHubForge._get_repo_path("ssh://git@github.com/org/repo.git") == "org/repo"
    assert GitHubForge._get_repo_path("https://github.com/org") is None


@requires_github
@patch("uvault.github.read_user_config")
@patch("builtins.print")
@patch("github.Github")
def test_get_github_client_no_token(
    mock_github_class, mock_print, mock_read_user_config
):
    mock_read_user_config.return_value = {}
    client = GitHubForge._get_client()
    assert client is not None
    mock_print.assert_called_once()
    mock_github_class.assert_called_once_with()


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
@patch("github.Auth.Token")
def test_get_github_client_success(
    mock_token_class, mock_github_class, mock_read_user_config
):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    client = GitHubForge._get_client()
    assert client is not None
    mock_token_class.assert_called_once_with("token123")
    mock_github_class.assert_called_once_with(auth=mock_token_class.return_value)


@patch("uvault.github.read_user_config")
def test_get_github_client_import_error(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    with patch.dict("sys.modules", {"github": None}):
        assert GitHubForge._get_client() is None


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
@patch("github.Auth.Token")
def test_get_github_client_cached(
    mock_token_class, mock_github_class, mock_read_user_config
):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    client1 = GitHubForge._get_client()
    client2 = GitHubForge._get_client()
    assert client1 is not None
    assert client1 is client2
    mock_github_class.assert_called_once()
