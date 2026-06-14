from unittest.mock import patch
from uvault.source import PackageSource


def test_package_source():
    # Test initialization and properties
    cfg = {
        "git": "https://example.com/repo.git",
        "subdirectory": "src",
        "tag": "v1.0.0",
    }
    src = PackageSource("my-pkg", cfg)

    assert src.name == "my-pkg"
    assert src.origin_url == "https://example.com/repo.git"
    assert src.subdirectory == "src"
    assert src.tag == "v1.0.0"
    assert not src.is_develop

    # Test from_toml
    src2 = PackageSource.from_toml("my-pkg", cfg)
    assert src2.origin_url == "https://example.com/repo.git"

    # Test to_toml
    toml_table = src.to_toml()
    assert toml_table["git"] == "https://example.com/repo.git"

    # Test update and delete
    src.update(tag="v2.0.0", subdirectory=None, extra="data")
    assert src.config["tag"] == "v2.0.0"
    assert "subdirectory" not in src.config
    assert src.config["extra"] == "data"

    # Test get_git_reference without origin_url
    src_no_git = PackageSource("no-git", {"other": "value"})
    assert src_no_git.get_git_reference() is None


@patch("uvault.forge.create_forge")
def test_package_source_fork(mock_create_forge):
    source = PackageSource("pkg-a", {"git": "https://github.com/org/repoa"})

    # Test forge returns True
    mock_forge = mock_create_forge.return_value
    mock_forge.fork.return_value = True
    assert source.fork("my-org") is True
    mock_forge.fork.assert_called_once_with("my-org")

    # Test forge is None
    mock_create_forge.return_value = None
    assert source.fork("my-org") is False
