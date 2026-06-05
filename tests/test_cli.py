import pytest
from uvault.cli import main


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0

    captured = capsys.readouterr()
    assert "Development and vaulting workflow" in captured.out


def test_cli_execution(capsys):
    result = main([])
    assert result == 0
    captured = capsys.readouterr()
    assert "uvault CLI is ready." in captured.out
