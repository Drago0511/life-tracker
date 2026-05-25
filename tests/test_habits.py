from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.habits import add_habit, complete_habit, delete_habit, list_habits, uncomplete_habit
from src.models import Habit


def _mock_habits(initial=None):
    store = {"habits": list(initial or [])}
    def load(): return [h for h in store["habits"] if not h.archived]
    def save(hs): store["habits"] = hs
    return load, save, store


@patch("src.habits.save_habits")
@patch("src.habits.load_habits")
@patch("src.habits.next_habit_id", return_value=1)
def test_add_habit(mock_id, mock_load, mock_save):
    mock_load.return_value = []
    h = add_habit("Meditate", frequency="daily", color="sage")
    assert h.title == "Meditate"
    assert h.frequency == "daily"
    assert h.color == "sage"
    mock_save.assert_called_once()


@patch("src.habits.save_habits")
@patch("src.habits.load_habits")
def test_complete_habit_today(mock_load, mock_save):
    today = datetime.now().strftime("%Y-%m-%d")
    h = Habit(id=1, title="Run")
    mock_load.return_value = [h]
    complete_habit(1)
    assert today in h.completions
    mock_save.assert_called_once()


@patch("src.habits.save_habits")
@patch("src.habits.load_habits")
def test_complete_habit_idempotent(mock_load, mock_save):
    today = datetime.now().strftime("%Y-%m-%d")
    h = Habit(id=1, title="Run", completions=[today])
    mock_load.return_value = [h]
    complete_habit(1)
    assert h.completions.count(today) == 1


@patch("src.habits.save_habits")
@patch("src.habits.load_habits")
def test_uncomplete_habit(mock_load, mock_save):
    today = datetime.now().strftime("%Y-%m-%d")
    h = Habit(id=1, title="Run", completions=[today])
    mock_load.return_value = [h]
    uncomplete_habit(1)
    assert today not in h.completions


@patch("src.habits.save_habits")
@patch("src.habits.load_habits")
def test_delete_habit(mock_load, mock_save):
    h = Habit(id=1, title="Run")
    mock_load.return_value = [h]
    result = delete_habit(1)
    assert result is True
    mock_save.assert_called_once_with([])


def test_streak_daily_consecutive():
    today = datetime.now().date()
    completions = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
    h = Habit(id=1, title="Run", completions=completions)
    assert h.current_streak == 5


def test_streak_daily_broken():
    today = datetime.now().date()
    completions = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(2, 6)]
    h = Habit(id=1, title="Run", completions=completions)
    assert h.current_streak == 0


def test_streak_zero_no_completions():
    h = Habit(id=1, title="Run")
    assert h.current_streak == 0


def test_completed_today_true():
    today = datetime.now().strftime("%Y-%m-%d")
    h = Habit(id=1, title="Run", completions=[today])
    assert h.completed_today is True


def test_completed_today_false():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    h = Habit(id=1, title="Run", completions=[yesterday])
    assert h.completed_today is False


def test_last_7_days():
    today = datetime.now().date()
    completions = [today.strftime("%Y-%m-%d"), (today - timedelta(days=2)).strftime("%Y-%m-%d")]
    h = Habit(id=1, title="Run", completions=completions)
    days = h.last_7_days
    assert len(days) == 7
    assert days[-1] is True   # today
    assert days[-3] is True   # 2 days ago
    assert days[-2] is False  # yesterday
