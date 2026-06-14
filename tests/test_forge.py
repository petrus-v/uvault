from uvault.forge import Forge, create_forge
from uvault.github import GitHubForge
from unittest.mock import patch


class DummyForge(Forge):
    def fork(self, target_org: str) -> bool:
        return True

    def enrich_package_status(self, pkg_status, ignore_labels) -> str | None:
        return None

    def get_remote_sha(self, ref_type: str, ref_value: str) -> str | None:
        return None

    def get_divergence(self, base_sha: str, head_sha: str):
        return None


def test_forge_abc():
    forge = DummyForge("https://example.com/repo")
    assert forge.origin_url == "https://example.com/repo"
    assert forge.fork("org") is True
    assert forge.enrich_package_status(None, []) is None
    assert forge.get_remote_sha("BRANCH", "main") is None
    assert forge.get_divergence("a", "b") is None


def test_create_forge():
    assert create_forge(None) is None
    assert create_forge("https://example.com/repo") is None

    gh_forge = create_forge("https://github.com/org/repo")
    assert isinstance(gh_forge, GitHubForge)


@patch("uvault.github.GitHubForge._get_client")
def test_github_forge_methods_no_client(mock_get_client):
    mock_get_client.return_value = None
    forge = GitHubForge("https://github.com/org/repo")

    assert forge.get_remote_sha("BRANCH", "main") is None
    assert forge.get_divergence("a", "b") is None

    # Also test path = None
    mock_get_client.return_value = "client"
    forge.path = None
    assert forge.get_remote_sha("BRANCH", "main") is None
    assert forge.get_divergence("a", "b") is None
