"""Parse TickTick API responses into TaskTree models."""

from typing import Optional

from .models import Priority, Task, TaskKind, TaskStatus, TaskTree
from .parser import parse_datetime


def _parse_api_priority(value: int) -> Priority:
    """Map API priority values to Priority enum.

    API uses: 0=none, 1=low, 3=medium, 5=high (same scale as CSV).
    """
    if value >= 5:
        return Priority.HIGH
    elif value >= 3:
        return Priority.MEDIUM
    elif value >= 1:
        return Priority.LOW
    return Priority.NONE


def _parse_api_status(value: int) -> TaskStatus:
    """Map API status values to TaskStatus enum.

    API uses: 0=normal, 2=completed.
    Note: API status 2 means completed (different from CSV where 2=archived).
    The API does not expose an archived status.
    """
    if value == 2:
        return TaskStatus.COMPLETED
    return TaskStatus.NORMAL


def _parse_api_kind(task_data: dict) -> tuple[TaskKind, bool]:
    """Determine task kind and checklist status from API data.

    Returns:
        Tuple of (TaskKind, is_checklist)
    """
    kind = task_data.get("kind", "TEXT")
    items = task_data.get("items", [])

    if kind == "NOTE":
        return TaskKind.NOTE, False
    if kind == "CHECKLIST" or items:
        return TaskKind.CHECKLIST, True

    return TaskKind.TEXT, False


def _format_checklist_items(items: list[dict]) -> str:
    """Convert API checklist items to markdown-format content.

    API items have: title, status (0=unchecked, 2=checked), sortOrder
    """
    if not items:
        return ""

    sorted_items = sorted(items, key=lambda x: x.get("sortOrder", 0))
    lines = []
    for item in sorted_items:
        title = item.get("title", "").strip()
        if not title:
            continue
        status = item.get("status", 0)
        marker = "▪" if status == 2 else "▫"
        lines.append(f"{marker}{title}")

    return "".join(lines)


def _build_project_lookup(projects: list[dict]) -> dict[str, dict]:
    """Build lookup dicts from project list.

    Returns:
        Dict mapping project_id -> project data
    """
    return {p["id"]: p for p in projects}


def _resolve_folder_name(project: dict, projects: list[dict]) -> str:
    """Resolve folder name for a project.

    Uses groupId to find the project group, which acts as the folder.
    Falls back to _Uncategorized if no group is found.
    """
    group_id = project.get("groupId")
    if not group_id:
        return "_Uncategorized"

    # Look for a project group with matching id
    # In the TickTick API, project groups are returned alongside projects
    # with an "isGroup" or similar flag, or via the groupId field.
    # The groupId maps to another project's id that acts as a folder.
    for p in projects:
        if p.get("id") == group_id:
            return p.get("name", "_Uncategorized")

    return "_Uncategorized"


def parse_api_response(
    projects: list[dict],
    tasks_by_project: dict[str, list[dict]],
) -> TaskTree:
    """Parse API response data into a TaskTree.

    Args:
        projects: List of project dicts from API
        tasks_by_project: Dict mapping project_id -> list of task dicts

    Returns:
        TaskTree with all parsed tasks
    """
    tree = TaskTree()
    project_lookup = _build_project_lookup(projects)

    for project_id, tasks in tasks_by_project.items():
        project = project_lookup.get(project_id, {})
        list_name = project.get("name", "_Uncategorized")
        folder_name = _resolve_folder_name(project, projects)

        for task_data in tasks:
            try:
                task = _parse_task(task_data, folder_name, list_name)
                tree.add_task(task)
            except Exception as e:
                title = task_data.get("title", "unknown")
                print(f"Warning: Failed to parse API task '{title}': {e}")

    tree.build_subtask_relationships()
    return tree


def _parse_task(task_data: dict, folder_name: str, list_name: str) -> Task:
    """Parse a single API task dict into a Task model."""
    kind, is_checklist = _parse_api_kind(task_data)

    # Build content from either content field or checklist items
    content = task_data.get("content", "") or ""
    items = task_data.get("items", [])
    if items:
        checklist_content = _format_checklist_items(items)
        if checklist_content:
            content = checklist_content

    # Tags come as a list from the API (vs comma-separated in CSV)
    tags = task_data.get("tags", []) or []

    return Task(
        folder_name=folder_name,
        list_name=list_name,
        title=task_data.get("title", "").strip(),
        kind=kind,
        tags=tags,
        content=content,
        is_checklist=is_checklist,
        start_date=parse_datetime(task_data.get("startDate", "") or ""),
        due_date=parse_datetime(task_data.get("dueDate", "") or ""),
        reminder="",
        repeat=task_data.get("repeatFlag", "") or "",
        priority=_parse_api_priority(task_data.get("priority", 0)),
        status=_parse_api_status(task_data.get("status", 0)),
        created_time=parse_datetime(task_data.get("createdTime", "") or ""),
        completed_time=parse_datetime(task_data.get("completedTime", "") or ""),
        order=task_data.get("sortOrder", 0) or 0,
        timezone=task_data.get("timeZone", "") or "",
        is_all_day=task_data.get("isAllDay", False),
        is_floating=task_data.get("isFloating", False),
        column_name="",
        column_order=-1,
        view_mode="",
        task_id=task_data.get("id", ""),
        parent_id=task_data.get("parentId", "") or "",
    )
