import argparse
import sys
from uvault.sync import SyncCommand


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

    args = parser.parse_args(argv)

    if args.command == "sync":
        cmd = SyncCommand(packages=args.package, update=args.update)
        return cmd.run()

    return 0  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
