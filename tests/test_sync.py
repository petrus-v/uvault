import pytest
from unittest.mock import patch, MagicMock
import tomlkit
import subprocess
from uvault.sync import SyncCommand, PackageSyncer


@pytest.fixture
def temp_pyproject(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    tag_prefix = "ppr-"

    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"
    ssh_only = true
    default = true

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "refs/pull/123/head", subdirectory = "my_addon" }
    """
    pyproject_file.write_text(content)
    return pyproject_file


def test_sync_no_pyproject(tmp_path, capsys):
    cmd = SyncCommand(pyproject_path=tmp_path / "nonexistent.toml")
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "pyproject.toml not found" in captured.out


def test_sync_no_tool_uvault(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test'")
    cmd = SyncCommand(pyproject_path=pyproject)
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "No [tool.uvault] section" in captured.out


def test_sync_no_vaults(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.uvault]\ntag_prefix = 'ppr-'")
    cmd = SyncCommand(pyproject_path=pyproject)
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "No [[tool.uvault.vcs_vaults]] configured." in captured.out


@patch("uvault.vcs.subprocess.run")
def test_sync_success(mock_run, temp_pyproject, tmp_path):
    def mock_run_side_effect(*args, **kwargs):
        mock_result = MagicMock()
        if args[0][:2] == ["git", "ls-remote"]:
            if args[0][2].startswith("https://github.com/OCA/"):
                mock_result.stdout = "1234abcd refs/pull/123/head\n"
            else:
                if "--tags" in args[0]:
                    raise subprocess.CalledProcessError(1, args[0])
        return mock_result

    mock_run.side_effect = mock_run_side_effect

    cache_dir = tmp_path / "cache"
    cmd = SyncCommand(pyproject_path=temp_pyproject, cache_dir=cache_dir)
    assert cmd.run() == 0

    with open(temp_pyproject) as f:
        doc = tomlkit.parse(f.read())

    assert "uv" in doc["tool"]
    assert "sources" in doc["tool"]["uv"]
    assert "my-addon" in doc["tool"]["uv"]["sources"]
    source = doc["tool"]["uv"]["sources"]["my-addon"]
    assert source["git"] == "git@github.com:petrus-v/my-addon.git"
    assert source["rev"] == "ppr-1234abcd"
    assert source["subdirectory"] == "my_addon"

    clone_call = [call for call in mock_run.call_args_list if "clone" in call.args[0]]
    assert len(clone_call) == 1
    assert clone_call[0].args[0] == [
        "git",
        "clone",
        "--bare",
        "https://github.com/OCA/my-addon",
        str(cache_dir / "my-addon"),
    ]

    push_call = [call for call in mock_run.call_args_list if "push" in call.args[0]]
    assert len(push_call) == 1
    assert push_call[0].args[0] == [
        "git",
        "-C",
        str(cache_dir / "my-addon"),
        "push",
        "git@github.com:petrus-v/my-addon.git",
        "1234abcd:refs/tags/ppr-1234abcd",
    ]


@patch("uvault.vcs.subprocess.run")
def test_sync_cache_exists(mock_run, temp_pyproject, tmp_path):
    def mock_run_side_effect(*args, **kwargs):
        mock_result = MagicMock()
        if args[0][:2] == ["git", "ls-remote"]:
            if "https://github.com/OCA/my-addon" in args[0]:
                mock_result.stdout = "5678efgh refs/pull/123/head\n"
            else:
                raise subprocess.CalledProcessError(1, args[0])
        return mock_result

    mock_run.side_effect = mock_run_side_effect

    cache_dir = tmp_path / "cache"
    repo_dir = cache_dir / "my-addon"
    repo_dir.mkdir(parents=True)

    cmd = SyncCommand(pyproject_path=temp_pyproject, cache_dir=cache_dir)
    assert cmd.run() == 0

    fetch_call = [call for call in mock_run.call_args_list if "fetch" in call.args[0]]
    assert len(fetch_call) == 1
    assert fetch_call[0].args[0] == ["git", "-C", str(repo_dir), "fetch", "origin"]


@patch("uvault.vcs.subprocess.run")
def test_sync_tag_exists_no_update(mock_run, temp_pyproject, tmp_path, capsys):
    def mock_run_side_effect(*args, **kwargs):
        mock_result = MagicMock()
        if args[0][:2] == ["git", "ls-remote"]:
            if "https://github.com/OCA/my-addon" in args[0]:
                mock_result.stdout = "1234abcd refs/pull/123/head\n"
            else:
                mock_result.stdout = "1234abcd refs/tags/ppr-1234abcd\n"
        return mock_result

    mock_run.side_effect = mock_run_side_effect

    cmd = SyncCommand(pyproject_path=temp_pyproject, cache_dir=tmp_path / "cache")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "already exists in vault" in captured.out

    push_call = [call for call in mock_run.call_args_list if "push" in call.args[0]]
    assert len(push_call) == 0


@patch("uvault.vcs.subprocess.run")
def test_sync_tag_exists_with_update(mock_run, temp_pyproject, tmp_path):
    def mock_run_side_effect(*args, **kwargs):
        mock_result = MagicMock()
        if args[0][:2] == ["git", "ls-remote"]:
            if "https://github.com/OCA/my-addon" in args[0]:
                mock_result.stdout = "1234abcd refs/pull/123/head\n"
            else:
                mock_result.stdout = "1234abcd refs/tags/ppr-1234abcd\n"
        return mock_result

    mock_run.side_effect = mock_run_side_effect

    cmd = SyncCommand(
        pyproject_path=temp_pyproject, cache_dir=tmp_path / "cache", update=True
    )
    assert cmd.run() == 0

    push_call = [call for call in mock_run.call_args_list if "push" in call.args[0]]
    assert len(push_call) == 1


@patch("uvault.vcs.subprocess.run")
def test_sync_failed_to_resolve_sha(mock_run, temp_pyproject, tmp_path, capsys):
    def mock_run_side_effect(*args, **kwargs):
        if args[0][:2] == ["git", "ls-remote"]:
            raise subprocess.CalledProcessError(1, args[0])

    mock_run.side_effect = mock_run_side_effect

    cmd = SyncCommand(pyproject_path=temp_pyproject, cache_dir=tmp_path / "cache")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "Failed to resolve" in captured.out


def test_get_repo_name():
    syncer = PackageSyncer("pkg", {}, None, None, {}, "", False)
    assert syncer._get_repo_name("https://github.com/OCA/social") == "social"
    assert syncer._get_repo_name("git@github.com:OCA/social.git") == "social"
    assert syncer._get_repo_name("ssh://git@github.com/OCA/social.git") == "social"


def test_compute_vault_url():
    syncer1 = PackageSyncer(
        "pkg",
        {},
        None,
        None,
        {"provider": "gitlab.com", "owner": "myorg", "ssh_only": False},
        "",
        False,
    )
    assert syncer1._compute_vault_url("repo") == "https://gitlab.com/myorg/repo.git"

    syncer2 = PackageSyncer(
        "pkg",
        {},
        None,
        None,
        {"provider": "github.com", "owner": "petrus-v", "ssh_only": True},
        "",
        False,
    )
    assert (
        syncer2._compute_vault_url("my-addon") == "git@github.com:petrus-v/my-addon.git"
    )

    syncer3 = PackageSyncer(
        "pkg", {}, None, None, {"provider": "github.com", "ssh_only": True}, "", False
    )
    assert syncer3._compute_vault_url("my-addon") == "git@github.com:my-addon.git"


@patch("uvault.vcs.subprocess.run")
def test_sync_rev_is_already_sha(mock_run, temp_pyproject, tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "1234567890abcdef1234567890abcdef12345678" }
    """
    pyproject.write_text(content)

    def mock_run_side_effect(*args, **kwargs):
        mock_result = MagicMock()
        mock_result.stdout = ""
        if (
            args[0][:2] == ["git", "ls-remote"]
            and "https://github.com/OCA/my-addon" in args[0]
        ):
            raise subprocess.CalledProcessError(1, args[0])
        return mock_result

    mock_run.side_effect = mock_run_side_effect

    cmd = SyncCommand(pyproject_path=pyproject, cache_dir=tmp_path / "cache")
    assert cmd.run() == 0

    with open(pyproject) as f:
        doc = tomlkit.parse(f.read())

    assert (
        doc["tool"]["uv"]["sources"]["my-addon"]["rev"]
        == "ppr-1234567890abcdef1234567890abcdef12345678"
    )


