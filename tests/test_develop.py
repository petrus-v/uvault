import pytest
from unittest.mock import patch, MagicMock
import tomlkit
from uvault.develop import DevelopCommand
from uvault.vcs import guess_repository_url, get_repo_name, compute_vault_urls
from importlib.metadata import PackageNotFoundError


@pytest.fixture
def temp_pyproject(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    tag_prefix = "ppr-"
    dev_directory = ".src"

    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"
    default = true

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "refs/pull/123/head", subdirectory = "my_addon" }
    """
    pyproject_file.write_text(content)
    return pyproject_file


def test_guess_repository_url():
    with patch("uvault.vcs.metadata") as mock_meta:
        m = MagicMock()
        m.get.return_value = "https://example.com/homepage"
        m.get_all.return_value = [
            "Source, https://github.com/owner/repo",
            "Repository, https://gitlab.com/owner/repo",
        ]
        mock_meta.return_value = m

        url = guess_repository_url("some-pkg")
        assert url == "https://github.com/owner/repo"


def test_guess_repository_url_gitlab():
    with patch("uvault.vcs.metadata") as mock_meta:
        m = MagicMock()
        m.get.return_value = "https://example.com/homepage"
        m.get_all.return_value = [
            "Repository, https://gitlab.com/owner/repo",
            "Other, https://git.sr.ht/~user/repo",
        ]
        mock_meta.return_value = m

        url = guess_repository_url("some-pkg")
        assert url == "https://gitlab.com/owner/repo"


def test_guess_repository_url_not_found():
    with patch("uvault.vcs.metadata", side_effect=PackageNotFoundError):
        assert guess_repository_url("unknown") is None


def test_get_repo_name():
    assert get_repo_name("https://github.com/OCA/my-addon") == "my-addon"
    assert get_repo_name("git@github.com:OCA/my-addon.git") == "my-addon"
    assert get_repo_name("ssh://git@github.com/OCA/my-addon.git") == "my-addon"


def test_compute_vault_urls():
    fetch, push = compute_vault_urls(
        "my-addon",
        {
            "provider": "gitlab.com",
            "owner": "cgi37",
            "fetch_ssh": False,
            "push_ssh": True,
        },
    )
    assert fetch == "https://gitlab.com/cgi37/my-addon.git"
    assert push == "ssh://git@gitlab.com/cgi37/my-addon.git"


def test_develop_no_pyproject(tmp_path, capsys):
    cmd = DevelopCommand(
        package="my-addon",
        branch="my-branch",
        pyproject_path=tmp_path / "nonexistent.toml",
    )
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "pyproject.toml not found" in captured.out


@patch("uvault.vcs.GitVcs.get_remote_sha", return_value="abcdef123")
@patch("uvault.vcs.subprocess.run")
def test_develop_success_with_config(mock_run, mock_get_sha, temp_pyproject, tmp_path):
    cmd = DevelopCommand(
        package="my-addon", branch="my-branch", pyproject_path=temp_pyproject
    )
    # Mock user config with custom remote and overriding 'origin'
    with patch(
        "uvault.develop.read_user_config",
        return_value={
            "remotes": {
                "myorg": "https://gitlab.com/myorg/",
                "origin": "ssh://git@github.com/my-fork/",
            }
        },
    ):
        assert cmd.run() == 0

    clone_call = [call for call in mock_run.call_args_list if "clone" in call.args[0]]
    assert len(clone_call) == 1
    assert clone_call[0].args[0] == [
        "git",
        "clone",
        "--filter=blob:none",
        "https://github.com/OCA/my-addon",
        str(tmp_path / ".src" / "my-addon"),
    ]

    checkout_call = [
        call for call in mock_run.call_args_list if "checkout" in call.args[0]
    ]
    assert len(checkout_call) == 1
    assert checkout_call[0].args[0] == [
        "git",
        "-C",
        str(tmp_path / ".src" / "my-addon"),
        "checkout",
        "-b",
        "my-branch",
        "abcdef123",
    ]

    remote_adds = [
        call
        for call in mock_run.call_args_list
        if "remote" in call.args[0] and "add" in call.args[0]
    ]
    assert len(remote_adds) == 3
    remotes_added = [c.args[0][5] for c in remote_adds]
    assert "origin" in remotes_added
    assert "vault" in remotes_added
    assert "myorg" in remotes_added

    with open(temp_pyproject) as f:
        doc = tomlkit.parse(f.read())

    assert (
        doc["tool"]["uv"]["sources"]["my-addon"]["path"] == "./.src/my-addon/my_addon"
    )
    assert doc["tool"]["uv"]["sources"]["my-addon"]["editable"] is True
    assert "subdirectory" not in doc["tool"]["uv"]["sources"]["my-addon"]


def test_develop_not_found(temp_pyproject, capsys):
    cmd = DevelopCommand(
        package="unknown", branch="my-branch", pyproject_path=temp_pyproject
    )
    assert cmd.run() == 1
    assert "Could not find configuration" in capsys.readouterr().out


@patch("uvault.vcs.subprocess.run")
@patch("uvault.vcs.GitVcs.get_remote_sha", return_value=None)
def test_develop_resolve_fails(mock_get_sha, mock_run, temp_pyproject, capsys):
    cmd = DevelopCommand(
        package="my-addon", branch="my-branch", pyproject_path=temp_pyproject
    )
    assert cmd.run() == 1
    assert "Could not resolve reference 123" in capsys.readouterr().out


@patch("uvault.vcs.subprocess.run")
def test_develop_dir_exists_no_ref(mock_run, tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon" }
    """
    pyproject_file.write_text(content)

    dest_dir = tmp_path / ".src" / "my-addon"
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)

    def mock_run_side_effect(*args, **kwargs):
        m = MagicMock()
        m.stdout = ""  # clean status
        return m

    mock_run.side_effect = mock_run_side_effect

    cmd = DevelopCommand(
        package="my-addon", branch="my-branch", pyproject_path=pyproject_file
    )
    assert cmd.run() == 1
    fetch_call = [call for call in mock_run.call_args_list if "fetch" in call.args[0]]
    assert len(fetch_call) == 0


