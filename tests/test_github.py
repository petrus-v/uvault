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


@requires_github
@patch("uvault.github.read_user_config", return_value={})
@patch("github.Github")
def test_token_read_from_gh_token_env(
    mock_github_class, mock_read_user_config, monkeypatch
):
    """CI and a `gh`-logged-in shell already export this; no file needed."""
    monkeypatch.setenv("GH_TOKEN", "env-token")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    GitHubForge._get_client()

    from github import Auth  # type: ignore

    assert mock_github_class.call_args is not None
    auth = mock_github_class.call_args.kwargs.get("auth")
    assert isinstance(auth, Auth.Token)
    assert auth.token == "env-token"


@requires_github
@patch("uvault.github.read_user_config", return_value={})
@patch("github.Github")
def test_github_token_env_is_a_fallback(
    mock_github_class, mock_read_user_config, monkeypatch
):
    """GITHUB_TOKEN is what Actions injects by default."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "actions-token")

    GitHubForge._get_client()

    auth = mock_github_class.call_args.kwargs.get("auth")
    assert auth.token == "actions-token"


@requires_github
@patch(
    "uvault.github.read_user_config",
    return_value={"github": {"token": "file-token"}},
)
@patch("github.Github")
def test_user_config_token_wins_over_env(
    mock_github_class, mock_read_user_config, monkeypatch
):
    """An explicit config entry must not be silently overridden by the shell."""
    monkeypatch.setenv("GH_TOKEN", "env-token")

    GitHubForge._get_client()

    auth = mock_github_class.call_args.kwargs.get("auth")
    assert auth.token == "file-token"


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_ensure_tag_ruleset_creates_it(mock_github_class, mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "t"}}
    g = mock_github_class.return_value
    g.requester.requestJsonAndCheck.return_value = ({}, [])

    forge = GitHubForge("https://github.com/foo/bar.git")
    assert forge.ensure_tag_ruleset("myorg/bar") is True

    post = [
        c
        for c in g.requester.requestJsonAndCheck.call_args_list
        if c.args and c.args[0] == "POST"
    ]
    assert len(post) == 1
    payload = post[0].kwargs["input"]
    assert payload["target"] == "tag"
    assert payload["enforcement"] == "active"
    types = {r["type"] for r in payload["rules"]}
    # `creation` must never be blocked: the vault has to keep accepting tags.
    assert types == {"deletion", "non_fast_forward"}


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_ensure_tag_ruleset_is_idempotent(mock_github_class, mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "t"}}
    g = mock_github_class.return_value
    g.requester.requestJsonAndCheck.return_value = (
        {},
        [{"name": GitHubForge.TAG_RULESET_NAME, "target": "tag"}],
    )

    forge = GitHubForge("https://github.com/foo/bar.git")
    assert forge.ensure_tag_ruleset("myorg/bar") is True
    # Already present: must not POST again.
    assert not [
        c
        for c in g.requester.requestJsonAndCheck.call_args_list
        if c.args and c.args[0] == "POST"
    ]


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_ensure_tag_ruleset_fails_soft_without_admin(
    mock_github_class, mock_read_user_config, capsys
):
    """A token that cannot create rulesets must still be able to vault."""
    mock_read_user_config.return_value = {"github": {"token": "t"}}
    from github.GithubException import GithubException  # type: ignore

    g = mock_github_class.return_value

    def side_effect(method, url, **kw):
        if method == "GET":
            return ({}, [])
        raise GithubException(403, {"message": "Resource not accessible"}, None)

    g.requester.requestJsonAndCheck.side_effect = side_effect

    forge = GitHubForge("https://github.com/foo/bar.git")
    # Does not raise, and says why.
    assert forge.ensure_tag_ruleset("myorg/bar") is False
    assert "Administration: write" in capsys.readouterr().out


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_fork_protects_tags_but_is_not_gated_on_it(
    mock_github_class, mock_read_user_config
):
    """Forking must succeed even when the tags cannot be protected."""
    mock_read_user_config.return_value = {"github": {"token": "t"}}
    from github.GithubException import GithubException  # type: ignore

    g = mock_github_class.return_value
    g.get_organization.return_value.create_fork.return_value = MagicMock(
        full_name="myorg/bar", html_url="https://github.com/myorg/bar"
    )
    g.requester.requestJsonAndCheck.side_effect = GithubException(
        403, {"message": "nope"}, None
    )

    forge = GitHubForge("https://github.com/foo/bar.git")
    assert forge.fork("myorg") is True


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_ensure_tag_ruleset_never_raises_on_an_odd_response(
    mock_github_class, mock_read_user_config
):
    """The promise is 'never raises' -- an unexpected payload must not escape.

    Regression: an unpackable-into-two response made this raise ValueError,
    which propagated out of fork() and failed the fork itself.
    """
    mock_read_user_config.return_value = {"github": {"token": "t"}}
    g = mock_github_class.return_value
    g.requester.requestJsonAndCheck.return_value = object()  # not a 2-tuple

    forge = GitHubForge("https://github.com/foo/bar.git")
    assert forge.ensure_tag_ruleset("myorg/bar") is False


@patch("uvault.github.read_user_config")
def test_ensure_tag_ruleset_without_a_token(mock_read_user_config):
    mock_read_user_config.return_value = {}
    forge = GitHubForge("https://github.com/foo/bar.git")
    assert forge.ensure_tag_ruleset("myorg/bar") is False


@requires_github
@patch("uvault.github.read_user_config")
def test_ensure_tag_ruleset_without_pygithub(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "t"}}
    forge = GitHubForge("https://github.com/foo/bar.git")
    with patch.dict(
        "sys.modules", {"github": MagicMock(), "github.GithubException": None}
    ):
        assert forge.ensure_tag_ruleset("myorg/bar") is False


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_ensure_tag_ruleset_when_rulesets_are_unavailable(
    mock_github_class, mock_read_user_config, capsys
):
    """404 is what a plan without rulesets looks like."""
    mock_read_user_config.return_value = {"github": {"token": "t"}}
    from github.GithubException import GithubException  # type: ignore

    g = mock_github_class.return_value
    g.requester.requestJsonAndCheck.side_effect = GithubException(
        404, {"message": "Not Found"}, None
    )

    forge = GitHubForge("https://github.com/foo/bar.git")
    assert forge.ensure_tag_ruleset("myorg/bar") is False
    assert "public repository" in capsys.readouterr().out


@requires_github
@patch("uvault.github.read_user_config")
@patch("github.Github")
def test_ensure_tag_ruleset_on_an_unexpected_api_error(
    mock_github_class, mock_read_user_config, capsys
):
    mock_read_user_config.return_value = {"github": {"token": "t"}}
    from github.GithubException import GithubException  # type: ignore

    g = mock_github_class.return_value
    g.requester.requestJsonAndCheck.side_effect = GithubException(
        500, {"message": "boom"}, None
    )

    forge = GitHubForge("https://github.com/foo/bar.git")
    assert forge.ensure_tag_ruleset("myorg/bar") is False
    assert "could not protect tags" in capsys.readouterr().out
