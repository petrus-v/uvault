import tomlkit
import tomlkit.items
from pathlib import Path

from uvault.source import PackageSource


import re
import typing


def normalize_pkg_name(name: str) -> str:
    """Normalize a Python package name for comparison."""
    return re.sub(r"[-_.]+", "-", name).lower()


def read_user_config() -> dict:
    config_path = Path("~/.config/uvault/config.toml").expanduser()
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                return tomlkit.parse(f.read())
            except Exception:
                pass
    return {}


class PyProject:
    """Abstraction over pyproject.toml configuration file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.doc: typing.Any = None

    def read(self):
        if not self.path.exists():
            raise FileNotFoundError(f"{self.path} not found")
        with open(self.path, "r", encoding="utf-8") as f:
            self.doc = tomlkit.parse(f.read())

    def write(self):
        if self.doc is None:
            raise RuntimeError("Cannot write before reading.")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(tomlkit.dumps(self.doc))

    def _ensure_section(self, *path_parts: str) -> tomlkit.items.Table:
        current = self.doc
        for part in path_parts:
            if part not in current:
                current.add(part, tomlkit.table())
            current = current[part]
        return current

    @property
    def tool_uvault(self) -> dict:
        return self.doc.get("tool", {}).get("uvault", {})

    @property
    def uvault_sources(self) -> dict[str, PackageSource]:
        return {
            normalize_pkg_name(k): PackageSource.from_toml(k, v)
            for k, v in self.tool_uvault.get("sources", {}).items()
        }

    def ensure_uv_sources(self) -> tomlkit.items.Table:
        return self._ensure_section("tool", "uv", "sources")

    @property
    def uv_sources(self) -> dict[str, PackageSource]:
        return {
            normalize_pkg_name(k): PackageSource.from_toml(k, v)
            for k, v in self.doc.get("tool", {})
            .get("uv", {})
            .get("sources", {})
            .items()
        }

    @property
    def project_version(self) -> str | None:
        return self.doc.get("project", {}).get("version")

    @property
    def tag_prefix(self) -> str:
        return self.tool_uvault.get("tag_prefix", "")

    @property
    def include_sha_in_release(self) -> bool:
        return self.tool_uvault.get("include_sha_in_release", True)

    @property
    def dev_directory(self) -> str:
        return self.tool_uvault.get("dev_directory", ".src")

    def get_vault_config(self) -> dict | None:
        vaults = self.tool_uvault.get("vcs_vaults", [])
        if not vaults:
            return None
        return next((v for v in vaults if v.get("default")), vaults[0])

    def set_uvault_source(self, name: str, source: PackageSource):
        sources = self._ensure_section("tool", "uvault", "sources")
        norm_name = normalize_pkg_name(name)
        for existing_key in list(sources.keys()):
            if normalize_pkg_name(existing_key) == norm_name and existing_key != name:
                del sources[existing_key]
        sources[name] = source.to_toml()

    def set_uv_source(self, name: str, source: PackageSource):
        sources = self._ensure_section("tool", "uv", "sources")
        norm_name = normalize_pkg_name(name)
        for existing_key in list(sources.keys()):
            if normalize_pkg_name(existing_key) == norm_name and existing_key != name:
                del sources[existing_key]
        sources[name] = source.to_toml()

    def delete_uv_source(self, name: str):
        sources = self.doc.get("tool", {}).get("uv", {}).get("sources", {})
        norm_name = normalize_pkg_name(name)
        for existing_key in list(sources.keys()):
            if normalize_pkg_name(existing_key) == norm_name:
                del sources[existing_key]
