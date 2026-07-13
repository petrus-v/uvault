import pytest
from unittest.mock import patch
from uvault.check import CheckCommand
from uvault.cli import main
import tomlkit
from pathlib import Path


@pytest.fixture(autouse=True)
def mock_get_remote_sha():
    with patch("uvault.vcs.GitVcs.get_remote_sha") as mock:
        # Default behavior: simulate offline / error
        mock.side_effect = Exception("Offline for testing")
        yield mock


def test_check_default_args():
    cmd = CheckCommand()
    assert cmd.pyproject_path == Path("pyproject.toml")
    assert cmd.auto_fix is True
    assert cmd.delete_extra is False


def test_check_no_pyproject(tmp_path, capsys):
    cmd = CheckCommand(pyproject_path=tmp_path / "nonexistent.toml")
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "pyproject.toml not found" in captured.out


def test_check_no_tool_uvault(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test'")
    cmd = CheckCommand(pyproject_path=pyproject)
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "No [tool.uvault] section found" in captured.out


def test_check_no_vaults(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    tag_prefix = 'ppr-'

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "123" }
    """
    pyproject.write_text(content)
    cmd = CheckCommand(pyproject_path=pyproject)
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "No [[tool.uvault.vcs_vaults]] configured." in captured.out


def test_check_no_sources(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.uvault]\ntag_prefix = 'ppr-'")
    cmd = CheckCommand(pyproject_path=pyproject)
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "No uvault sources configured in pyproject.toml." in captured.out


def test_check_missing_in_uv_sources(tmp_path, capsys, mock_get_remote_sha):
    mock_get_remote_sha.side_effect = None
    mock_get_remote_sha.return_value = "1234abcd"

    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "123" }
    """
    pyproject.write_text(content)
    cmd = CheckCommand(pyproject_path=pyproject, auto_fix=False)
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "Syncing my-addon..." in captured.out


def test_check_develop_mode(tmp_path, capsys, mock_get_remote_sha):
    mock_get_remote_sha.side_effect = None
    mock_get_remote_sha.return_value = "1234abcd"

    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "123" }

    [tool.uv.sources]
    my-addon = { path = "./.src/my-addon", editable = true }
    """
    pyproject.write_text(content)
    cmd = CheckCommand(pyproject_path=pyproject, auto_fix=False)
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "is in develop mode" in captured.out


def test_check_success(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "123" }

    [tool.uv.sources]
    my-addon = { git = "https://github.com/petrus-v/my-addon", tag = "ppr+123" }
    """
    pyproject.write_text(content)
    cmd = CheckCommand(pyproject_path=pyproject)
    assert cmd.run() == 0


def test_check_auto_fix_success(tmp_path, capsys, mock_get_remote_sha):
    mock_get_remote_sha.side_effect = None
    mock_get_remote_sha.return_value = "1234abcd"

    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    tag_prefix = "ppr-"
    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"
    default = true

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "123", subdirectory = "my_subdir" }

    [tool.uv.sources]
    my-addon = { path = "./.src/my-addon", editable = true }
    """
    pyproject.write_text(content)

    cmd = CheckCommand(pyproject_path=pyproject, auto_fix=True)
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "is in develop mode" in captured.out
    assert "Updated pyproject.toml" in captured.out

    with open(pyproject, "r") as f:
        doc = tomlkit.parse(f.read())

    assert (
        doc["tool"]["uv"]["sources"]["my-addon"]["git"]
        == "https://github.com/petrus-v/my-addon.git"
    )
    assert doc["tool"]["uv"]["sources"]["my-addon"]["tag"] == "ppr+1234abcd"
    assert doc["tool"]["uv"]["sources"]["my-addon"]["subdirectory"] == "my_subdir"


def test_check_no_auto_fix(tmp_path, capsys, mock_get_remote_sha):
    mock_get_remote_sha.side_effect = None
    mock_get_remote_sha.return_value = "1234abcd"

    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    tag_prefix = "ppr-"
    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"
    default = true

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "123" }

    [tool.uv.sources]
    my-addon = { path = "./.src/my-addon", editable = true }
    """
    pyproject.write_text(content)

    cmd = CheckCommand(pyproject_path=pyproject, auto_fix=False)
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "is in develop mode" in captured.out
    assert "Dry-run: pyproject.toml would be updated." in captured.out

    with open(pyproject, "r") as f:
        doc = tomlkit.parse(f.read())

    assert doc["tool"]["uv"]["sources"]["my-addon"]["path"] == "./.src/my-addon"


def test_check_delete_extra(tmp_path, capsys):
    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"
    default = true

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "123" }

    [tool.uv.sources]
    my-addon = { git = "https://github.com/petrus-v/my-addon.git", tag = "ppr+123" }
    other-addon = { git = "https://github.com/petrus-v/other-addon.git", tag = "ppr+456" }
    """
    pyproject.write_text(content)

    # Without delete_extra: should pass since extra package is ignored
    cmd = CheckCommand(pyproject_path=pyproject, delete_extra=False)
    assert cmd.run() == 0

    # With delete_extra: should fail and fix (delete) extra package
    cmd = CheckCommand(pyproject_path=pyproject, delete_extra=True, auto_fix=True)
    assert cmd.run() == 1
    captured = capsys.readouterr()
    assert "Removed extra package other-addon" in captured.out

    with open(pyproject, "r") as f:
        doc = tomlkit.parse(f.read())

    assert "other-addon" not in doc["tool"]["uv"]["sources"]


@patch("uvault.cli.CheckCommand")
def test_cli_check(mock_check):
    mock_instance = mock_check.return_value
    mock_instance.run.return_value = 0

    assert main(["check"]) == 0
    mock_check.assert_called_once_with(auto_fix=True, delete_extra=False)
    mock_instance.run.assert_called_once()


@patch("uvault.cli.CheckCommand")
def test_cli_check_no_auto_fix(mock_check):
    mock_instance = mock_check.return_value
    mock_instance.run.return_value = 0

    assert main(["check", "--no-auto-fix", "--delete-extra"]) == 0
    mock_check.assert_called_once_with(auto_fix=False, delete_extra=True)
    mock_instance.run.assert_called_once()


def test_check_develop_mode_failed_restore(tmp_path, capsys, mock_get_remote_sha):
    mock_get_remote_sha.side_effect = None
    mock_get_remote_sha.return_value = None

    pyproject = tmp_path / "pyproject.toml"
    content = """
    [tool.uvault]
    [[tool.uvault.vcs_vaults]]
    provider = "github.com"
    owner = "petrus-v"

    [tool.uvault.sources]
    my-addon = { git = "https://github.com/OCA/my-addon", rev = "123" }

    [tool.uv.sources]
    my-addon = { path = "./.src/my-addon", editable = true }
    """
    pyproject.write_text(content)

    cmd = CheckCommand(pyproject_path=pyproject, auto_fix=True)
    assert cmd.run() == 1
