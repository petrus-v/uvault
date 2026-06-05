# uvault

Development and vaulting workflow for [uv](https://github.com/astral-sh/uv) VCS dependencies.

Secure your Python projects against deleted or force-pushed upstream commits.

`uvault` automatically vaults transient VCS references (like GitHub PRs)
into your organization's own repositories, while allowing developers to instantly
switch dependencies into local editable mode—fully integrated with pyproject.toml and uv.

