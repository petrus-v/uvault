from pathlib import Path
from uvault.project import PyProject, normalize_pkg_name


class CheckCommand:
    def __init__(
        self,
        pyproject_path: str | Path = "pyproject.toml",
        auto_fix: bool = True,
        delete_extra: bool = False,
    ):
        self.pyproject_path = Path(pyproject_path)
        self.auto_fix = auto_fix
        self.delete_extra = delete_extra

    def run(self) -> int:
        project = PyProject(self.pyproject_path)
        try:
            project.read()
        except FileNotFoundError:
            print("pyproject.toml not found")
            return 1

        if not project.tool_uvault:
            print("No [tool.uvault] section found in pyproject.toml.")
            return 0

        if not project.uvault_sources:
            print("No uvault sources configured in pyproject.toml.")
            return 0

        from uvault.sync import SyncCommand

        # Run SyncCommand with:
        # - update=False: only process missing or develop mode packages
        # - delete_extra=self.delete_extra: parameterizable extra cleanup
        # - keep_develop=False: verify/restore develop packages back to vaulted state
        # - vaulting=False: read-only/dry-run, do not push to remote vault during check
        # - dry_run=not self.auto_fix: do not write to pyproject.toml if auto_fix is disabled
        cmd = SyncCommand(
            update=False,
            delete_extra=self.delete_extra,
            keep_develop=False,
            pyproject_path=str(self.pyproject_path),
            vaulting=False,
            dry_run=not self.auto_fix,
        )

        res = cmd.run()
        if res != 0:
            return res

        if cmd.has_changes:
            return 1

        # Even if cmd.run() returns 0 (no changes made/needed), we must verify that no package
        # is left in develop mode or completely missing (which can happen if a restoration failed).
        project.read()
        uv_sources = project.uv_sources
        for name in project.uvault_sources:
            norm_name = normalize_pkg_name(name)
            uv_source = uv_sources.get(norm_name)
            if not uv_source or uv_source.is_develop:
                return 1

        return 0
