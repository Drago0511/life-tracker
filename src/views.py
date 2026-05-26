import calendar as cal_mod
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.models import Task


def _scope_rank(scope: str) -> int:
    return {"yearly": 0, "monthly": 1, "weekly": 2, "daily": 3}.get(scope, 3)


def _dur_rank(dur: str) -> int:
    return {"project": 0, "medium": 1, "quick": 2}.get(dur, 2)


def scope_sort_key(task: Task):
    pri = {"high": 0, "medium": 1, "low": 2}.get(task.priority, 1)
    return (_scope_rank(task.scope), _dur_rank(task.duration_type), pri, task.due_datetime or "9999")


def _today() -> datetime:
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_date(date_str: Optional[str]) -> datetime:
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass
    return _today()


def day_tasks(tasks: List[Task], date: Optional[str] = None) -> Dict:
    ref = _parse_date(date)
    ref_str = ref.strftime("%Y-%m-%d")
    result: Dict[str, List[Task]] = {"long_term": [], "today": [], "overdue": []}
    for t in tasks:
        if t.completed:
            continue
        if t.scope in ("monthly", "yearly") or t.duration_type == "project":
            result["long_term"].append(t)
            continue
        if t.due_datetime:
            due_date = t.due_datetime[:10]
            if due_date < ref_str:
                result["overdue"].append(t)
            elif due_date == ref_str:
                result["today"].append(t)
        else:
            result["today"].append(t)
    for key in result:
        result[key].sort(key=scope_sort_key)
    return result


def week_groups(tasks: List[Task]) -> Dict:
    ws = _today() - timedelta(days=_today().weekday())
    days = {(ws + timedelta(days=i)).strftime("%Y-%m-%d"): [] for i in range(7)}
    long_term, unscheduled = [], []
    for t in tasks:
        if t.completed:
            continue
        if t.scope in ("monthly", "yearly") or t.duration_type == "project":
            long_term.append(t)
            continue
        due_date = t.due_datetime[:10] if t.due_datetime else None
        if due_date in days:
            days[due_date].append(t)
        else:
            unscheduled.append(t)
    for key in days:
        days[key].sort(key=scope_sort_key)
    return {"long_term": sorted(long_term, key=scope_sort_key),
            "days": days,
            "unscheduled": sorted(unscheduled, key=scope_sort_key)}


def month_groups(tasks: List[Task]) -> Dict:
    now = datetime.now()
    year, month = now.year, now.month
    weeks: Dict[int, List[Task]] = {1: [], 2: [], 3: [], 4: []}
    long_term, unscheduled = [], []
    for t in tasks:
        if t.completed:
            continue
        if t.scope == "yearly" or (t.scope == "monthly" and t.duration_type == "project"):
            long_term.append(t)
            continue
        if t.due_datetime:
            try:
                due = datetime.fromisoformat(t.due_datetime)
                if due.year == year and due.month == month:
                    weeks[min(((due.day - 1) // 7) + 1, 4)].append(t)
                else:
                    unscheduled.append(t)
            except ValueError:
                unscheduled.append(t)
        else:
            unscheduled.append(t)
    for k in weeks:
        weeks[k].sort(key=scope_sort_key)
    return {"long_term": sorted(long_term, key=scope_sort_key),
            "weeks": weeks,
            "unscheduled": sorted(unscheduled, key=scope_sort_key)}


def sixmonth_groups(tasks: List[Task]) -> Dict:
    now = datetime.now()
    months = {}
    for i in range(6):
        m = (now.month - 1 + i) % 12 + 1
        y = now.year + (now.month - 1 + i) // 12
        months[f"{y}-{m:02d}"] = []
    ungrouped = []
    for t in tasks:
        if t.completed:
            continue
        key = t.due_datetime[:7] if t.due_datetime else None
        if key in months:
            months[key].append(t)
        else:
            ungrouped.append(t)
    for k in months:
        months[k].sort(key=scope_sort_key)
    return {"months": months, "ungrouped": sorted(ungrouped, key=scope_sort_key)}


def year_groups(tasks: List[Task]) -> Dict:
    now = datetime.now()
    quarters = {1: [], 2: [], 3: [], 4: []}
    ungrouped = []
    for t in tasks:
        if t.completed:
            continue
        if t.due_datetime:
            try:
                due = datetime.fromisoformat(t.due_datetime)
                if due.year == now.year:
                    quarters[(due.month - 1) // 3 + 1].append(t)
                else:
                    ungrouped.append(t)
            except ValueError:
                ungrouped.append(t)
        else:
            ungrouped.append(t)
    for k in quarters:
        quarters[k].sort(key=scope_sort_key)
    return {"quarters": quarters, "ungrouped": sorted(ungrouped, key=scope_sort_key)}


def timeblock_data(tasks: List[Task], date: Optional[str] = None) -> Dict:
    day = _parse_date(date).date()
    day_str = day.strftime("%Y-%m-%d")
    slots: Dict[int, List[Task]] = {h: [] for h in range(6, 24)}
    unscheduled = []
    for t in tasks:
        if t.completed:
            continue
        if t.due_datetime:
            try:
                due = datetime.fromisoformat(t.due_datetime)
                if due.date() == day and 6 <= due.hour < 24:
                    slots[due.hour].append(t)
                    continue
            except ValueError:
                pass
        unscheduled.append(t)
    for h in slots:
        slots[h].sort(key=scope_sort_key)
    return {"slots": slots, "unscheduled": sorted(unscheduled, key=scope_sort_key), "date": day_str}


def compute_weekly_report(tasks: List[Task], habits: list) -> Dict:
    now = datetime.now()
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6)
    ws_d, we_d = week_start.date(), week_end.date()

    completed_week = []
    for t in tasks:
        if t.completed and t.completed_at:
            try:
                if ws_d <= datetime.fromisoformat(t.completed_at).date() <= we_d:
                    completed_week.append(t)
            except ValueError:
                pass

    by_cat: Dict[str, int] = defaultdict(int)
    for t in completed_week:
        by_cat[t.category] += 1

    active = [t for t in tasks if not t.completed]
    overdue = [t for t in active if t.due_datetime and
               datetime.fromisoformat(t.due_datetime) < now]
    goals = [t for t in tasks if t.scope in ("monthly", "yearly") and not t.completed]

    habit_stats = [
        {"title": h.title, "streak": h.current_streak,
         "completed_today": h.completed_today, "frequency": h.frequency}
        for h in habits
    ]

    weekly_history = []
    for i in range(11, -1, -1):
        ref = now - timedelta(weeks=i)
        w_start = (ref - timedelta(days=ref.weekday())).date()
        w_end = w_start + timedelta(days=6)
        count = 0
        for t in tasks:
            if t.completed and t.completed_at:
                try:
                    if w_start <= datetime.fromisoformat(t.completed_at).date() <= w_end:
                        count += 1
                except ValueError:
                    pass
        weekly_history.append(count)

    return {
        "week_label": f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}",
        "completed": completed_week,
        "completed_count": len(completed_week),
        "by_category": dict(by_cat),
        "active_count": len(active),
        "overdue_count": len(overdue),
        "habits": habit_stats,
        "goals": goals,
        "weekly_history": weekly_history,
    }
