import calendar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional

Priority = Literal["critical", "important", "high", "medium", "low"]
Scope = Literal["daily", "weekly", "monthly", "yearly"]
DurationType = Literal["quick", "medium", "project"]
HabitColor = Literal["sage", "terracotta", "sky", "gold", "violet",
                     "forest", "steel", "amber", "softviolet", "dustyrose",
                     "sienna", "slate", "teal", "warmcream", "charcoal", "plum"]
HabitFrequency = Literal["daily", "weekly", "flexible"]

PRIORITIES = ("critical", "important", "high", "medium", "low")
RECURRENCES = ("daily", "weekly", "monthly")
SCOPES = ("daily", "weekly", "monthly", "yearly")
DURATION_TYPES = ("quick", "medium", "project")
HABIT_COLORS = ("forest", "terracotta", "steel", "amber", "softviolet",
                "dustyrose", "sienna", "slate", "teal", "warmcream", "charcoal", "plum")

LEADING_REMINDER_MINUTES: dict = {
    "1w": 10080, "3d": 4320, "1d": 1440,
    "3h": 180, "1h": 60, "30m": 30, "15m": 15, "5m": 5,
}
LEADING_REMINDER_LABELS = ("1w", "3d", "1d", "3h", "1h", "30m", "15m", "5m")


def _streak_daily(comp_set, today) -> int:
    start = today if today in comp_set else (
        today - timedelta(days=1) if (today - timedelta(days=1)) in comp_set else None
    )
    if start is None:
        return 0
    streak, cur = 0, start
    while cur in comp_set:
        streak += 1
        cur -= timedelta(days=1)
    return streak


def _streak_flexible(comp_set, today, target: int = 5) -> int:
    """Consecutive weeks (Mon–Sun) where the user hit target completions."""
    def ws(d): return d - timedelta(days=d.weekday())

    def week_hits(week_start):
        week_end = week_start + timedelta(days=6)
        return sum(1 for d in comp_set if week_start <= d <= week_end)

    this_week = ws(today)
    prev_week = this_week - timedelta(weeks=1)
    if week_hits(this_week) >= target:
        start_week = this_week
    elif week_hits(prev_week) >= target:
        start_week = prev_week
    else:
        return 0

    streak, cur = 0, start_week
    while week_hits(cur) >= target:
        streak += 1
        cur -= timedelta(weeks=1)
    return streak


def _streak_weekly(comp_set, today) -> int:
    def ws(d): return d - timedelta(days=d.weekday())
    this_week = ws(today)
    prev_week = this_week - timedelta(weeks=1)
    weeks = {ws(d) for d in comp_set}
    if this_week not in weeks and prev_week not in weeks:
        return 0
    start_week = this_week if this_week in weeks else prev_week
    streak, cur = 0, start_week
    while cur in weeks:
        streak += 1
        cur -= timedelta(weeks=1)
    return streak


@dataclass
class Task:
    id: int
    title: str
    completed: bool = False
    category: str = "general"
    due_datetime: Optional[str] = None
    priority: Priority = "medium"
    recurring: Optional[str] = None
    leading_reminders: List[str] = field(default_factory=list)
    description: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    scope: Scope = "daily"
    duration_type: DurationType = "quick"
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    completed_at: Optional[str] = None
    start_date: Optional[str] = None
    subtasks: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "completed": self.completed,
            "category": self.category, "due_datetime": self.due_datetime,
            "priority": self.priority, "recurring": self.recurring,
            "leading_reminders": self.leading_reminders, "description": self.description,
            "created_at": self.created_at, "scope": self.scope,
            "duration_type": self.duration_type, "estimated_minutes": self.estimated_minutes,
            "actual_minutes": self.actual_minutes, "completed_at": self.completed_at,
            "start_date": self.start_date, "subtasks": self.subtasks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"], title=data["title"],
            completed=data.get("completed", False),
            category=data.get("category", "general"),
            due_datetime=data.get("due_datetime"),
            priority=data.get("priority", "medium"),
            recurring=data.get("recurring"),
            leading_reminders=data.get("leading_reminders", []),
            description=data.get("description"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            scope=data.get("scope", "daily"),
            duration_type=data.get("duration_type", "quick"),
            estimated_minutes=data.get("estimated_minutes"),
            actual_minutes=data.get("actual_minutes"),
            completed_at=data.get("completed_at"),
            start_date=data.get("start_date"),
            subtasks=data.get("subtasks", []),
        )

    def subtask_progress(self) -> tuple:
        if not self.subtasks:
            return (0, 0)
        done = sum(1 for s in self.subtasks if s.get("done"))
        return (done, len(self.subtasks))

    def next_due(self) -> Optional[str]:
        if not self.due_datetime or not self.recurring:
            return None
        try:
            due = datetime.fromisoformat(self.due_datetime)
            if self.recurring == "daily":
                due += timedelta(days=1)
            elif self.recurring == "weekly":
                due += timedelta(weeks=1)
            elif self.recurring == "monthly":
                month = due.month % 12 + 1
                year = due.year + (due.month // 12)
                day = min(due.day, calendar.monthrange(year, month)[1])
                due = due.replace(year=year, month=month, day=day)
            return due.strftime("%Y-%m-%dT%H:%M")
        except ValueError:
            return None


@dataclass
class Habit:
    id: int
    title: str
    category: str = "general"
    frequency: HabitFrequency = "daily"
    completions: List[str] = field(default_factory=list)  # "YYYY-MM-DD" dates
    color: HabitColor = "sage"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    archived: bool = False
    best_streak: int = 0

    @property
    def completed_today(self) -> bool:
        return datetime.now().strftime("%Y-%m-%d") in self.completions

    @property
    def current_streak(self) -> int:
        if not self.completions:
            return 0
        today = datetime.now().date()
        comp_set = {datetime.strptime(d, "%Y-%m-%d").date() for d in self.completions}
        if self.frequency == "daily":
            return _streak_daily(comp_set, today)
        if self.frequency == "flexible":
            return _streak_flexible(comp_set, today)
        return _streak_weekly(comp_set, today)

    @property
    def last_7_days(self) -> List[bool]:
        today = datetime.now().date()
        comp_set = set(self.completions)
        return [
            (today - timedelta(days=i)).strftime("%Y-%m-%d") in comp_set
            for i in range(6, -1, -1)
        ]

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "category": self.category,
            "frequency": self.frequency, "completions": self.completions,
            "color": self.color, "created_at": self.created_at,
            "archived": self.archived, "best_streak": self.best_streak,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Habit":
        return cls(
            id=data["id"], title=data["title"],
            category=data.get("category", "general"),
            frequency=data.get("frequency", "daily"),
            completions=data.get("completions", []),
            color=data.get("color", "sage"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            archived=data.get("archived", False),
            best_streak=data.get("best_streak", 0),
        )
