import pytest
import tomlkit
from uvault.project import PyProject
from uvault.source import PackageSource


def test_pyproject_write_before_read(tmp_path):
    proj = PyProject(tmp_path / "pyproject.toml")
    with pytest.raises(RuntimeError, match="Cannot write before reading."):
        proj.write()


def test_set_uvault_source_normalize(tmp_path):
    proj = PyProject(tmp_path / "pyproject.toml")
    proj.doc = tomlkit.document()
    proj.set_uvault_source("My-Pkg", PackageSource("My-Pkg", {"git": "url"}))
    assert "My-Pkg" in proj.tool_uvault["sources"]

    # Update with different casing
    proj.set_uvault_source("my_pkg", PackageSource("my_pkg", {"git": "url2"}))
    assert "My-Pkg" not in proj.tool_uvault["sources"]
    assert "my_pkg" in proj.tool_uvault["sources"]


def test_set_uv_source_normalize(tmp_path):
    proj = PyProject(tmp_path / "pyproject.toml")
    proj.doc = tomlkit.document()
    proj.set_uv_source("My-Pkg", PackageSource("My-Pkg", {"git": "url"}))
    assert "My-Pkg" in proj.doc["tool"]["uv"]["sources"]

    # Update with different casing
    proj.set_uv_source("my_pkg", PackageSource("my_pkg", {"git": "url2"}))
    assert "My-Pkg" not in proj.doc["tool"]["uv"]["sources"]
    assert "my_pkg" in proj.doc["tool"]["uv"]["sources"]


def test_delete_uv_source_normalize(tmp_path):
    proj = PyProject(tmp_path / "pyproject.toml")
    proj.doc = tomlkit.document()
    proj.set_uv_source("My-Pkg", PackageSource("My-Pkg", {"git": "url"}))
    assert "My-Pkg" in proj.doc["tool"]["uv"]["sources"]

    # Delete with different casing
    proj.delete_uv_source("my_pkg")
    assert "My-Pkg" not in proj.doc["tool"]["uv"]["sources"]

    # Delete when empty (no error)
    proj.delete_uv_source("my_pkg")
