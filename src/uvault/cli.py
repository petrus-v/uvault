import argparse
import sys
from uvault.sync import SyncCommand
from uvault.develop import DevelopCommand
from uvault.add import AddCommand


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]  # pragma: no cover

    parser = argparse.ArgumentParser(
        description="Development and vaulting workflow for uv VCS dependencies."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync and vault VCS dependencies.")
    sync_parser.add_argument(
        "-U",
        "--update",
        action="store_true",
        help="Force update the vaulted reference.",
    )
    sync_parser.add_argument(
        "-P",
        "--package",
        action="append",
        help="Specific package to sync. Can be used multiple times.",
    )

    sync_parser.add_argument(
        "--delete-extra",
        action="store_true",
        help="Delete references in uv.sources that are not in uvault.sources.",
    )
    sync_parser.add_argument(
        "--keep-develop",
        action="store_true",
        help="Keep packages that are in local develop mode instead of restoring them.",
    )

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new vaulting intention.")
    add_parser.add_argument("package", help="The package to add")
    add_parser.add_argument("url", nargs="?", help="The VCS URL or PEP 508 string")
    add_parser.add_argument("--pr", help="Pull request number")
    add_parser.add_argument("--branch", help="Branch name")
    add_parser.add_argument("--tag", help="Tag name")
    add_parser.add_argument("--rev", help="Revision SHA")
    add_parser.add_argument("--subdirectory", help="Subdirectory in the repository")

    # Develop command
    dev_parser = subparsers.add_parser("develop", help="Develop a package locally.")
    dev_parser.add_argument("package", help="The package to develop")
    dev_parser.add_argument("branch", help="Branch name to checkout or create")

    # Release command
    release_parser = subparsers.add_parser(
        "release",
        help="Update tags in uv.sources with the current project version, keeping the same commit references.",
    )
    release_parser.add_argument(
        "-P",
        "--package",
        action="append",
        help="Apply the release tag only to the specified vaulted package. Can be used multiple times.",
    )
    release_parser.add_argument(
        "--keep-develop",
        action="store_true",
        help="Keep packages that are in local develop mode instead of restoring them.",
    )

    args = parser.parse_args(argv)

    if args.command == "sync":
        cmd = SyncCommand(
            packages=args.package,
            update=args.update,
            delete_extra=args.delete_extra,
            keep_develop=args.keep_develop,
        )
        return cmd.run()
    elif args.command == "release":
        cmd = SyncCommand(
            packages=args.package,
            update=False,
            delete_extra=False,
            keep_develop=args.keep_develop,
            release=True,
        )
        return cmd.run()
    elif args.command == "develop":
        cmd = DevelopCommand(package=args.package, branch=args.branch)
        return cmd.run()
    elif args.command == "add":
        cmd = AddCommand(
            package=args.package,
            url=args.url,
            pr=args.pr,
            branch=args.branch,
            tag=args.tag,
            rev=args.rev,
            subdirectory=args.subdirectory,
        )
        return cmd.run()

    return 0  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
