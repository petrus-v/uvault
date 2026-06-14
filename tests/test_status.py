from unittest.mock import patch, MagicMock
from uvault.status import StatusCommand, PackageStatus
from uvault.source import PackageSource
from datetime import datetime, timezone, timedelta


def test_status_format_date():
    cmd = StatusCommand(None, "list", "name")

    assert cmd._format_date(None) == "inconnue"

    now = datetime.now(timezone.utc)
    assert cmd._format_date(now) == "aujourd'hui"

    naive_now = datetime.now()
    assert cmd._format_date(naive_now) == "aujourd'hui"

    assert cmd._format_date(now - timedelta(days=2)) == "il y a 2 jour(s)"
    assert cmd._format_date(now - timedelta(days=45)) == "il y a 1 mois"
    assert cmd._format_date(now - timedelta(days=400)) == "il y a 1 an(s)"


def test_status_get_color():
    cmd = StatusCommand(None, "list", "name")
    assert cmd._get_status_color("MERGED") == "🟢"
    assert cmd._get_status_color("OPEN") == "🟡"
    assert cmd._get_status_color("CLOSED") == "🔴"
    assert cmd._get_status_color("ACTIVE") == "🔵"
    assert cmd._get_status_color("UNKNOWN") == "⚪"


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_run(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource(
            "pkg-a", {"git": "https://github.com/org/repoa", "branch": "main"}
        ),
        "pkg-b": PackageSource(
            "pkg-b",
            {"git": "https://github.com/org/repob", "rev": "refs/pull/123/head"},
        ),
        "pkg-c": PackageSource(
            "pkg-c", {"git": "https://github.com/org/repoc", "tag": "v1"}
        ),
    }

    mock_proj.uv_sources = {
        "pkg-a": PackageSource("pkg-a", {"rev": "sha123"}),
        "pkg-b": PackageSource("pkg-b", {"rev": "sha456"}),
        "pkg-c": PackageSource("pkg-c", {"rev": "sha789"}),
    }

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_repo_a = MagicMock()
    mock_branch_a = MagicMock()
    mock_branch_a.commit.commit.author.date = datetime.now(timezone.utc)
    mock_branch_a.commit.sha = "sha123"
    mock_repo_a.get_branch.return_value = mock_branch_a

    mock_repo_b = MagicMock()
    mock_pull_b = MagicMock()
    mock_pull_b.merged = False
    mock_pull_b.state = "open"
    mock_pull_b.labels = [MagicMock(name="staled")]
    mock_pull_b.labels[0].name = "staled"
    mock_pull_b.updated_at = datetime.now(timezone.utc) - timedelta(days=10)
    mock_pull_b.head.sha = "sha456"
    mock_repo_b.get_pull.return_value = mock_pull_b

    def get_repo_side_effect(path):
        if path == "org/repoa":
            return mock_repo_a
        if path == "org/repob":
            return mock_repo_b
        raise Exception("Not found")

    mock_client.get_repo.side_effect = get_repo_side_effect

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0

    captured = capsys.readouterr()
    assert "pkg-a" in captured.out
    assert "ACTIVE" in captured.out
    assert "pkg-b" in captured.out
    assert "OPEN" in captured.out
    assert "staled" in captured.out

    # filter packages
    cmd = StatusCommand(packages=["pkg-a"], format_type="inline", sort_by="status")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "VCS Metadata:" in captured.out
    assert "pkg-a" in captured.out
    assert "pkg-b" not in captured.out

    cmd = StatusCommand(packages=["pkg-b"], format_type="table", sort_by="date")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "Last Activity" in captured.out
    assert "Package" in captured.out
    assert "pkg-b" in captured.out
    assert "pkg-a" not in captured.out


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_run_no_client(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource(
            "pkg-a", {"git": "https://github.com/org/repoa", "branch": "main"}
        ),
    }
    mock_get_client.return_value = None

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "UNKNOWN" in captured.out


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_pr_merged(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource(
            "pkg-a",
            {"git": "https://github.com/org/repoa", "rev": "refs/pull/123/head"},
        ),
    }

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_repo_a = MagicMock()
    mock_pull_a = MagicMock()
    mock_pull_a.merged = True
    mock_pull_a.labels = []
    mock_pull_a.updated_at = datetime.now(timezone.utc)
    mock_repo_a.get_pull.return_value = mock_pull_a
    mock_client.get_repo.return_value = mock_repo_a

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "MERGED" in captured.out


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_pr_closed(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource(
            "pkg-a",
            {"git": "https://github.com/org/repoa", "rev": "refs/pull/123/head"},
        ),
    }

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_repo_a = MagicMock()
    mock_pull_a = MagicMock()
    mock_pull_a.merged = False
    mock_pull_a.state = "closed"
    mock_pull_a.labels = []
    mock_pull_a.updated_at = datetime.now(timezone.utc)
    mock_repo_a.get_pull.return_value = mock_pull_a
    mock_client.get_repo.return_value = mock_repo_a

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "CLOSED" in captured.out


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_pr_exception(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource(
            "pkg-a",
            {"git": "https://github.com/org/repoa", "rev": "refs/pull/123/head"},
        ),
        "pkg-b": PackageSource(
            "pkg-b", {"git": "https://github.com/org/repob", "branch": "main"}
        ),
    }

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_repo_a = MagicMock()
    mock_repo_a.get_pull.side_effect = Exception("API error")
    mock_repo_a.get_branch.side_effect = Exception("API error")
    mock_client.get_repo.return_value = mock_repo_a

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "UNKNOWN" in captured.out


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_behind(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource(
            "pkg-a", {"git": "https://github.com/org/repoa", "branch": "main"}
        ),
        "pkg-b": PackageSource(
            "pkg-b", {"git": "https://github.com/org/repob", "branch": "dev"}
        ),
    }

    # We inject behind logic by mocking _check_package
    with patch.object(StatusCommand, "_check_package") as mock_check:
        mock_check.side_effect = [
            PackageStatus(
                name="pkg-b",
                source_url="org/repoa",
                ref_type="BRANCH",
                ref_value="main",
                status="ACTIVE",
                behind=5,
                diverged=True,
                labels=[],
                last_activity=None,
            ),
            PackageStatus(
                name="pkg-a",
                source_url="org/" + ("very_long_repo_name_" * 5),
                ref_type="BRANCH",
                ref_value="main",
                status="ACTIVE",
                behind=0,
                diverged=False,
                labels=[],
                last_activity=None,
            ),
        ]

        cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
        cmd.run()
        captured = capsys.readouterr()
        assert "5 nouveaux commits" in captured.out

        # Reset side effect since it consumed the iterator
        mock_check.side_effect = [
            PackageStatus(
                name="pkg-a",
                source_url="org/" + ("very_long_repo_name_" * 5),
                ref_type="BRANCH",
                ref_value="main",
                status="ACTIVE",
                behind=0,
                diverged=False,
                labels=[],
                last_activity=None,
            ),
            PackageStatus(
                name="pkg-b",
                source_url="org/repoa",
                ref_type="BRANCH",
                ref_value="main",
                status="ACTIVE",
                behind=5,
                diverged=True,
                labels=[],
                last_activity=None,
            ),
        ]
        cmd = StatusCommand(packages=None, format_type="table", sort_by="name")
        cmd.run()
        captured = capsys.readouterr()
        assert "+5" in captured.out
        assert "very_long_repo_n..." in captured.out
        assert "..." in captured.out

        mock_check.side_effect = [
            PackageStatus(
                name="pkg-a",
                source_url="org/" + ("very_long_repo_name_" * 5),
                ref_type="BRANCH",
                ref_value="main",
                status="ACTIVE",
                behind=0,
                diverged=False,
                labels=[],
                last_activity=None,
            ),
            PackageStatus(
                name="pkg-b",
                source_url="org/repoa",
                ref_type="BRANCH",
                ref_value="main",
                status="ACTIVE",
                behind=5,
                diverged=True,
                labels=[],
                last_activity=None,
            ),
        ]
        cmd = StatusCommand(packages=None, format_type="inline", sort_by="name")
        cmd.run()
        captured = capsys.readouterr()
        assert "+5 commits (Force-Push detecté!)" in captured.out


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_compare_diverged(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource(
            "pkg-a", {"git": "https://github.com/org/repoa", "branch": "main"}
        ),
    }
    mock_proj.uv_sources = {
        "pkg-a": PackageSource(
            "pkg-a", {"git": "https://github.com/org/repoa", "rev": "sha123"}
        ),
    }

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_repo_a = MagicMock()
    mock_branch_a = MagicMock()
    mock_branch_a.commit.commit.author.date = datetime.now(timezone.utc)
    mock_branch_a.commit.sha = "sha456"
    mock_repo_a.get_branch.return_value = mock_branch_a
    mock_comp = MagicMock()
    mock_comp.ahead_by = 2
    mock_comp.behind_by = 1
    mock_comp.status = "diverged"
    mock_repo_a.compare.return_value = mock_comp
    mock_client.get_repo.return_value = mock_repo_a

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "Force-Push detecté!" in captured.out


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_vaulted_tag(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource(
            "pkg-a", {"git": "https://github.com/org/repoa", "branch": "main"}
        ),
    }
    mock_proj.uv_sources = {
        "pkg-a": PackageSource(
            "pkg-a", {"git": "https://github.com/org/repoa", "tag": "v1.0"}
        ),
    }

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_repo_a = MagicMock()
    mock_branch_a = MagicMock()
    mock_branch_a.commit.sha = "sha456"
    mock_branch_a.commit.commit.author.date = datetime.now(timezone.utc)
    mock_repo_a.get_branch.return_value = mock_branch_a
    mock_gh_ref = MagicMock()
    mock_gh_ref.object.sha = "sha123"
    mock_repo_a.get_git_ref.return_value = mock_gh_ref

    mock_comp = MagicMock()
    mock_comp.ahead_by = 2
    mock_comp.behind_by = 0
    mock_comp.status = "ahead"
    mock_repo_a.compare.return_value = mock_comp
    mock_client.get_repo.return_value = mock_repo_a

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0
    mock_repo_a.get_git_ref.assert_called_once_with("tags/v1.0")


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_vaulted_branch(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource(
            "pkg-a", {"git": "https://github.com/org/repoa", "branch": "main"}
        ),
    }
    mock_proj.uv_sources = {
        "pkg-a": PackageSource(
            "pkg-a", {"git": "https://github.com/org/repoa", "branch": "dev"}
        ),
    }

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_repo_a = MagicMock()
    mock_branch_main = MagicMock()
    mock_branch_main.commit.sha = "sha456"
    mock_branch_main.commit.commit.author.date = datetime.now(timezone.utc)
    mock_branch_dev = MagicMock()
    mock_branch_dev.commit.sha = "sha123"
    mock_branch_dev.commit.commit.author.date = datetime.now(timezone.utc)

    def get_branch_side_effect(val):
        if val == "main":
            return mock_branch_main
        if val == "dev":
            return mock_branch_dev
        raise Exception("Not found")

    mock_repo_a.get_branch.side_effect = get_branch_side_effect

    mock_comp = MagicMock()
    mock_comp.ahead_by = 2
    mock_comp.behind_by = 0
    mock_comp.status = "ahead"
    mock_repo_a.compare.return_value = mock_comp
    mock_client.get_repo.return_value = mock_repo_a

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_vaulted_fallback(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource(
            "pkg-a", {"git": "https://github.com/org/repoa", "branch": "main"}
        ),
    }
    uv_source_mock = PackageSource(
        "pkg-a", {"git": "https://github.com/org/repoa", "branch": "dev"}
    )
    mock_proj.uv_sources = {
        "pkg-a": uv_source_mock,
    }

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_repo_a = MagicMock()

    # Fail the github API call to force fallback for vaulted_sha (dev)
    mock_branch_a = MagicMock()
    mock_branch_a.commit.commit.author.date = datetime.now(timezone.utc)
    mock_branch_a.commit.sha = "main-sha"

    def get_branch_side_effect(name):
        if name == "main":
            return mock_branch_a
        raise Exception("API failure")

    mock_repo_a.get_branch.side_effect = get_branch_side_effect
    mock_client.get_repo.return_value = mock_repo_a

    with patch.object(uv_source_mock, "get_vcs") as mock_get_vcs:
        mock_vcs = MagicMock()
        mock_vcs.get_remote_sha.side_effect = Exception("Fallback also fails")
        mock_get_vcs.return_value = mock_vcs

        cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
        assert cmd.run() == 0
        mock_vcs.get_remote_sha.assert_called_once()


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_no_origin_url(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    # A package with no "git" property
    mock_proj.uvault_sources = {
        "pkg-a": PackageSource("pkg-a", {"path": "./local"}),
    }

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "UNKNOWN" in captured.out


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_github_api_failure(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-fail": PackageSource(
            "pkg-fail", {"git": "https://github.com/org/repoa", "branch": "main"}
        ),
    }
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_repo = MagicMock()
    # Force _fetch_github_metadata to fail (by failing get_branch) so remote_sha is None
    mock_repo.get_branch.side_effect = Exception("API failure")
    mock_client.get_repo.return_value = mock_repo

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0
    captured = capsys.readouterr()
    assert "UNKNOWN" in captured.out


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_parse_ref_type_exceptions(mock_pyproject, mock_get_client, capsys):
    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-invalid": PackageSource(
            "pkg-invalid", {"git": "https://github.com/org/repoa"}
        ),
        "pkg-none": PackageSource("pkg-none", {"git": "https://github.com/org/repob"}),
    }
    mock_proj.uv_sources = {}

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    with patch.object(PackageSource, "get_git_reference") as mock_get_ref:

        def side_effect():
            if mock_get_ref.call_count == 1:
                mock_ref = MagicMock()
                mock_ref.ref_type = "INVALID_TYPE"
                mock_ref.value = "val"
                return mock_ref
            return None

        mock_get_ref.side_effect = side_effect

        cmd = StatusCommand(
            packages=["pkg-invalid", "pkg-none"], format_type="list", sort_by="name"
        )
        assert cmd.run() == 0


@patch("uvault.github.GitHubForge._get_client")
@patch("uvault.status.PyProject")
def test_status_uv_source_none(mock_pyproject, mock_get_client, capsys):
    from datetime import datetime, timezone

    mock_proj = mock_pyproject.return_value
    mock_proj.uvault_sources = {
        "pkg-no-uv": PackageSource(
            "pkg-no-uv", {"git": "https://github.com/org/repoc", "branch": "main"}
        ),
    }
    mock_proj.uv_sources = {}

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_repo = MagicMock()
    mock_branch = MagicMock()
    mock_branch.commit.commit.author.date = datetime.now(timezone.utc)
    mock_branch.commit.sha = "main-sha"
    mock_repo.get_branch.return_value = mock_branch
    mock_client.get_repo.return_value = mock_repo

    cmd = StatusCommand(packages=None, format_type="list", sort_by="name")
    assert cmd.run() == 0
