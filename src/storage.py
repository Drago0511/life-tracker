import json
import os
from typing import List

from src.models import Habit, Task

DATA_FILE = os.path.expanduser("~/.todo_lists_data.json")
DEFAULT_CATEGORIES = ["general", "homework", "life", "emails", "work"]


def _load_raw() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"tasks": [], "categories": list(DEFAULT_CATEGORIES), "habits": []}
    with open(DATA_FILE) as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"tasks": data, "categories": list(DEFAULT_CATEGORIES), "habits": []}
    if "habits" not in data:
        data["habits"] = []
    return data


def _save_raw(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_tasks() -> List[Task]:
    return [Task.from_dict(d) for d in _load_raw()["tasks"]]


def save_tasks(tasks: List[Task]) -> None:
    raw = _load_raw()
    raw["tasks"] = [t.to_dict() for t in tasks]
    _save_raw(raw)


def load_categories() -> List[str]:
    return _load_raw().get("categories", list(DEFAULT_CATEGORIES))


def save_categories(categories: List[str]) -> None:
    raw = _load_raw()
    raw["categories"] = categories
    _save_raw(raw)


def load_habits() -> List[Habit]:
    return [Habit.from_dict(d) for d in _load_raw().get("habits", []) if not d.get("archived")]


def save_habits(habits: List[Habit]) -> None:
    raw = _load_raw()
    all_raw = _load_raw().get("habits", [])
    archived = [h for h in all_raw if h.get("archived")]
    raw["habits"] = [h.to_dict() for h in habits] + archived
    _save_raw(raw)


def next_id(items: list) -> int:
    return max((t.id for t in items), default=0) + 1


def next_habit_id() -> int:
    raw = _load_raw()
    habits = raw.get("habits", [])
    return max((h["id"] for h in habits), default=0) + 1