@patch("uvault.vcs.subprocess.run")
def test_fetch_remote_string(mock_run, tmp_path):
    from uvault.vcs import GitVcs

    vcs = GitVcs()
    vcs.fetch_remote(tmp_path, ref="refs/pull/123/head")
    mock_run.assert_called_once_with(
        ["git", "-C", str(tmp_path), "fetch", "origin", "refs/pull/123/head"],
        check=True,
    )


@patch("uvault.vcs.GitVcs.get_remote_sha", return_value="abcdef123")
@patch("uvault.vcs.subprocess.run")
def test_develop_dir_exists_clean(mock_run, mock_get_sha, temp_pyproject, tmp_path):
    dest_dir = tmp_path / ".src" / "my-addon"
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)

    def mock_run_side_effect(*args, **kwargs):
        m = MagicMock()
        m.stdout = ""  # clean status
        return m

    mock_run.side_effect = mock_run_side_effect

    cmd = DevelopCommand(
        package="my-addon", pyproject_path=temp_pyproject, branch="some-branch"
    )
    assert cmd.run() == 0

    fetch_call = [call for call in mock_run.call_args_list if "fetch" in call.args[0]]
    assert len(fetch_call) == 1

    checkout_call = [
        call for call in mock_run.call_args_list if "checkout" in call.args[0]
    ]
    assert len(checkout_call) == 1
    assert checkout_call[0].args[0] == [
        "git",
        "-C",
        str(dest_dir),
        "checkout",
        "-b",
        "some-branch",
        "abcdef123",
    ]


