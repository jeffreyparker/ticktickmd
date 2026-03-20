#!/usr/bin/env python3
"""
TickTick to Markdown Converter

Converts TickTick tasks into structured markdown files.
Supports CSV backup files and the TickTick Open API.

Usage:
    ticktickmd csv backup.csv -o output/
    ticktickmd api -o output/
    ticktickmd auth login
"""

import argparse
import sys
from pathlib import Path


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    """Add shared output arguments to a subcommand parser."""
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output directory (or file path with --single-file)",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Write all files to a single directory instead of hierarchy",
    )
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="Write all tasks to a single markdown file",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived tasks in output",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Don't generate index files for lists",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed progress",
    )


def _write_output(tree, args) -> None:
    """Write a TaskTree to output using the shared output args."""
    from .writer import MarkdownWriter, write_single_file

    if args.single_file:
        if args.verbose:
            print(f"Writing single file to {args.output}...")

        count = write_single_file(tree, args.output, args.include_archived)
        print(f"Wrote {count} tasks to {args.output}")
    else:
        if args.verbose:
            print(f"Writing to {args.output}...")

        writer = MarkdownWriter(
            output_dir=args.output,
            flat=args.flat,
            include_archived=args.include_archived,
            include_index=not args.no_index,
        )

        stats = writer.write_tree(tree)

        print(f"Done! Wrote {stats['files_written']} files")
        if stats["files_skipped"] > 0:
            print(f"  (skipped {stats['files_skipped']} archived tasks)")

        if args.verbose:
            print(f"\nOutput structure:")
            for folder_name in sorted(tree.folders.keys()):
                folder = tree.folders[folder_name]
                try:
                    print(f"  {folder_name}/")
                except UnicodeEncodeError:
                    print(f"  {folder_name.encode('ascii', 'replace').decode()}/")
                for list_name in sorted(folder.lists.keys()):
                    task_count = len(folder.lists[list_name].tasks)
                    try:
                        print(f"    {list_name}/ ({task_count} tasks)")
                    except UnicodeEncodeError:
                        print(f"    {list_name.encode('ascii', 'replace').decode()}/ ({task_count} tasks)")


def _cmd_csv(args) -> None:
    """Handle the csv subcommand."""
    from .parser import parse_csv

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.input.suffix.lower() == ".csv":
        print("Warning: Input file doesn't have .csv extension", file=sys.stderr)

    if args.verbose:
        print(f"Parsing {args.input}...")

    try:
        tree = parse_csv(args.input)
    except Exception as e:
        print(f"Error parsing CSV: {e}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Parsed {len(tree.all_tasks)} tasks in {len(tree.folders)} folders")

    _write_output(tree, args)


def _cmd_api(args) -> None:
    """Handle the api subcommand."""
    try:
        import httpx  # noqa: F401
    except ImportError:
        print(
            "Error: The 'api' command requires httpx. Install with:\n"
            "  pip install ticktickmd[api]",
            file=sys.stderr,
        )
        sys.exit(1)

    from .auth import get_access_token
    from .api import TickTickClient
    from .api_parser import parse_api_response
    from .exceptions import AuthError, TickTickError

    try:
        access_token = get_access_token()
    except AuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print("Fetching tasks from TickTick API...")

    try:
        with TickTickClient(access_token, verbose=args.verbose) as client:
            projects, tasks_by_project = client.fetch_all_tasks(
                project_filter=args.project
            )
    except TickTickError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    tree = parse_api_response(projects, tasks_by_project)

    if args.verbose:
        print(f"Fetched {len(tree.all_tasks)} tasks in {len(tree.folders)} folders")

    _write_output(tree, args)


def _cmd_auth(args) -> None:
    """Handle the auth subcommand."""
    from .auth import handle_auth_command

    handle_auth_command(args.action)


def main():
    parser = argparse.ArgumentParser(
        description="Convert TickTick tasks to markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s csv backup.csv -o output/
      Convert CSV backup to hierarchical folder structure

  %(prog)s csv backup.csv -o output/ --flat
      Convert to flat directory (all files in one folder)

  %(prog)s api -o output/
      Fetch from TickTick API and convert

  %(prog)s api -o output/ --project "Work"
      Fetch only tasks from the "Work" project

  %(prog)s auth login
      Set up TickTick API authentication
        """,
    )

    subparsers = parser.add_subparsers(dest="command")

    # csv subcommand
    csv_parser = subparsers.add_parser(
        "csv",
        help="Convert a TickTick CSV backup file",
        description="Convert a TickTick CSV backup file to markdown",
    )
    csv_parser.add_argument(
        "input",
        type=Path,
        help="Path to TickTick CSV backup file",
    )
    _add_output_args(csv_parser)

    # api subcommand
    api_parser = subparsers.add_parser(
        "api",
        help="Fetch tasks from TickTick API",
        description="Fetch tasks from the TickTick Open API and convert to markdown",
    )
    _add_output_args(api_parser)
    api_parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Only fetch tasks from this project (case-insensitive)",
    )

    # auth subcommand
    auth_parser = subparsers.add_parser(
        "auth",
        help="Manage TickTick API authentication",
        description="Manage OAuth tokens for the TickTick API",
    )
    auth_parser.add_argument(
        "action",
        choices=["login", "status", "logout"],
        help="Auth action: login, status, or logout",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "csv":
        _cmd_csv(args)
    elif args.command == "api":
        _cmd_api(args)
    elif args.command == "auth":
        _cmd_auth(args)


if __name__ == "__main__":
    main()
