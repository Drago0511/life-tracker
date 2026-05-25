from unittest.mock import patch

import pytest

import src.storage as storage_module
from src.tasks import (
    add_category, add_task, complete_task, delete_category,
    delete_task, list_categories, list_tasks,
)


@pytest.fixture(autouse=True)
def tmp_data_file(tmp_path):
    data_file = str(tmp_path / "tasks.json")
    with patch.object(storage_module, "DATA_FILE", data_file):
        yield data_file


def test_add_task_defaults():
    task = add_task("Buy milk")
    assert task.id == 1
    assert task.title == "Buy milk"
    assert not task.completed
    assert task.category == "general"
    assert task.priority == "medium"
    assert task.due_datetime is None
    assert task.recurring is None
    assert task.leading_reminders == []


def test_add_task_all_fields():
    task = add_task(
        "Stand-up", category="work", due_datetime="2026-06-01T09:00",
        priority="high", recurring="daily", leading_reminders=["15m", "1h"],
    )
    assert task.priority == "high"
    assert task.category == "work"
    assert task.due_datetime == "2026-06-01T09:00"
    assert task.recurring == "daily"
    assert task.leading_reminders == ["15m", "1h"]


def test_add_multiple_tasks_increments_id():
    t1 = add_task("First")
    t2 = add_task("Second")
    assert t2.id == t1.id + 1


def test_complete_task():
    task = add_task("Do laundry")
    result = complete_task(task.id)
    assert result is not None
    assert result.completed


def test_complete_nonexistent_task():
    assert complete_task(999) is None


def test_complete_recurring_spawns_next():
    add_task("Daily standup", due_datetime="2026-06-01T09:00", recurring="daily")
    complete_task(1)
    tasks = list_tasks(show_completed=True)
    active = [t for t in tasks if not t.completed]
    assert len(active) == 1
    assert active[0].due_datetime == "2026-06-02T09:00"


def test_delete_task():
    task = add_task("Clean desk")
    assert delete_task(task.id)
    assert list_tasks() == []


def test_delete_nonexistent_task():
    assert not delete_task(999)


def test_list_excludes_completed_by_default():
    t1 = add_task("Active")
    t2 = add_task("Done")
    complete_task(t2.id)
    tasks = list_tasks()
    assert len(tasks) == 1
    assert tasks[0].id == t1.id


def test_list_show_all():
    add_task("Active")
    t2 = add_task("Done")
    complete_task(t2.id)
    assert len(list_tasks(show_completed=True)) >= 2


def test_list_filter_by_category():
    add_task("School task", category="homework")
    add_task("Life task", category="life")
    tasks = list_tasks(category="homework")
    assert len(tasks) == 1
    assert tasks[0].category == "homework"


def test_list_sorted_by_due_date():
    add_task("Later", due_datetime="2026-06-05T10:00")
    add_task("Sooner", due_datetime="2026-06-01T10:00")
    add_task("No due")
    tasks = list_tasks()
    assert tasks[0].due_datetime == "2026-06-01T10:00"
    assert tasks[1].due_datetime == "2026-06-05T10:00"
    assert tasks[2].due_datetime is None


def test_categories_crud():
    cats = add_category("projects")
    assert "projects" in cats
    cats = add_category("projects")  # duplicate
    assert cats.count("projects") == 1
    cats = delete_category("projects")
    assert "projects" not in cats


def test_delete_category_reassigns_tasks():
    add_category("temp")
    add_task("My task", category="temp")
    delete_category("temp")
    tasks = list_tasks()
    assert tasks[0].category == "general"


def test_cannot_delete_general_category():
    cats = delete_category("general")
    assert "general" in cats