def test_sync_missing_package_or_invalid_config(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"

    [tool.uvault.sources]
    bad-addon = { git = "https://github.com/OCA/my-addon" }
    """
    pyproject.write_text(content)

    cmd = SyncCommand(pyproject_path=pyproject, packages=["unknown-addon"])
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "Package unknown-addon not found" in captured.out

    cmd = SyncCommand(pyproject_path=pyproject, packages=["bad-addon"])
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "missing 'git' or 'rev'" in captured.out


@patch("uvault.vcs.subprocess.run")
def test_sync_specific_package_implies_update(mock_run, temp_pyproject, tmp_path):
    def mock_run_side_effect(*args, **kwargs):
        mock_result = MagicMock()
        if args[0][:2] == ["git", "ls-remote"]:
            if "https://github.com/OCA/my-addon" in args[0]:
                mock_result.stdout = "1234abcd refs/pull/123/head\n"
            else:
                mock_result.stdout = "1234abcd refs/tags/ppr-1234abcd\n"  # tag exists
        return mock_result

    mock_run.side_effect = mock_run_side_effect

    # We specify packages=["my-addon"], which should imply force_update=True
    cmd = SyncCommand(
        pyproject_path=temp_pyproject,
        cache_dir=tmp_path / "cache",
        packages=["my-addon"],
    )
    assert cmd.run() == 0

    # It should push despite the tag existing
    push_call = [call for call in mock_run.call_args_list if "push" in call.args[0]]
    assert len(push_call) == 1
