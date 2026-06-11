# Contributing to uvault

Thank you for your interest in contributing to `uvault`! This document provides the essential commands you need to work on the project.

## Running Tests

We use `pytest` for running tests. Our CI requires 100% test coverage.

To run the standard test suite:
```bash
uv run pytest
```

To run the test suite with the `github` extra enabled (which is required to reach 100% coverage on `github.py`):
```bash
uv run --extra github pytest
```

## Documentation

The documentation is built using [Zensical](https://zensical.org/).

### Serve Locally

To preview your documentation changes locally with live-reloading, run:
```bash
uv run zensical serve
```

### Build the Documentation

To build the static HTML site (output will be in the `site/` directory):
```bash
uv run zensical build
```

### Publishing the Documentation

The publication of the documentation is fully automated. Whenever code is pushed to the `main` branch, a GitHub Actions workflow (`.github/workflows/docs.yml`) is automatically triggered. This CI workflow builds the documentation using Zensical and securely deploys the resulting static files directly to **GitHub Pages**. You do not need to run any manual deployment commands.

## Making a Release

We use `bump-my-version` to manage versioning and release tags. When you are ready to make a release, use the following command to bump the version. This will automatically update `pyproject.toml`, `src/uvault/__init__.py`, `uv.lock`, and create the appropriate Git commit and tag.

```bash
uvx bump-my-version bump [major|minor|patch]
```

For example, to publish a new patch release:
```bash
uvx bump-my-version bump patch
git push --tags
```
*(Note: Pushing the newly created tag to the repository will automatically trigger the CI workflow to build and publish the package to PyPI.)*
