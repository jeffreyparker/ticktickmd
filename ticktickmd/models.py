"""Data models for TickTick tasks."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    NORMAL = 0
    COMPLETED = 1
    ARCHIVED = 2


class TaskKind(Enum):
    TEXT = "TEXT"
    NOTE = "NOTE"
    CHECKLIST = "CHECKLIST"


class Priority(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 3
    HIGH = 5


@dataclass
class Task:
    """Represents a single TickTick task."""

    folder_name: str
    list_name: str
    title: str
    kind: TaskKind
    tags: list[str]
    content: str
    is_checklist: bool
    start_date: Optional[datetime]
    due_date: Optional[datetime]
    reminder: str
    repeat: str
    priority: Priority
    status: TaskStatus
    created_time: Optional[datetime]
    completed_time: Optional[datetime]
    order: int
    timezone: str
    is_all_day: bool
    is_floating: bool
    column_name: str
    column_order: int
    view_mode: str
    task_id: str
    parent_id: str

    # Computed fields
    subtasks: list["Task"] = field(default_factory=list)

    @property
    def is_completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def is_archived(self) -> bool:
        return self.status == TaskStatus.ARCHIVED

    @property
    def has_parent(self) -> bool:
        return bool(self.parent_id)

    @property
    def priority_label(self) -> str:
        return {
            Priority.NONE: "none",
            Priority.LOW: "low",
            Priority.MEDIUM: "medium",
            Priority.HIGH: "high",
        }.get(self.priority, "none")

    @property
    def status_label(self) -> str:
        return {
            TaskStatus.NORMAL: "active",
            TaskStatus.COMPLETED: "completed",
            TaskStatus.ARCHIVED: "archived",
        }.get(self.status, "active")


@dataclass
class TaskList:
    """Represents a TickTick list containing tasks."""

    name: str
    folder_name: str
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)


@dataclass
class Folder:
    """Represents a TickTick folder containing lists."""

    name: str
    lists: dict[str, TaskList] = field(default_factory=dict)

    def get_or_create_list(self, list_name: str) -> TaskList:
        if list_name not in self.lists:
            self.lists[list_name] = TaskList(name=list_name, folder_name=self.name)
        return self.lists[list_name]


@dataclass
class TaskTree:
    """Hierarchical structure: Folder -> List -> Tasks."""

    folders: dict[str, Folder] = field(default_factory=dict)
    all_tasks: dict[str, Task] = field(default_factory=dict)  # task_id -> Task

    def get_or_create_folder(self, folder_name: str) -> Folder:
        if not folder_name:
            folder_name = "_Uncategorized"
        if folder_name not in self.folders:
            self.folders[folder_name] = Folder(name=folder_name)
        return self.folders[folder_name]

    def add_task(self, task: Task) -> None:
        folder = self.get_or_create_folder(task.folder_name)
        list_name = task.list_name or "_Uncategorized"
        task_list = folder.get_or_create_list(list_name)
        task_list.add_task(task)
        self.all_tasks[task.task_id] = task

    def build_subtask_relationships(self) -> None:
        """Link subtasks to their parents."""
        for task in self.all_tasks.values():
            if task.parent_id and task.parent_id in self.all_tasks:
                parent = self.all_tasks[task.parent_id]
                parent.subtasks.append(task)

    def get_top_level_tasks(self) -> list[Task]:
        """Return tasks that don't have parents."""
        return [t for t in self.all_tasks.values() if not t.has_parent]
