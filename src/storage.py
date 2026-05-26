import json
import os
from typing import List

from src.models import Habit, Task

_DATABASE_URL = os.environ.get("DATABASE_URL")
_DATA_FILE = os.path.expanduser("~/.todo_lists_data.json")
DEFAULT_CATEGORIES = ["general", "homework", "life", "emails", "work"]


# ── PostgreSQL backend ───────────────────────────────────────────────────────

def _conn():
    import psycopg2
    url = _DATABASE_URL
    if url and url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return psycopg2.connect(url)


def _init_db() -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    category TEXT DEFAULT 'general',
                    due_datetime TEXT,
                    priority TEXT DEFAULT 'medium',
                    recurring TEXT,
                    leading_reminders TEXT DEFAULT '[]',
                    description TEXT,
                    created_at TEXT,
                    scope TEXT DEFAULT 'daily',
                    duration_type TEXT DEFAULT 'quick',
                    estimated_minutes INTEGER,
                    actual_minutes INTEGER,
                    completed_at TEXT,
                    start_date TEXT,
                    subtasks TEXT DEFAULT '[]'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS habits (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    frequency TEXT DEFAULT 'daily',
                    completions TEXT DEFAULT '[]',
                    color TEXT DEFAULT 'sage',
                    created_at TEXT,
                    archived BOOLEAN DEFAULT FALSE
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    name TEXT PRIMARY KEY
                )
            """)
            cur.execute("SELECT COUNT(*) FROM categories")
            if cur.fetchone()[0] == 0:
                for cat in DEFAULT_CATEGORIES:
                    cur.execute(
                        "INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING",
                        (cat,),
                    )
        conn.commit()


_db_ready = False


def _ensure_db() -> None:
    global _db_ready
    if not _db_ready:
        _init_db()
        _db_ready = True


def _row_to_task(row: tuple, keys: list) -> Task:
    d = dict(zip(keys, row))
    d["leading_reminders"] = json.loads(d["leading_reminders"] or "[]")
    d["subtasks"] = json.loads(d["subtasks"] or "[]")
    return Task.from_dict(d)


def _row_to_habit(row: tuple, keys: list) -> Habit:
    d = dict(zip(keys, row))
    d["completions"] = json.loads(d["completions"] or "[]")
    return Habit.from_dict(d)


# ── DB task ops ──────────────────────────────────────────────────────────────

def _db_load_tasks() -> List[Task]:
    _ensure_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks ORDER BY id")
            cols = [d[0] for d in cur.description]
            return [_row_to_task(r, cols) for r in cur.fetchall()]


def _db_save_tasks(tasks: List[Task]) -> None:
    _ensure_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks")
            for t in tasks:
                d = t.to_dict()
                cur.execute(
                    """INSERT INTO tasks (id, title, completed, category, due_datetime,
                           priority, recurring, leading_reminders, description, created_at,
                           scope, duration_type, estimated_minutes, actual_minutes,
                           completed_at, start_date, subtasks)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        d["id"], d["title"], d["completed"], d["category"], d["due_datetime"],
                        d["priority"], d["recurring"], json.dumps(d["leading_reminders"]),
                        d["description"], d["created_at"], d["scope"], d["duration_type"],
                        d["estimated_minutes"], d["actual_minutes"], d["completed_at"],
                        d["start_date"], json.dumps(d["subtasks"]),
                    ),
                )
        conn.commit()


def _db_next_id() -> int:
    _ensure_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM tasks")
            return cur.fetchone()[0]


# ── DB habit ops ─────────────────────────────────────────────────────────────

def _db_load_habits() -> List[Habit]:
    _ensure_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM habits WHERE archived = FALSE ORDER BY id")
            cols = [d[0] for d in cur.description]
            return [_row_to_habit(r, cols) for r in cur.fetchall()]


def _db_save_habits(habits: List[Habit]) -> None:
    _ensure_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM habits WHERE archived = FALSE")
            for h in habits:
                d = h.to_dict()
                cur.execute(
                    """INSERT INTO habits (id, title, category, frequency, completions,
                           color, created_at, archived)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        d["id"], d["title"], d["category"], d["frequency"],
                        json.dumps(d["completions"]), d["color"], d["created_at"], d["archived"],
                    ),
                )
        conn.commit()


def _db_next_habit_id() -> int:
    _ensure_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM habits")
            return cur.fetchone()[0]


# ── DB category ops ──────────────────────────────────────────────────────────

def _db_load_categories() -> List[str]:
    _ensure_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM categories ORDER BY name")
            return [r[0] for r in cur.fetchall()]


def _db_save_categories(categories: List[str]) -> None:
    _ensure_db()
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM categories")
            for cat in categories:
                cur.execute("INSERT INTO categories (name) VALUES (%s)", (cat,))
        conn.commit()


# ── JSON file backend ────────────────────────────────────────────────────────

def _load_raw() -> dict:
    if not os.path.exists(_DATA_FILE):
        return {"tasks": [], "categories": list(DEFAULT_CATEGORIES), "habits": []}
    with open(_DATA_FILE) as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"tasks": data, "categories": list(DEFAULT_CATEGORIES), "habits": []}
    if "habits" not in data:
        data["habits"] = []
    return data


def _save_raw(data: dict) -> None:
    with open(_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Public API ───────────────────────────────────────────────────────────────

def load_tasks() -> List[Task]:
    if _DATABASE_URL:
        return _db_load_tasks()
    return [Task.from_dict(d) for d in _load_raw()["tasks"]]


def save_tasks(tasks: List[Task]) -> None:
    if _DATABASE_URL:
        _db_save_tasks(tasks)
        return
    raw = _load_raw()
    raw["tasks"] = [t.to_dict() for t in tasks]
    _save_raw(raw)


def next_id(items: list) -> int:
    if _DATABASE_URL:
        return _db_next_id()
    return max((t.id for t in items), default=0) + 1


def load_categories() -> List[str]:
    if _DATABASE_URL:
        return _db_load_categories()
    return _load_raw().get("categories", list(DEFAULT_CATEGORIES))


def save_categories(categories: List[str]) -> None:
    if _DATABASE_URL:
        _db_save_categories(categories)
        return
    raw = _load_raw()
    raw["categories"] = categories
    _save_raw(raw)


def load_habits() -> List[Habit]:
    if _DATABASE_URL:
        return _db_load_habits()
    return [Habit.from_dict(d) for d in _load_raw().get("habits", []) if not d.get("archived")]


def save_habits(habits: List[Habit]) -> None:
    if _DATABASE_URL:
        _db_save_habits(habits)
        return
    raw = _load_raw()
    all_raw = _load_raw().get("habits", [])
    archived = [h for h in all_raw if h.get("archived")]
    raw["habits"] = [h.to_dict() for h in habits] + archived
    _save_raw(raw)


def next_habit_id() -> int:
    if _DATABASE_URL:
        return _db_next_habit_id()
    raw = _load_raw()
    habits = raw.get("habits", [])
    return max((h["id"] for h in habits), default=0) + 1
