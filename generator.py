"""Markdown generator for TickTick tasks."""

import re
from datetime import datetime
from typing import Optional

from models import Task, TaskKind


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for YAML frontmatter."""
    if dt is None:
        return ""
    return dt.isoformat()


def format_date(dt: Optional[datetime]) -> str:
    """Format date only for display."""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d")


def escape_yaml_string(s: str) -> str:
    """Escape a string for YAML frontmatter."""
    if not s:
        return '""'
    # If contains special chars, wrap in quotes
    if any(c in s for c in ':"\'[]{}#&*!|>%@`'):
        # Escape internal quotes
        s = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{s}"'
    if s.strip() != s or not s:
        return f'"{s}"'
    return s


def convert_checklist_content(content: str) -> str:
    """Convert TickTick checklist format to markdown checkboxes.

    TickTick uses:
    - ▫ (U+25AB, WHITE SMALL SQUARE) for unchecked
    - ▪ (U+25AA, BLACK SMALL SQUARE) for checked

    Items are separated by these markers with no newlines between them.
    """
    if not content:
        return ""

    # Split on checklist markers, keeping the marker
    # Pattern: split just before ▫ or ▪
    parts = re.split(r"(▫|▪)", content)

    lines = []
    current_marker = None

    for part in parts:
        if part == "▫":
            current_marker = "- [ ] "
        elif part == "▪":
            current_marker = "- [x] "
        elif part.strip() and current_marker:
            # Clean up the item text
            item_text = part.strip()
            if item_text:
                lines.append(f"{current_marker}{item_text}")
            current_marker = None
        elif part.strip() and not current_marker:
            # Text before any marker, or non-checklist content
            lines.append(part.strip())

    return "\n".join(lines)


def split_ticktick_list(content: str) -> list[str]:
    """Split TickTick concatenated list items.

    TickTick exports lists without newlines, e.g.:
    "- Item 1- Item 2- Item 3"

    We need to split on "- " that starts a new item.
    Heuristic: split when we see "- " preceded by non-space
    (meaning previous item ended and new one starts).
    """
    if not content or "- " not in content:
        return [content] if content else []

    # If content starts with "- ", it's a list
    if not content.strip().startswith("- "):
        return [content]

    # Split on pattern: word/punctuation followed by "- "
    # This catches "item1- item2" but not " - " in the middle of text
    parts = re.split(r"(?<=[^\s])- ", content)

    result = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue

        if i == 0:
            # First part might start with "- "
            if part.startswith("- "):
                result.append(part)
            else:
                result.append(f"- {part}")
        else:
            result.append(f"- {part}")

    return result


def split_concatenated_text(content: str) -> str:
    """Split TickTick's concatenated text into separate lines.

    TickTick concatenates sentences without spaces or newlines, e.g.:
    "Current Milage 23452Last service 2025-08-06"

    Split on patterns like:
    - digit + uppercase letter (e.g., "23452Last")
    - lowercase + uppercase (e.g., "milesHow")
    - punctuation + uppercase (e.g., "it.The")
    - question/exclamation + uppercase (e.g., "change?Kia")
    """
    if not content:
        return ""

    # Only apply smart splitting if we detect concatenated text
    # Look for patterns like "word123Word" or "wordWord"
    if not re.search(r'[a-z0-9][A-Z]', content):
        # No concatenation detected, return as-is
        return content

    result = content

    # Split on: digit followed by capital letter (e.g., "23452Last")
    result = re.sub(r'(\d)([A-Z])', r'\1\n\n\2', result)

    # Split on: lowercase followed by capital letter (e.g., "milesHow")
    # But preserve acronyms and common patterns
    result = re.sub(r'([a-z])([A-Z])', r'\1\n\n\2', result)

    # Split on: period/question/exclamation followed by capital (e.g., "it.The")
    result = re.sub(r'([.?!])([A-Z])', r'\1\n\n\2', result)

    # Clean up any triple+ newlines to double
    result = re.sub(r'\n{3,}', r'\n\n', result)

    return result.strip()


def convert_content_to_markdown(content: str, is_checklist: bool) -> str:
    """Convert task content to proper markdown.

    Handles:
    - Checklist symbols
    - Existing markdown (links, code blocks)
    - Line breaks (TickTick uses \\r carriage returns)
    - TickTick's concatenated list format
    """
    if not content:
        return ""

    # TickTick uses \r (carriage return) for line breaks in CSV export
    # Normalize all line endings to \n
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    if is_checklist or "▫" in content or "▪" in content:
        return convert_checklist_content(content)

    # Check if this looks like a concatenated list (starts with "- ")
    if content.strip().startswith("- "):
        items = split_ticktick_list(content)
        return "\n".join(items)

    # Handle regular text with newlines
    lines = content.split("\n")
    result_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped:
            result_lines.append(stripped)

    return "\n".join(result_lines)


def generate_frontmatter(task: Task) -> str:
    """Generate YAML frontmatter for a task."""
    lines = ["---"]

    lines.append(f"title: {escape_yaml_string(task.title)}")
    lines.append(f"folder: {escape_yaml_string(task.folder_name)}")
    lines.append(f"list: {escape_yaml_string(task.list_name)}")
    lines.append(f"kind: {escape_yaml_string(task.kind.value)}")

    # Tags as YAML array
    if task.tags:
        tags_str = ", ".join(escape_yaml_string(t) for t in task.tags)
        lines.append(f"tags: [{tags_str}]")
    else:
        lines.append("tags: []")

    lines.append(f"status: {escape_yaml_string(task.status_label)}")
    lines.append(f"priority: {escape_yaml_string(task.priority_label)}")

    # Dates
    if task.created_time:
        lines.append(f"created: {format_datetime(task.created_time)}")
    if task.completed_time:
        lines.append(f"completed: {format_datetime(task.completed_time)}")
    if task.due_date:
        lines.append(f"due: {format_date(task.due_date)}")
    if task.start_date:
        lines.append(f"start: {format_date(task.start_date)}")

    # Other metadata
    if task.reminder:
        lines.append(f"reminder: {escape_yaml_string(task.reminder)}")
    if task.repeat:
        lines.append(f"repeat: {escape_yaml_string(task.repeat)}")
    if task.timezone:
        lines.append(f"timezone: {escape_yaml_string(task.timezone)}")

    lines.append(f"ticktick_id: {escape_yaml_string(task.task_id)}")

    if task.parent_id:
        lines.append(f"parent_id: {escape_yaml_string(task.parent_id)}")

    lines.append("---")
    return "\n".join(lines)


def generate_subtasks_section(subtasks: list[Task], indent: int = 0) -> str:
    """Generate markdown for subtasks."""
    if not subtasks:
        return ""

    lines = []
    indent_str = "  " * indent

    for subtask in sorted(subtasks, key=lambda t: t.order):
        # Treat both completed and archived as done
        is_done = subtask.is_completed or subtask.is_archived
        checkbox = "[x]" if is_done else "[ ]"
        lines.append(f"{indent_str}- {checkbox} {subtask.title}")

        # Add subtask content if present
        if subtask.content:
            content = convert_content_to_markdown(subtask.content, subtask.is_checklist)
            if content:
                # Indent content under the subtask
                for content_line in content.split("\n"):
                    if content_line.strip():
                        lines.append(f"{indent_str}  {content_line}")

        # Recursively add nested subtasks
        if subtask.subtasks:
            nested = generate_subtasks_section(subtask.subtasks, indent + 1)
            if nested:
                lines.append(nested)

    return "\n".join(lines)


def generate_markdown(task: Task, include_frontmatter: bool = True) -> str:
    """Generate complete markdown for a task.

    Args:
        task: The task to convert
        include_frontmatter: Whether to include YAML frontmatter

    Returns:
        Complete markdown string
    """
    sections = []

    # Frontmatter
    if include_frontmatter:
        sections.append(generate_frontmatter(task))
        sections.append("")  # Blank line after frontmatter

    # Title as heading
    sections.append(f"# {task.title}")
    sections.append("")

    # Main content
    if task.content:
        content = convert_content_to_markdown(task.content, task.is_checklist)
        if content:
            sections.append(content)
            sections.append("")

    # Subtasks section
    if task.subtasks:
        sections.append("## Subtasks")
        sections.append("")
        sections.append(generate_subtasks_section(task.subtasks))
        sections.append("")

    # Metadata footer (optional, for quick reference)
    metadata_parts = []
    if task.due_date:
        metadata_parts.append(f"Due: {format_date(task.due_date)}")
    if task.priority.value > 0:
        metadata_parts.append(f"Priority: {task.priority_label}")
    if task.tags:
        metadata_parts.append(f"Tags: {', '.join(task.tags)}")

    if metadata_parts:
        sections.append("---")
        sections.append(" | ".join(metadata_parts))

    return "\n".join(sections).rstrip() + "\n"


def generate_list_index(list_name: str, folder_name: str, tasks: list[Task]) -> str:
    """Generate an index file for a list."""
    lines = [
        "---",
        f"title: {escape_yaml_string(list_name)}",
        f"folder: {escape_yaml_string(folder_name)}",
        "type: list-index",
        "---",
        "",
        f"# {list_name}",
        "",
    ]

    # Group by status
    active = [t for t in tasks if not t.is_completed and not t.is_archived and not t.has_parent]
    completed = [t for t in tasks if t.is_completed and not t.has_parent]
    archived = [t for t in tasks if t.is_archived and not t.has_parent]

    if active:
        lines.append("## Active")
        lines.append("")
        for task in sorted(active, key=lambda t: t.order):
            checkbox = "[ ]"
            lines.append(f"- {checkbox} [[{task.title}]]")
        lines.append("")

    if completed:
        lines.append("## Completed")
        lines.append("")
        for task in sorted(completed, key=lambda t: t.order):
            lines.append(f"- [x] [[{task.title}]]")
        lines.append("")

    if archived:
        lines.append("## Archived")
        lines.append("")
        for task in sorted(archived, key=lambda t: t.order):
            lines.append(f"- [[{task.title}]]")
        lines.append("")

    return "\n".join(lines)
