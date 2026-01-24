"""CSV parser for TickTick backup files."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Priority, Task, TaskKind, TaskStatus, TaskTree


def parse_datetime(value: str) -> Optional[datetime]:
    """Parse TickTick datetime format."""
    if not value or not value.strip():
        return None
    try:
        # Format: 2025-12-27T03:57:34+0000
        return datetime.strptime(value.strip(), "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        try:
            # Try without timezone
            return datetime.strptime(value.strip(), "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None


def parse_bool(value: str) -> bool:
    """Parse boolean fields."""
    return value.strip().upper() in ("Y", "TRUE", "1", "YES")


def parse_int(value: str, default: int = 0) -> int:
    """Parse integer fields."""
    try:
        return int(value.strip()) if value.strip() else default
    except ValueError:
        return default


def parse_status(value: str) -> TaskStatus:
    """Parse status field."""
    status_val = parse_int(value, 0)
    try:
        return TaskStatus(status_val)
    except ValueError:
        return TaskStatus.NORMAL


def parse_priority(value: str) -> Priority:
    """Parse priority field."""
    priority_val = parse_int(value, 0)
    if priority_val >= 5:
        return Priority.HIGH
    elif priority_val >= 3:
        return Priority.MEDIUM
    elif priority_val >= 1:
        return Priority.LOW
    return Priority.NONE


def parse_kind(value: str) -> TaskKind:
    """Parse task kind field."""
    value = value.strip().upper()
    try:
        return TaskKind(value)
    except ValueError:
        return TaskKind.TEXT


def parse_tags(value: str) -> list[str]:
    """Parse tags field (comma-separated)."""
    if not value or not value.strip():
        return []
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def parse_csv(file_path: Path) -> TaskTree:
    """Parse a TickTick CSV backup file.

    Args:
        file_path: Path to the CSV file

    Returns:
        TaskTree with all parsed tasks
    """
    import io

    tree = TaskTree()

    # Open with newline='' to preserve \r characters in CSV fields
    with open(file_path, "r", encoding="utf-8-sig", newline='') as f:
        # Read entire file content
        content = f.read()

        # Find header position
        header_pos = content.find('"Folder Name"')
        if header_pos == -1:
            raise ValueError("Could not find CSV header row")

        # Parse CSV from header onwards using StringIO
        # This preserves \r characters within fields
        csv_data = io.StringIO(content[header_pos:])
        reader = csv.DictReader(csv_data)

        for row in reader:
            try:
                task = Task(
                    folder_name=row.get("Folder Name", "").strip(),
                    list_name=row.get("List Name", "").strip(),
                    title=row.get("Title", "").strip(),
                    kind=parse_kind(row.get("Kind", "TEXT")),
                    tags=parse_tags(row.get("Tags", "")),
                    content=row.get("Content", ""),
                    is_checklist=parse_bool(row.get("Is Check list", "N")),
                    start_date=parse_datetime(row.get("Start Date", "")),
                    due_date=parse_datetime(row.get("Due Date", "")),
                    reminder=row.get("Reminder", "").strip(),
                    repeat=row.get("Repeat", "").strip(),
                    priority=parse_priority(row.get("Priority", "0")),
                    status=parse_status(row.get("Status", "0")),
                    created_time=parse_datetime(row.get("Created Time", "")),
                    completed_time=parse_datetime(row.get("Completed Time", "")),
                    order=parse_int(row.get("Order", "0")),
                    timezone=row.get("Timezone", "").strip(),
                    is_all_day=parse_bool(row.get("Is All Day", "")),
                    is_floating=parse_bool(row.get("Is Floating", "")),
                    column_name=row.get("Column Name", "").strip(),
                    column_order=parse_int(row.get("Column Order", "-1"), -1),
                    view_mode=row.get("View Mode", "").strip(),
                    task_id=row.get("taskId", "").strip(),
                    parent_id=row.get("parentId", "").strip(),
                )
                tree.add_task(task)
            except Exception as e:
                # Log but continue on parse errors
                title = row.get("Title", "unknown")
                print(f"Warning: Failed to parse task '{title}': {e}")

    # Build parent-child relationships
    tree.build_subtask_relationships()

    return tree


if __name__ == "__main__":
    # Quick test
    import sys

    if len(sys.argv) > 1:
        tree = parse_csv(Path(sys.argv[1]))
        print(f"Parsed {len(tree.all_tasks)} tasks")
        print(f"Folders: {list(tree.folders.keys())}")
        for folder_name, folder in tree.folders.items():
            print(f"  {folder_name}: {list(folder.lists.keys())}")
