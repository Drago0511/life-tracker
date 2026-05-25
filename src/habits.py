from datetime import datetime
from typing import List, Optional

from src.models import Habit
from src.storage import load_habits, next_habit_id, save_habits


def add_habit(
    title: str,
    category: str = "general",
    frequency: str = "daily",
    color: str = "sage",
) -> Habit:
    habits = load_habits()
    habit = Habit(
        id=next_habit_id(),
        title=title,
        category=category,
        frequency=frequency,
        color=color,
    )
    habits.append(habit)
    save_habits(habits)
    return habit


def complete_habit(habit_id: int) -> Optional[Habit]:
    habits = load_habits()
    today = datetime.now().strftime("%Y-%m-%d")
    for habit in habits:
        if habit.id == habit_id:
            if today not in habit.completions:
                habit.completions.append(today)
                save_habits(habits)
            return habit
    return None


def uncomplete_habit(habit_id: int) -> Optional[Habit]:
    habits = load_habits()
    today = datetime.now().strftime("%Y-%m-%d")
    for habit in habits:
        if habit.id == habit_id:
            habit.completions = [d for d in habit.completions if d != today]
            save_habits(habits)
            return habit
    return None


def delete_habit(habit_id: int) -> bool:
    habits = load_habits()
    filtered = [h for h in habits if h.id != habit_id]
    if len(filtered) == len(habits):
        return False
    save_habits(filtered)
    return True


def update_habit(
    habit_id: int,
    title: Optional[str] = None,
    category: Optional[str] = None,
    frequency: Optional[str] = None,
    color: Optional[str] = None,
) -> Optional[Habit]:
    habits = load_habits()
    for habit in habits:
        if habit.id == habit_id:
            if title is not None:
                habit.title = title
            if category is not None:
                habit.category = category
            if frequency is not None:
                habit.frequency = frequency
            if color is not None:
                habit.color = color
            save_habits(habits)
            return habit
    return None


def list_habits() -> List[Habit]:
    return load_habits()
