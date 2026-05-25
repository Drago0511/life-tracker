import time
from datetime import datetime, timedelta
from typing import Set

from src.models import LEADING_REMINDER_MINUTES
from src.notifications import notify
from src.storage import load_tasks

_notified: Set[tuple] = set()


def check_reminders() -> None:
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    tasks = load_tasks()
    for task in tasks:
        if task.completed or not task.due_datetime:
            continue
        due_key = task.due_datetime

        key_due = (task.id, "due", due_key)
        if task.due_datetime == now_str and key_due not in _notified:
            notify("Due now", task.title)
            _notified.add(key_due)

        try:
            due = datetime.fromisoformat(task.due_datetime)
        except ValueError:
            continue

        for label in task.leading_reminders:
            minutes = LEADING_REMINDER_MINUTES.get(label)
            if minutes is None:
                continue
            trigger = (due - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M")
            key = (task.id, label, due_key)
            if trigger == now_str and key not in _notified:
                notify(f"Reminder — {label} before due", task.title)
                _notified.add(key)


def run() -> None:
    print("Reminder daemon started. Press Ctrl+C to stop.")
    last_date = datetime.now().date()
    while True:
        today = datetime.now().date()
        if today != last_date:
            _notified.clear()
            last_date = today
        check_reminders()
        time.sleep(60)
