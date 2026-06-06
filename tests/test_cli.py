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

    assert main(["sync", "--package", "my-addon", "--update"]) == 0

    mock_sync.assert_called_once_with(packages=["my-addon"], update=True)
    mock_instance.run.assert_called_once()


@patch("uvault.cli.SyncCommand")
def test_cli_sync_default(mock_sync):
    mock_instance = mock_sync.return_value
    mock_instance.run.return_value = 1

    assert main(["sync"]) == 1

    mock_sync.assert_called_once_with(packages=None, update=False)
    mock_instance.run.assert_called_once()
