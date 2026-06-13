from unittest.mock import patch, MagicMock

from uvault.github import attempt_github_fork


def test_attempt_github_fork_not_github_provider():
    assert not attempt_github_fork(
        "https://gitlab.com/foo/bar.git", {"provider": "gitlab.com"}
    )


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_no_token(mock_read_user_config):
    mock_read_user_config.return_value = {}
    assert not attempt_github_fork(
        "https://github.com/foo/bar.git", {"provider": "github.com", "owner": "myorg"}
    )


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_success(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    mock_github_module = MagicMock()
    mock_github_class = MagicMock()
    mock_auth_class = MagicMock()
    mock_github_module.Github = mock_github_class
    mock_github_module.Auth = mock_auth_class
    mock_github = MagicMock()
    mock_github_class.return_value = mock_github
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo
    mock_org = MagicMock()
    mock_github.get_organization.return_value = mock_org
    mock_fork = MagicMock()
    mock_fork.html_url = "https://github.com/myorg/bar"
    mock_org.create_fork.return_value = mock_fork

    with patch.dict(
        "sys.modules",
        {"github": mock_github_module, "github.GithubException": MagicMock()},
    ):
        with patch("time.sleep"):  # to speed up the test
            assert attempt_github_fork(
                "https://github.com/foo/bar.git",
                {
                    "provider": "github.com",
                    "owner": "myorg",
                },
            )

    mock_auth_class.Token.assert_called_once_with("token123")
    mock_github_class.assert_called_once_with(auth=mock_auth_class.Token.return_value)
    mock_github.get_repo.assert_called_once_with("foo/bar")
    mock_github.get_organization.assert_called_once_with("myorg")
    mock_org.create_fork.assert_called_once_with(mock_repo)


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_ssh_url(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    mock_github_module = MagicMock()
    mock_github_class = MagicMock()
    mock_auth_class = MagicMock()
    mock_github_module.Github = mock_github_class
    mock_github_module.Auth = mock_auth_class
    mock_github = MagicMock()
    mock_github_class.return_value = mock_github

    with patch.dict(
        "sys.modules",
        {"github": mock_github_module, "github.GithubException": MagicMock()},
    ):
        with patch("time.sleep"):
            assert attempt_github_fork(
                "git@github.com:foo/bar.git",
                {
                    "provider": "github.com",
                    "owner": "myorg",
                },
            )
    mock_github.get_repo.assert_called_once_with("foo/bar")


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_ssh_scheme_url(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    mock_github_module = MagicMock()
    mock_github_class = MagicMock()
    mock_github_module.Github = mock_github_class
    mock_github = MagicMock()
    mock_github_class.return_value = mock_github

    with patch.dict(
        "sys.modules",
        {"github": mock_github_module, "github.GithubException": MagicMock()},
    ):
        with patch("time.sleep"):
            assert attempt_github_fork(
                "ssh://git@github.com/foo/bar.git",
                {
                    "provider": "github.com",
                    "owner": "myorg",
                },
            )
    mock_github.get_repo.assert_called_once_with("foo/bar")


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_no_target_org(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    with patch.dict(
        "sys.modules", {"github": MagicMock(), "github.GithubException": MagicMock()}
    ):
        assert not attempt_github_fork(
            "https://github.com/foo/bar.git",
            {"provider": "github.com"},
        )


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_invalid_path(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    with patch.dict(
        "sys.modules", {"github": MagicMock(), "github.GithubException": MagicMock()}
    ):
        assert not attempt_github_fork(
            "https://github.com/foo",  # no slash
            {"provider": "github.com", "owner": "myorg"},
        )


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_empty_path(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    with patch.dict(
        "sys.modules", {"github": MagicMock(), "github.GithubException": MagicMock()}
    ):
        assert not attempt_github_fork(
            "https://github.com/",  # empty path
            {"provider": "github.com", "owner": "myorg"},
        )


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_github_exception(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}

    class DummyGithubException(Exception):
        pass

    mock_github_module = MagicMock()
    mock_github_class = MagicMock()
    mock_auth_class = MagicMock()
    mock_github_module.Github = mock_github_class
    mock_github_module.Auth = mock_auth_class
    mock_github_module.GithubException = DummyGithubException
    mock_github_exception_module = MagicMock()
    mock_github_exception_module.GithubException = DummyGithubException

    mock_github = MagicMock()
    mock_github_class.return_value = mock_github
    mock_github.get_repo.side_effect = DummyGithubException("Not Found")

    with patch.dict(
        "sys.modules",
        {
            "github": mock_github_module,
            "github.GithubException": mock_github_exception_module,
        },
    ):
        assert not attempt_github_fork(
            "https://github.com/foo/bar.git",
            {"provider": "github.com", "owner": "myorg"},
        )


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_missing_pygithub(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    with patch.dict("sys.modules", {"github": None}):
        assert not attempt_github_fork(
            "https://github.com/foo/bar.git",
            {"provider": "github.com", "owner": "myorg"},
        )


def test_get_github_repo_path():
    from uvault.github import get_github_repo_path

    assert get_github_repo_path("https://github.com/org/repo") == "org/repo"
    assert get_github_repo_path("https://github.com/org/repo.git") == "org/repo"
    assert get_github_repo_path("git@github.com:org/repo.git") == "org/repo"
    assert get_github_repo_path("ssh://git@github.com/org/repo.git") == "org/repo"
    assert get_github_repo_path("https://github.com/org") is None


@patch("uvault.github.read_user_config")
@patch("builtins.print")
def test_get_github_client_no_token(mock_print, mock_read_user_config):
    from uvault.github import get_github_client

    mock_read_user_config.return_value = {}

    mock_github_module = MagicMock()
    with patch.dict("sys.modules", {"github": mock_github_module}):
        client = get_github_client()
        assert client is not None
        mock_print.assert_called_once()
        mock_github_module.Github.assert_called_once_with()


@patch("uvault.github.read_user_config")
def test_get_github_client_success(mock_read_user_config):
    from uvault.github import get_github_client

    mock_read_user_config.return_value = {"github": {"token": "token123"}}

    mock_github_module = MagicMock()
    mock_auth_class = MagicMock()
    mock_github_module.Auth = mock_auth_class

    with patch.dict("sys.modules", {"github": mock_github_module}):
        client = get_github_client()
        assert client is not None
        mock_auth_class.Token.assert_called_once_with("token123")
        mock_github_module.Github.assert_called_once_with(
            auth=mock_auth_class.Token.return_value
        )


@patch("uvault.github.read_user_config")
def test_get_github_client_import_error(mock_read_user_config):
    from uvault.github import get_github_client

    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    with patch.dict("sys.modules", {"github": None}):
        assert get_github_client() is None


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_missing_github_exception(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    mock_github_module = MagicMock()
    with patch.dict(
        "sys.modules", {"github": mock_github_module, "github.GithubException": None}
    ):
        from uvault.github import attempt_github_fork

        assert not attempt_github_fork(
            "https://github.com/foo/bar.git",
            {"provider": "github.com", "owner": "myorg"},
        )
