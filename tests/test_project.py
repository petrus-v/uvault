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


# A pyproject.toml where the [tool.*] tables are not contiguous: another
# top-level table sits between them. tomlkit then hands back an
# OutOfOrderTableProxy for doc["tool"] rather than a Table, and the proxy has
# no .add(). This is the ordinary shape of a hatch project, where
# [tool.hatch.metadata] sits next to [project] and [tool.uv] comes later.
OUT_OF_ORDER_PYPROJECT = """\
[project]
name = "demo"
version = "0.1.0"

[tool.hatch.metadata]
allow-direct-references = true

[project.optional-dependencies]
dev = ["ruff"]

[tool.uv]
package = true
"""


def test_set_uvault_source_with_out_of_order_tool_tables(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(OUT_OF_ORDER_PYPROJECT)
    proj = PyProject(path)
    proj.read()

    # Guard the premise: without this the test would silently stop
    # exercising the out-of-order path if tomlkit ever changed.
    assert type(proj.doc["tool"]).__name__ == "OutOfOrderTableProxy"

    proj.set_uvault_source("my-pkg", PackageSource("my-pkg", {"git": "url"}))
    assert "my-pkg" in proj.tool_uvault["sources"]

    # The document must still round-trip.
    proj.write()
    reread = PyProject(path)
    reread.read()
    assert "my-pkg" in reread.tool_uvault["sources"]
    assert reread.doc["tool"]["hatch"]["metadata"]["allow-direct-references"] is True
    assert reread.doc["tool"]["uv"]["package"] is True


# Same shape, but with no [tool.uv] at all, so set_uv_source has to create it
# on the proxy rather than descend into an existing Table. Without that the
# `if part not in current` guard skips the failing line and the bug hides.
OUT_OF_ORDER_PYPROJECT_NO_UV = """\
[project]
name = "demo"
version = "0.1.0"

[tool.hatch.metadata]
allow-direct-references = true

[project.optional-dependencies]
dev = ["ruff"]

[tool.ruff]
line-length = 88
"""


def test_set_uv_source_with_out_of_order_tool_tables(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(OUT_OF_ORDER_PYPROJECT_NO_UV)
    proj = PyProject(path)
    proj.read()

    assert type(proj.doc["tool"]).__name__ == "OutOfOrderTableProxy"
    assert "uv" not in proj.doc["tool"]

    proj.set_uv_source("my-pkg", PackageSource("my-pkg", {"git": "url"}))
    assert "my-pkg" in proj.doc["tool"]["uv"]["sources"]

    proj.write()
    reread = PyProject(path)
    reread.read()
    assert "my-pkg" in reread.doc["tool"]["uv"]["sources"]
    assert reread.doc["tool"]["ruff"]["line-length"] == 88


def test_get_vault_config_routing(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(
        """\
[project]
name = "demo"
version = "0.1.0"

[[tool.uvault.vcs_vaults]]
provider = "github.com"
owner = "default-org"
default = true

[[tool.uvault.vcs_vaults]]
provider = "github.com"
owner = "special-org"
packages = ["odoo-addon-account"]

[[tool.uvault.vcs_vaults]]
provider = "gitlab.com"
owner = "odoo-org"
packages = ["odoo_addon_*", "*-core"]

[[tool.uvault.vcs_vaults]]
provider = "github.com"
owner = "mono-org"
repo = "single-vault"
packages = "mono-pkg"
"""
    )
    proj = PyProject(path)
    proj.read()

    def vault_for(pkg: str | None = None) -> dict:
        cfg = proj.get_vault_config(pkg)
        assert cfg is not None
        return cfg

    # Exact match wins over later wildcard
    assert vault_for("odoo-addon-account")["owner"] == "special-org"
    # Wildcard with normalization (_ / . / case)
    assert vault_for("Odoo.Addon-Sale")["owner"] == "odoo-org"
    assert vault_for("my-core")["owner"] == "odoo-org"
    # String packages field handled gracefully
    assert vault_for("mono-pkg")["repo"] == "single-vault"
    # Unmatched package falls back to default = true
    assert vault_for("requests")["owner"] == "default-org"
    # No package name returns default = true
    assert vault_for()["owner"] == "default-org"


def test_get_vault_config_no_vaults(tmp_path):
    proj = PyProject(tmp_path / "pyproject.toml")
    proj.doc = tomlkit.document()
    assert proj.get_vault_config("anything") is None
