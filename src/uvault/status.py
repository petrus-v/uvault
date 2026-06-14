import datetime

from dataclasses import dataclass
from enum import StrEnum

from uvault.project import PyProject
from uvault.source import PackageSource
from uvault.vcs import RefType


class PullRequestStatus(StrEnum):
    MERGED = "MERGED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ACTIVE = "ACTIVE"
    UNKNOWN = "UNKNOWN"


@dataclass
class PackageStatus:
    name: str
    source_url: str
    ref_type: RefType
    ref_value: str
    status: PullRequestStatus
    behind: int
    diverged: bool
    labels: list[str]
    last_activity: datetime.datetime | None


class StatusCommand:
    def __init__(self, packages: list[str] | None, format_type: str, sort_by: str):
        self.packages = packages
        self.format_type = format_type
        self.sort_by = sort_by
        self.project = PyProject("pyproject.toml")

    def run(self) -> int:
        self.project.read()
        uvault_sources = self.project.uvault_sources

        if self.packages:
            packages_to_check = {
                k: v for k, v in uvault_sources.items() if k in self.packages
            }
        else:
            packages_to_check = uvault_sources

        package_statuses = []
        for pkg, source in packages_to_check.items():
            package_status = self._check_package(pkg, source)
            package_statuses.append(package_status)

        # Sorting
        if self.sort_by == "status":
            package_statuses.sort(key=lambda x: (x.status, x.name))
        elif self.sort_by == "date":
            # descending activity
            package_statuses.sort(
                key=lambda x: (
                    x.last_activity
                    or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
                    x.name,
                ),
                reverse=True,
            )
        else:
            package_statuses.sort(key=lambda x: x.name)

        if self.format_type == "inline":
            self._print_inline(package_statuses)
        elif self.format_type == "table":
            self._print_table(package_statuses)
        else:
            self._print_list(package_statuses)

        return 0

    def _calculate_divergence(
        self,
        forge,
        pkg_status: PackageStatus,
        remote_sha: str | None,
        uv_source: PackageSource,
    ):
        if not remote_sha:
            return

        vaulted_ref = uv_source.get_git_reference()
        if not vaulted_ref:
            return

        vaulted_sha = None
        if vaulted_ref.ref_type == RefType.REV:
            vaulted_sha = vaulted_ref.value
        elif forge:
            vaulted_sha = forge.get_remote_sha(vaulted_ref.ref_type, vaulted_ref.value)

        if not vaulted_sha:
            # Fallback to ls-remote if API fails or is not available
            try:
                vcs = uv_source.get_vcs()
                if uv_source.origin_url:
                    vaulted_sha = vcs.get_remote_sha(uv_source.origin_url, vaulted_ref)
            except Exception:
                pass

        if vaulted_sha and vaulted_sha != remote_sha:
            if forge:
                divergence = forge.get_divergence(vaulted_sha, remote_sha)
                if divergence:
                    behind, diverged = divergence
                    pkg_status.behind = behind
                    pkg_status.diverged = diverged

    def _check_package(self, pkg: str, source: PackageSource) -> PackageStatus:
        origin_url = source.origin_url
        if not origin_url:
            return PackageStatus(
                pkg,
                "None",
                RefType.UNKNOWN,
                "",
                PullRequestStatus.UNKNOWN,
                0,
                False,
                [],
                None,
            )

        git_ref = source.get_git_reference()
        ref_type = git_ref.ref_type if git_ref else RefType.UNKNOWN
        ref_value = git_ref.value if git_ref else ""

        forge = source.get_forge()
        path = forge.path if hasattr(forge, "path") else None

        pkg_status = PackageStatus(
            name=pkg,
            source_url=path or origin_url,
            ref_type=ref_type,
            ref_value=ref_value,
            status=PullRequestStatus.UNKNOWN,
            behind=0,
            diverged=False,
            labels=[],
            last_activity=None,
        )

        if forge:
            ignore_labels = self.project.tool_uvault.get(
                "ignore_labels", ["mod:", "series:"]
            )
            remote_sha = forge.enrich_package_status(pkg_status, ignore_labels)
            uv_source = self.project.uv_sources.get(pkg_status.name)
            if uv_source:
                self._calculate_divergence(forge, pkg_status, remote_sha, uv_source)

        return pkg_status

    def _print_inline(self, results: list[PackageStatus]):
        print("VCS Metadata:")
        max_pkg_len = max([len(r.name) for r in results]) if results else 0
        max_pkg_len = min(max_pkg_len, 50)  # cap at 50

        for res in results:
            color = self._get_status_color(res.status)
            labels_str = f", labels: {','.join(res.labels)}" if res.labels else ""
            diverged_str = " (Force-Push detecté!)" if res.diverged else ""
            behind_str = (
                f", +{res.behind} commits{diverged_str}"
                if res.behind or res.diverged
                else ", à jour"
            )
            pkg_name = (
                res.name
                if len(res.name) <= max_pkg_len
                else res.name[: max_pkg_len - 2] + ".."
            )
            print(
                f"  {color} [{res.status:<6}] {pkg_name:<{max_pkg_len}} ({res.ref_type} {res.ref_value}{behind_str}{labels_str})"
            )

    def _print_list(self, results: list[PackageStatus]):
        for i, res in enumerate(results):
            color = self._get_status_color(res.status)
            if i > 0:
                print()
            print(f"📦 {res.name} ({res.source_url})")
            print(f"   ├─ Type   : {res.ref_type} {res.ref_value}")
            print(f"   ├─ Statut : {color} {res.status}")

            if res.diverged:
                behind_str = f"⚠️ {res.behind} nouveaux commits (Force-Push detecté!)"
            elif res.behind:
                behind_str = f"⚠️ {res.behind} nouveaux commits distants"
            else:
                behind_str = "à jour"

            date_str = self._format_date(res.last_activity)
            labels_str = f" | labels: {','.join(res.labels)}" if res.labels else ""
            print(
                f"   └─ Update : {behind_str} (dernière activité {date_str}){labels_str}"
            )

    def _print_table(self, results: list[PackageStatus]):
        print(
            f"{'Package':<45} {'Source':<25} {'Status':<8} {'Behind':<8} {'Last Activity':<15} {'Labels'}"
        )
        print("-" * 115)
        for res in results:
            labels_str = ",".join(res.labels) if res.labels else "-"
            behind_str = f"+{res.behind}" if res.behind else "0"
            if res.diverged:
                behind_str += " (FP!)"
            date_str = self._format_date(res.last_activity)
            source_str = f"{res.source_url}#{res.ref_value}"
            if len(source_str) > 23:
                source_str = source_str[:20] + "..."
            pkg_name = res.name if len(res.name) <= 44 else res.name[:42] + ".."
            print(
                f"{pkg_name:<45} {source_str:<25} [{res.status:<6}] {behind_str:<8} {date_str:<15} {labels_str}"
            )

    def _get_status_color(self, status: PullRequestStatus | str) -> str:
        if status == PullRequestStatus.MERGED:
            return "🟢"
        if status == PullRequestStatus.OPEN:
            return "🟡"
        if status == PullRequestStatus.CLOSED:
            return "🔴"
        if status == PullRequestStatus.ACTIVE:
            return "🔵"
        return "⚪"

    def _format_date(self, dt: datetime.datetime | None) -> str:
        if not dt:
            return "inconnue"
        now = datetime.datetime.now(datetime.timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)

        diff = now - dt
        if diff.days > 365:
            return f"il y a {diff.days // 365} an(s)"
        if diff.days > 30:
            return f"il y a {diff.days // 30} mois"
        if diff.days > 0:
            return f"il y a {diff.days} jour(s)"
        return "aujourd'hui"
