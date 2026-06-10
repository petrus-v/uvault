import pytest
from unittest.mock import patch
from uvault.cli import main


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "Development and vaulting workflow" in captured.out


def test_cli_no_args(capsys):
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "required" in captured.err


@patch("uvault.cli.SyncCommand")
def test_cli_sync(mock_sync):
    mock_instance = mock_sync.return_value
    mock_instance.run.return_value = 0

    assert main(["sync", "--package", "my-addon", "--update", "--delete-extra"]) == 0

    mock_sync.assert_called_once_with(
        packages=["my-addon"], update=True, delete_extra=True, keep_develop=False
    )
    mock_instance.run.assert_called_once()


@patch("uvault.cli.SyncCommand")
def test_cli_sync_default(mock_sync):
    mock_instance = mock_sync.return_value
    mock_instance.run.return_value = 1

    assert main(["sync"]) == 1

    mock_sync.assert_called_once_with(
        packages=None, update=False, delete_extra=False, keep_develop=False
    )
    mock_instance.run.assert_called_once()


@patch("uvault.cli.DevelopCommand")
def test_cli_develop(mock_dev):
    mock_instance = mock_dev.return_value
    mock_instance.run.return_value = 0

    assert main(["develop", "my-addon", "my-branch"]) == 0

    mock_dev.assert_called_once_with(package="my-addon", branch="my-branch")
    mock_instance.run.assert_called_once()


def test_cli_develop_missing_branch(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["develop", "my-addon"])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "the following arguments are required: branch" in captured.err


@patch("uvault.cli.AddCommand")
def test_cli_add(mock_add):
    mock_instance = mock_add.return_value
    mock_instance.run.return_value = 0

    assert (
        main(
            [
                "add",
                "my-addon",
                "git+https://github.com",
                "--pr",
                "123",
                "--branch",
                "main",
                "--tag",
                "v1",
                "--rev",
                "abc",
                "--subdirectory",
                "sub",
            ]
        )
        == 0
    )

    mock_add.assert_called_once_with(
        package="my-addon",
        url="git+https://github.com",
        pr="123",
        branch="main",
        tag="v1",
        rev="abc",
        subdirectory="sub",
    )
    mock_instance.run.assert_called_once()


@patch("uvault.cli.SyncCommand")
def test_cli_release(mock_sync):
    mock_instance = mock_sync.return_value
    mock_instance.run.return_value = 0

    assert main(["release", "--package", "my-addon", "--keep-develop"]) == 0

    mock_sync.assert_called_once_with(
        packages=["my-addon"],
        update=False,
        delete_extra=False,
        keep_develop=True,
        release=True,
    )
    mock_instance.run.assert_called_once()
