from datetime import datetime
from typing import List, Optional

from src.models import Task
from src.storage import (
    load_categories, load_tasks, next_id,
    save_categories, save_tasks,
)


def add_task(
    title: str,
    category: str = "general",
    due_datetime: Optional[str] = None,
    priority: str = "medium",
    recurring: Optional[str] = None,
    leading_reminders: Optional[List[str]] = None,
    description: Optional[str] = None,
    scope: str = "daily",
    duration_type: str = "quick",
    estimated_minutes: Optional[int] = None,
    start_date: Optional[str] = None,
    subtasks: Optional[List[dict]] = None,
) -> Task:
    tasks = load_tasks()
    task = Task(
        id=next_id(tasks),
        title=title,
        category=category,
        due_datetime=due_datetime,
        priority=priority,
        recurring=recurring,
        leading_reminders=leading_reminders or [],
        description=description,
        scope=scope,
        duration_type=duration_type,
        estimated_minutes=estimated_minutes,
        start_date=start_date,
        subtasks=subtasks or [],
    )
    tasks.append(task)
    save_tasks(tasks)
    return task


def complete_task(task_id: int, actual_minutes: Optional[int] = None) -> Optional[Task]:
    tasks = load_tasks()
    for task in tasks:
        if task.id == task_id:
            task.completed = True
            task.completed_at = datetime.now().isoformat()
            if actual_minutes is not None:
                task.actual_minutes = actual_minutes
            save_tasks(tasks)
            if task.recurring:
                _spawn_next(task)
            return task
    return None


def toggle_subtask(task_id: int, subtask_idx: int) -> Optional[Task]:
    tasks = load_tasks()
    for task in tasks:
        if task.id == task_id:
            if 0 <= subtask_idx < len(task.subtasks):
                task.subtasks[subtask_idx]["done"] = not task.subtasks[subtask_idx].get("done", False)
                save_tasks(tasks)
            return task
    return None


def delete_task(task_id: int) -> bool:
    tasks = load_tasks()
    filtered = [t for t in tasks if t.id != task_id]
    if len(filtered) == len(tasks):
        return False
    save_tasks(filtered)
    return True


def list_tasks(
    show_completed: bool = False,
    category: Optional[str] = None,
) -> List[Task]:
    tasks = load_tasks()
    if not show_completed:
        tasks = [t for t in tasks if not t.completed]
    if category and category != "all":
        tasks = [t for t in tasks if t.category == category]
    return sorted(tasks, key=_due_sort_key)


def pinned_tasks(n: int = 3) -> List[Task]:
    tasks = [t for t in load_tasks() if not t.completed]
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    tasks.sort(key=lambda t: (priority_rank.get(t.priority, 1), _due_sort_key(t)))
    return tasks[:n]


def handle_overdue_recurring() -> None:
    now = datetime.now()
    tasks = load_tasks()
    to_remove, to_add = [], []
    for task in tasks:
        if task.completed or not task.due_datetime or not task.recurring:
            continue
        try:
            if datetime.fromisoformat(task.due_datetime) < now:
                to_remove.append(task.id)
                next_due = task.next_due()
                to_add.append(Task(
                    id=0,  # assigned below
                    title=task.title,
                    category=task.category,
                    due_datetime=next_due,
                    priority=task.priority,
                    recurring=task.recurring,
                    leading_reminders=task.leading_reminders,
                    scope=task.scope,
                    duration_type=task.duration_type,
                    estimated_minutes=task.estimated_minutes,
                ))
        except ValueError:
            pass
    if to_remove:
        tasks = [t for t in tasks if t.id not in to_remove]
        for new_task in to_add:
            new_task.id = next_id(tasks)
            tasks.append(new_task)
        save_tasks(tasks)


def add_category(name: str) -> List[str]:
    cats = load_categories()
    if name and name not in cats:
        cats.append(name)
        save_categories(cats)
    return cats


def delete_category(name: str) -> List[str]:
    if name == "general":
        return load_categories()
    cats = [c for c in load_categories() if c != name]
    save_categories(cats)
    tasks = load_tasks()
    for t in tasks:
        if t.category == name:
            t.category = "general"
    save_tasks(tasks)
    return cats


def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    due_datetime: Optional[str] = None,
    priority: Optional[str] = None,
    recurring: Optional[str] = None,
    leading_reminders: Optional[List[str]] = None,
    scope: Optional[str] = None,
    duration_type: Optional[str] = None,
    estimated_minutes: Optional[int] = None,
    start_date: Optional[str] = None,
    subtasks: Optional[List[dict]] = None,
) -> Optional[Task]:
    tasks = load_tasks()
    for task in tasks:
        if task.id == task_id:
            if title is not None:
                task.title = title
            if description is not None:
                task.description = description or None
            if category is not None:
                task.category = category
            if due_datetime is not None:
                task.due_datetime = due_datetime or None
            if priority is not None:
                task.priority = priority
            if recurring is not None:
                task.recurring = recurring or None
            if leading_reminders is not None:
                task.leading_reminders = leading_reminders
            if scope is not None:
                task.scope = scope
            if duration_type is not None:
                task.duration_type = duration_type
            if estimated_minutes is not None:
                task.estimated_minutes = estimated_minutes
            if start_date is not None:
                task.start_date = start_date or None
            if subtasks is not None:
                task.subtasks = subtasks
            save_tasks(tasks)
            return task
    return None


def list_categories() -> List[str]:
    return load_categories()


def _due_sort_key(task: Task):
    return (0, task.due_datetime) if task.due_datetime else (1, "")


def _spawn_next(completed_task: Task) -> None:
    next_due = completed_task.next_due()
    tasks = load_tasks()
    tasks.append(Task(
        id=next_id(tasks),
        title=completed_task.title,
        category=completed_task.category,
        due_datetime=next_due,
        priority=completed_task.priority,
        recurring=completed_task.recurring,
        leading_reminders=completed_task.leading_reminders,
        scope=completed_task.scope,
        duration_type=completed_task.duration_type,
        estimated_minutes=completed_task.estimated_minutes,
    ))
    save_tasks(tasks)
