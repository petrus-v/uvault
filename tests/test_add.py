from unittest.mock import patch
import tomlkit
from uvault.add import AddCommand


def test_add_no_pyproject(tmp_path, capsys):
    cmd = AddCommand(
        package="my-addon",
        url="https://github.com/OCA/my-addon",
        pyproject_path=tmp_path / "nonexistent.toml",
    )
    assert cmd.run() == 1
    assert "pyproject.toml not found" in capsys.readouterr().out


def test_add_success_pep508(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("[project]\nname = 'test'")

    cmd = AddCommand(
        package="my-addon",
        url="git+https://github.com/OCA/website@refs/pull/1170/head#subdirectory=website_social",
        pyproject_path=pyproject_file,
    )
    assert cmd.run() == 0

    with open(pyproject_file) as f:
        doc = tomlkit.parse(f.read())

    sources = doc["tool"]["uvault"]["sources"]
    assert sources["my-addon"]["git"] == "https://github.com/OCA/website"
    assert sources["my-addon"]["rev"] == "refs/pull/1170/head"
    assert sources["my-addon"]["subdirectory"] == "website_social"


def test_add_success_pep508_no_ref(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("[project]\nname = 'test'")

    cmd = AddCommand(
        package="my-addon",
        url="git+https://github.com/OCA/website#subdirectory=website_social",
        pyproject_path=pyproject_file,
    )
    assert cmd.run() == 0

    with open(pyproject_file) as f:
        doc = tomlkit.parse(f.read())

    sources = doc["tool"]["uvault"]["sources"]
    assert sources["my-addon"]["git"] == "https://github.com/OCA/website"
    assert "rev" not in sources["my-addon"]
    assert sources["my-addon"]["subdirectory"] == "website_social"


def test_add_success_flags(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("")

    cmd = AddCommand(
        package="my-addon",
        url="https://github.com/OCA/website",
        pr="1170",
        subdirectory="website_social",
        pyproject_path=pyproject_file,
    )
    assert cmd.run() == 0

    with open(pyproject_file) as f:
        doc = tomlkit.parse(f.read())

    sources = doc["tool"]["uvault"]["sources"]
    assert sources["my-addon"]["git"] == "https://github.com/OCA/website"
    assert sources["my-addon"]["rev"] == "refs/pull/1170/head"
    assert sources["my-addon"]["subdirectory"] == "website_social"


def test_add_success_flags_gitlab(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("")

    cmd = AddCommand(
        package="my-addon",
        url="https://gitlab.com/cgi37/website",
        pr="1170",
        pyproject_path=pyproject_file,
    )
    assert cmd.run() == 0

    with open(pyproject_file) as f:
        doc = tomlkit.parse(f.read())

    sources = doc["tool"]["uvault"]["sources"]
    assert sources["my-addon"]["git"] == "https://gitlab.com/cgi37/website"
    assert sources["my-addon"]["rev"] == "refs/merge-requests/1170/head"


def test_add_branch(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("")
    cmd = AddCommand(
        package="my-addon",
        url="https://github.com/OCA/website",
        branch="16.0",
        pyproject_path=pyproject_file,
    )
    assert cmd.run() == 0
    with open(pyproject_file) as f:
        doc = tomlkit.parse(f.read())
    assert doc["tool"]["uvault"]["sources"]["my-addon"]["branch"] == "16.0"


def test_add_tag(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("")
    cmd = AddCommand(
        package="my-addon",
        url="https://github.com/OCA/website",
        tag="v1.0",
        pyproject_path=pyproject_file,
    )
    assert cmd.run() == 0
    with open(pyproject_file) as f:
        doc = tomlkit.parse(f.read())
    assert doc["tool"]["uvault"]["sources"]["my-addon"]["tag"] == "v1.0"


def test_add_rev(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("")
    cmd = AddCommand(
        package="my-addon",
        url="https://github.com/OCA/website",
        rev="abcdef",
        pyproject_path=pyproject_file,
    )
    assert cmd.run() == 0
    with open(pyproject_file) as f:
        doc = tomlkit.parse(f.read())
    assert doc["tool"]["uvault"]["sources"]["my-addon"]["rev"] == "abcdef"


@patch(
    "uvault.add.guess_repository_url", return_value="https://github.com/guessed/repo"
)
def test_add_guess_url_success(mock_guess, tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("")

    cmd = AddCommand(package="my-addon", pyproject_path=pyproject_file)
    assert cmd.run() == 0

    with open(pyproject_file) as f:
        doc = tomlkit.parse(f.read())

    sources = doc["tool"]["uvault"]["sources"]
    assert sources["my-addon"]["git"] == "https://github.com/guessed/repo"


@patch("uvault.add.guess_repository_url", return_value=None)
def test_add_guess_url_fail(mock_guess, tmp_path, capsys):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text("")

    cmd = AddCommand(package="my-addon", pyproject_path=pyproject_file)
    assert cmd.run() == 1
    assert "Could not find or guess repository URL" in capsys.readouterr().out
