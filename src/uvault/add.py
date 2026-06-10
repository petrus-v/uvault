from pathlib import Path
import urllib.parse
import tomlkit

from uvault.vcs import guess_repository_url
from uvault.source import PackageSource


class AddCommand:
    def __init__(
        self,
        package: str,
        url: str | None = None,
        pr: str | None = None,
        branch: str | None = None,
        tag: str | None = None,
        rev: str | None = None,
        subdirectory: str | None = None,
        pyproject_path: str = "pyproject.toml",
    ):
        self.package = package
        self.url = url
        self.pr = pr
        self.branch = branch
        self.tag = tag
        self.rev = rev
        self.subdirectory = subdirectory
        self.pyproject_path = Path(pyproject_path)

    def _parse_url(self):
        if not self.url:
            return

        # Handle git+https://... format
        if self.url.startswith("git+"):
            url_no_git = self.url[4:]
            parsed = urllib.parse.urlparse(url_no_git)

            # Extract rev/branch/tag from @...
            if "@" in parsed.path:
                path, ref = parsed.path.split("@", 1)
                self.url = f"{parsed.scheme}://{parsed.netloc}{path}"
                self.rev = (
                    ref  # by default it's a rev, could be branch/tag but uv accepts rev
                )
            else:
                self.url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

            # Extract subdirectory from #subdirectory=...
            if parsed.fragment:
                fragments = urllib.parse.parse_qs(parsed.fragment)
                if "subdirectory" in fragments:
                    self.subdirectory = fragments["subdirectory"][0]

    def run(self):
        if not self.pyproject_path.exists():
            print("pyproject.toml not found")
            return 1

        self._parse_url()

        if not self.url:
            guessed_url = guess_repository_url(self.package)
            if not guessed_url:
                print(f"Could not find or guess repository URL for {self.package}")
                return 1
            self.url = guessed_url
            print(f"Guessed repository URL: {self.url}")

        with open(self.pyproject_path, "r", encoding="utf-8") as f:
            doc = tomlkit.parse(f.read())

        if "tool" not in doc:
            doc.add("tool", tomlkit.table())
        if "uvault" not in doc["tool"]:
            doc["tool"].add("uvault", tomlkit.table())
        if "sources" not in doc["tool"]["uvault"]:
            doc["tool"]["uvault"].add("sources", tomlkit.table())

        uvault_sources = doc["tool"]["uvault"]["sources"]

        new_source = PackageSource(self.package, {})
        new_source.update(git=self.url)

        # Priority: pr, rev, branch, tag
        if self.pr:
            if "github.com" in self.url:
                new_source.update(rev=f"refs/pull/{self.pr}/head")
            else:
                new_source.update(rev=f"refs/merge-requests/{self.pr}/head")
        elif self.rev:
            new_source.update(rev=self.rev)
        elif self.branch:
            new_source.update(branch=self.branch)
        elif self.tag:
            new_source.update(tag=self.tag)

        if self.subdirectory:
            new_source.update(subdirectory=self.subdirectory)

        uvault_sources[self.package] = new_source.to_toml()

        with open(self.pyproject_path, "w", encoding="utf-8") as f:
            f.write(tomlkit.dumps(doc))

        print(f"Added {self.package} to [tool.uvault.sources]")
        print("Run `uvault sync` to lock this dependency in [tool.uv.sources]")

        return 0
