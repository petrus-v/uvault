import pytest
from unittest.mock import patch, MagicMock

from uvault.github import attempt_github_fork

import importlib.util

HAS_GITHUB = importlib.util.find_spec("github") is not None

requires_github = pytest.mark.skipif(not HAS_GITHUB, reason="pygithub not installed")


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


@requires_github
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


@requires_github
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


@requires_github
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
    assert not attempt_github_fork(
        "https://github.com/foo/bar.git",
        {"provider": "github.com"},
    )


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_invalid_path(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    assert not attempt_github_fork(
        "https://github.com/foo",  # no slash
        {"provider": "github.com", "owner": "myorg"},
    )


@patch("uvault.github.read_user_config")
def test_attempt_github_fork_empty_path(mock_read_user_config):
    mock_read_user_config.return_value = {"github": {"token": "token123"}}
    assert not attempt_github_fork(
        "https://github.com/",  # empty path
        {"provider": "github.com", "owner": "myorg"},
    )


@requires_github
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