@patch("uvault.vcs.GitVcs.get_remote_sha", return_value="abcdef123")
@patch("uvault.vcs.subprocess.run")
def test_develop_no_tool_uv(mock_run, mock_get_sha, tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    tag_prefix = "ppr-"
    dev_directory = ".src"
    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "refs/pull/123/head" }
    """
    pyproject_file.write_text(content)

    cmd = DevelopCommand(
        package="my-addon", branch="my-branch", pyproject_path=pyproject_file
    )
    assert cmd.run() == 0
    with open(pyproject_file) as f:
        doc = tomlkit.parse(f.read())
    assert "uv" in doc["tool"]
    assert "sources" in doc["tool"]["uv"]
    assert "my-addon" in doc["tool"]["uv"]["sources"]


def test_develop_no_git_in_source(temp_pyproject, tmp_path, capsys):
    with open(temp_pyproject, "r") as f:
        doc = tomlkit.parse(f.read())
    doc["tool"]["uvault"]["sources"]["my-addon"] = {"hg": "old_url"}
    with open(temp_pyproject, "w") as f:
        f.write(tomlkit.dumps(doc))

    cmd = DevelopCommand(
        package="my-addon", branch="dev-branch", pyproject_path=temp_pyproject
    )
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "does not have a valid VCS origin" in captured.out


@patch("uvault.vcs.GitVcs.get_remote_sha", return_value="abcdef123")
@patch("uvault.vcs.subprocess.run")
def test_develop_dir_exists_dirty(
    mock_run, mock_get_sha, temp_pyproject, tmp_path, capsys
):
    dest_dir = tmp_path / ".src" / "my-addon"
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)

    def mock_run_side_effect(*args, **kwargs):
        m = MagicMock()
        m.stdout = "M somefile.py"  # dirty status
        return m

    mock_run.side_effect = mock_run_side_effect

    cmd = DevelopCommand(
        package="my-addon", branch="my-branch", pyproject_path=temp_pyproject
    )
    assert cmd.run() == 1
    assert "uncommitted changes" in capsys.readouterr().out


def test_read_user_config(tmp_path):
    from uvault.project import read_user_config

    # By default reads from ~/.config/uvault/config.toml
    # We mock it to ensure coverage
    with patch("uvault.project.Path.expanduser", return_value=tmp_path / "config.toml"):
        (tmp_path / "config.toml").write_text(
            '[remotes]\nmyorg = "https://gitlab.com/"\n'
        )
        cfg = read_user_config()
        assert cfg.get("remotes", {}).get("myorg") == "https://gitlab.com/"

    with patch(
        "uvault.project.Path.expanduser", return_value=tmp_path / "nonexistent.toml"
    ):
        cfg = read_user_config()
        assert cfg == {}

    # Invalid toml
    with patch(
        "uvault.project.Path.expanduser", return_value=tmp_path / "invalid.toml"
    ):
        (tmp_path / "invalid.toml").write_text("trust_guessed_urls = true\ninvalid")
        cfg = read_user_config()
        assert cfg == {}


@patch("uvault.vcs.GitVcs.get_remote_sha", return_value="abcdef123")
@patch("uvault.vcs.subprocess.run")
def test_develop_ref_branch_exists(mock_run, mock_get_sha, tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "abcdef123" }
    """
    pyproject_file.write_text(content)
    dest_dir = tmp_path / ".src" / "my-addon"
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)

    def mock_run_side_effect(*args, **kwargs):
        m = MagicMock()
        m.stdout = ""
        if "show-ref" in args[0]:
            m.returncode = 0
        else:
            m.returncode = 0
        return m

    mock_run.side_effect = mock_run_side_effect
    cmd = DevelopCommand(
        package="my-addon", pyproject_path=pyproject_file, branch="some-branch"
    )
    assert cmd.run() == 0
    checkout_call = [
        call for call in mock_run.call_args_list if "checkout" in call.args[0]
    ]
    assert len(checkout_call) == 1
    assert checkout_call[0].args[0] == [
        "git",
        "-C",
        str(dest_dir),
        "checkout",
        "some-branch",
    ]


@patch("uvault.vcs.GitVcs.get_remote_sha", return_value="abcdef123")
@patch("uvault.vcs.subprocess.run")
def test_develop_unnormalized_name(mock_run, mock_get_sha, temp_pyproject, tmp_path):
    # Call develop with underscore but config has hyphen
    cmd = DevelopCommand(
        package="my_addon", branch="my-branch", pyproject_path=temp_pyproject
    )
    assert cmd.run() == 0

    clone_call = [call for call in mock_run.call_args_list if "clone" in call.args[0]]
    assert len(clone_call) == 1
    # Check that it uses the canonical name from the config for the directory
    assert clone_call[0].args[0] == [
        "git",
        "clone",
        "--filter=blob:none",
        "https://github.com/OCA/my-addon",
        str(tmp_path / ".src" / "my-addon"),
    ]

    with open(temp_pyproject) as f:
        doc = tomlkit.parse(f.read())

    # Check that it updated uv.sources using the canonical name
    assert (
        doc["tool"]["uv"]["sources"]["my-addon"]["path"] == "./.src/my-addon/my_addon"
    )
