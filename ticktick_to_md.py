#!/usr/bin/env python3
"""
TickTick to Markdown Converter

Converts TickTick CSV backup exports into a structured hierarchy of markdown files.

Usage:
    python ticktick_to_md.py backup.csv -o output/
    python ticktick_to_md.py backup.csv -o output/ --flat
    python ticktick_to_md.py backup.csv -o output/all.md --single-file
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Convert TickTick CSV backup to markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s backup.csv -o output/
      Convert to hierarchical folder structure

  %(prog)s backup.csv -o output/ --flat
      Convert to flat directory (all files in one folder)

  %(prog)s backup.csv -o output/ --include-archived
      Include archived tasks

  %(prog)s backup.csv -o all_tasks.md --single-file
      Convert to single markdown file
        """,
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Path to TickTick CSV backup file",
    )

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

    args = parser.parse_args()

    # Validate input file
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.input.suffix.lower() == ".csv":
        print(f"Warning: Input file doesn't have .csv extension", file=sys.stderr)

    # Import here to avoid slow startup for --help
    from parser import parse_csv
    from writer import MarkdownWriter, write_single_file

    # Parse CSV
    if args.verbose:
        print(f"Parsing {args.input}...")

    try:
        tree = parse_csv(args.input)
    except Exception as e:
        print(f"Error parsing CSV: {e}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Parsed {len(tree.all_tasks)} tasks in {len(tree.folders)} folders")

    # Write output
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
                # Handle encoding issues with emojis on Windows
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


if __name__ == "__main__":
    main()
