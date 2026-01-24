"""File writer for markdown output."""

import re
from pathlib import Path
from typing import Optional

from generator import generate_list_index, generate_markdown
from models import Task, TaskTree


# Characters not allowed in filenames on Windows/Mac/Linux
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
MAX_FILENAME_LENGTH = 100


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename.

    Args:
        name: The original name

    Returns:
        A safe filename
    """
    if not name:
        return "_unnamed"

    # Replace invalid characters with dash
    safe = re.sub(INVALID_FILENAME_CHARS, "-", name)

    # Replace multiple dashes with single dash
    safe = re.sub(r"-+", "-", safe)

    # Remove leading/trailing dashes and spaces
    safe = safe.strip("- ")

    # Truncate if too long
    if len(safe) > MAX_FILENAME_LENGTH:
        safe = safe[:MAX_FILENAME_LENGTH].rstrip("- ")

    # Ensure we have something
    if not safe:
        return "_unnamed"

    return safe


def get_unique_path(path: Path) -> Path:
    """Get a unique file path by adding a number suffix if needed.

    Args:
        path: The desired path

    Returns:
        A path that doesn't exist (original or with number suffix)
    """
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    counter = 2
    while True:
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path
        counter += 1
        if counter > 1000:  # Safety limit
            raise RuntimeError(f"Too many files with name: {stem}")


class MarkdownWriter:
    """Writes tasks to markdown files in a directory structure."""

    def __init__(
        self,
        output_dir: Path,
        flat: bool = False,
        include_archived: bool = False,
        include_index: bool = True,
    ):
        """Initialize the writer.

        Args:
            output_dir: Root output directory
            flat: If True, write all files to single directory
            include_archived: If True, include archived tasks
            include_index: If True, generate index files for lists
        """
        self.output_dir = Path(output_dir)
        self.flat = flat
        self.include_archived = include_archived
        self.include_index = include_index
        self.files_written = 0
        self.files_skipped = 0

    def write_task(self, task: Task, base_dir: Path) -> Optional[Path]:
        """Write a single task to a markdown file.

        Args:
            task: The task to write
            base_dir: Directory to write to

        Returns:
            Path to written file, or None if skipped
        """
        # Skip archived tasks unless requested
        if task.is_archived and not self.include_archived:
            self.files_skipped += 1
            return None

        # Skip subtasks (they're included in parent)
        if task.has_parent:
            return None

        # Generate filename
        filename = sanitize_filename(task.title) + ".md"
        file_path = get_unique_path(base_dir / filename)

        # Generate content
        content = generate_markdown(task)

        # Write file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        self.files_written += 1

        return file_path

    def write_list_index(
        self, list_name: str, folder_name: str, tasks: list[Task], base_dir: Path
    ) -> Optional[Path]:
        """Write an index file for a list.

        Args:
            list_name: Name of the list
            folder_name: Name of the folder
            tasks: Tasks in the list
            base_dir: Directory to write to

        Returns:
            Path to written file
        """
        if not self.include_index:
            return None

        file_path = base_dir / "_index.md"
        content = generate_list_index(list_name, folder_name, tasks)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return file_path

    def write_tree(self, tree: TaskTree) -> dict:
        """Write all tasks from a TaskTree.

        Args:
            tree: The parsed task tree

        Returns:
            Statistics dict with counts
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.flat:
            # Write all tasks to single directory
            for task in tree.all_tasks.values():
                self.write_task(task, self.output_dir)
        else:
            # Write in hierarchy: folder/list/task.md
            for folder_name, folder in tree.folders.items():
                folder_dir = self.output_dir / sanitize_filename(folder_name)

                for list_name, task_list in folder.lists.items():
                    list_dir = folder_dir / sanitize_filename(list_name)

                    # Write tasks
                    for task in task_list.tasks:
                        self.write_task(task, list_dir)

                    # Write list index
                    self.write_list_index(
                        list_name, folder_name, task_list.tasks, list_dir
                    )

        return {
            "files_written": self.files_written,
            "files_skipped": self.files_skipped,
            "total_tasks": len(tree.all_tasks),
        }


def write_single_file(tree: TaskTree, output_path: Path, include_archived: bool = False) -> int:
    """Write all tasks to a single markdown file.

    Args:
        tree: The parsed task tree
        output_path: Path to output file
        include_archived: Whether to include archived tasks

    Returns:
        Number of tasks written
    """
    sections = []
    count = 0

    sections.append("# TickTick Backup")
    sections.append("")

    for folder_name, folder in sorted(tree.folders.items()):
        sections.append(f"## {folder_name}")
        sections.append("")

        for list_name, task_list in sorted(folder.lists.items()):
            sections.append(f"### {list_name}")
            sections.append("")

            # Sort tasks by order
            sorted_tasks = sorted(task_list.tasks, key=lambda t: t.order)

            for task in sorted_tasks:
                # Skip archived unless requested
                if task.is_archived and not include_archived:
                    continue

                # Skip subtasks (handled with parent)
                if task.has_parent:
                    continue

                checkbox = "[x]" if task.is_completed else "[ ]"
                sections.append(f"- {checkbox} **{task.title}**")

                if task.content:
                    # Indent content
                    from generator import convert_content_to_markdown
                    content = convert_content_to_markdown(task.content, task.is_checklist)
                    for line in content.split("\n"):
                        if line.strip():
                            sections.append(f"  {line}")

                # Add subtasks
                for subtask in sorted(task.subtasks, key=lambda t: t.order):
                    sub_checkbox = "[x]" if subtask.is_completed else "[ ]"
                    sections.append(f"  - {sub_checkbox} {subtask.title}")

                sections.append("")
                count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(sections), encoding="utf-8")

    return count
