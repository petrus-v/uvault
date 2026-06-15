import tomlkit
import tomlkit.items
from typing import TYPE_CHECKING

from uvault.vcs import get_vcs, VcsProvider, VcsReference

if TYPE_CHECKING:
    from uvault.forge import Forge


class PackageSource:
    """Represents a package source configuration from either [tool.uvault.sources] or [tool.uv.sources]."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = dict(config)

    @classmethod
    def from_toml(cls, name: str, config: dict) -> "PackageSource":
        return cls(name, config)

    def to_toml(self) -> tomlkit.items.InlineTable:
        table = tomlkit.inline_table()
        for k, v in self.config.items():
            table[k] = v
        return table

    @property
    def origin_url(self) -> str | None:
        """Returns the VCS origin URL. Currently only supports 'git'."""
        return self.config.get("git")

    @property
    def subdirectory(self) -> str | None:
        return self.config.get("subdirectory")

    @property
    def tag(self) -> str | None:
        return self.config.get("tag")

    @property
    def is_develop(self) -> bool:
        """Returns True if this is an editable/path-based source (development mode)."""
        return self.config.get("editable") is True or "path" in self.config

    def get_vcs(self) -> VcsProvider:
        """Instantiate the correct VCS provider for this source."""
        return get_vcs(self.config)

    def get_forge(self) -> "Forge | None":
        """Instantiate the correct Forge provider for this source."""
        from uvault.forge import create_forge

        return create_forge(self.origin_url)

    def fork(self, target_org: str) -> bool:
        """Fork the repository to the target organization using the forge API."""
        forge = self.get_forge()
        if forge:
            return forge.fork(target_org)
        return False

    def get_git_reference(self) -> VcsReference | None:
        """Extract the git reference from the configuration."""
        if not self.origin_url:
            return None
        return VcsReference.from_config(self.config)

    def update(self, **kwargs) -> None:
        """Update source properties, maintaining any unused/unknown configuration parameters."""
        for k, v in kwargs.items():
            if v is not None:
                self.config[k] = v
            elif k in self.config:
                del self.config[k]
