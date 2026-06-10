import pytest
from uvault.project import PyProject


def test_pyproject_write_before_read(tmp_path):
    proj = PyProject(tmp_path / "pyproject.toml")
    with pytest.raises(RuntimeError, match="Cannot write before reading."):
        proj.write()
