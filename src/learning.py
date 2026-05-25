import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.storage import load_tasks


def get_insights() -> Dict:
    tasks = load_tasks()
    completed = [t for t in tasks if t.completed and t.completed_at]

    hour_counts: Dict[int, int] = defaultdict(int)
    category_times: Dict[str, List[int]] = defaultdict(list)
    scope_completion: Dict[str, int] = defaultdict(int)
    duration_accuracy: List[float] = []

    for t in completed:
        try:
            hour_counts[datetime.fromisoformat(t.completed_at).hour] += 1
        except (ValueError, TypeError):
            pass
        if t.estimated_minutes and t.actual_minutes:
            duration_accuracy.append(t.actual_minutes / t.estimated_minutes)
            category_times[t.category].append(t.actual_minutes)
        scope_completion[t.scope] += 1

    preferred_hour = max(hour_counts, key=hour_counts.get) if hour_counts else None
    avg_accuracy = sum(duration_accuracy) / len(duration_accuracy) if duration_accuracy else 1.0

    return {
        "preferred_hour": preferred_hour,
        "avg_accuracy": round(avg_accuracy, 2),
        "scope_completion": dict(scope_completion),
        "category_times": {k: round(sum(v) / len(v)) for k, v in category_times.items()},
        "total_completed": len(completed),
    }


def predict_duration(title: str, category: str, duration_type: str) -> Optional[int]:
    tasks = load_tasks()
    completed = [t for t in tasks if t.completed and t.actual_minutes and t.category == category]
    if not completed:
        return {"quick": 15, "medium": 60, "project": 240}.get(duration_type)
    same_type = [t.actual_minutes for t in completed if t.duration_type == duration_type]
    if same_type:
        return round(sum(same_type) / len(same_type))
    return round(sum(t.actual_minutes for t in completed) / len(completed))


def suggest_subtasks(title: str, duration_type: str) -> List[str]:
    if duration_type == "quick":
        return []

    from src.ai_client import ai_json
    result = ai_json(
        f'Task: "{title}"\nType: {duration_type} project\n\n'
        f'List 4-5 specific, actionable subtasks. Return ONLY a JSON array of strings.',
        max_tokens=200,
    )
    if result:
        try:
            parsed = json.loads(result)
            if isinstance(parsed, list) and all(isinstance(s, str) for s in parsed):
                return parsed[:6]
        except (json.JSONDecodeError, ValueError):
            pass

    templates = {
        "research": ["Define scope", "Gather sources", "Synthesize findings", "Write summary"],
        "write": ["Outline", "First draft", "Revise", "Final review"],
        "build": ["Design", "Implement core", "Test", "Refine"],
        "plan": ["Identify goals", "List steps", "Assign timelines", "Review plan"],
        "learn": ["Find resources", "Study concepts", "Practice", "Review & reflect"],
        "review": ["Read through", "Note issues", "Make changes", "Final check"],
    }
    title_lower = title.lower()
    for keyword, subtasks in templates.items():
        if keyword in title_lower:
            return subtasks
    if duration_type == "project":
        return ["Define scope", "Break into milestones", "Execute", "Review & complete"]
    return ["Start", "Work through", "Finish up"]


def schedule_suggest(tasks: list, insights: Dict) -> List[Dict]:
    if not tasks:
        return []
    preferred = insights.get("preferred_hour", 9)
    task_descriptions = "\n".join(
        f"- [{i}] {t.title} ({t.duration_type}, ~{t.estimated_minutes or '?'}min, {t.priority} priority)"
        for i, t in enumerate(tasks[:8])
    )
    from src.ai_client import ai_json
    result = ai_json(
        f"Schedule these tasks optimally for today. User's preferred focus hour: {preferred}:00.\n"
        f"Tasks:\n{task_descriptions}\n\n"
        f'Return JSON array: [{{"task_idx": 0, "hour": 9, "reason": "..."}}]. '
        f"Quick tasks in morning slots, projects at peak hour, low priority late afternoon.",
        max_tokens=300,
    )
    if result:
        try:
            parsed = json.loads(result)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    hour = preferred or 9
    return [{"task_idx": i, "hour": min(hour + i, 21), "reason": "Based on your patterns"}
            for i in range(min(len(tasks), 6))]


def _fallback_weekly_insight(report_data: Dict) -> str:
    """Deterministic insight built from report_data, used when no LLM is available."""
    completed = int(report_data.get("completed_count", 0) or 0)
    active = int(report_data.get("active_count", 0) or 0)
    overdue = int(report_data.get("overdue_count", 0) or 0)
    by_cat = report_data.get("by_category", {}) or {}
    habits = report_data.get("habits", []) or []
    streaked = [h for h in habits if (h.get("streak") or 0) > 0]
    top_streak = max(streaked, key=lambda h: h.get("streak", 0)) if streaked else None
    top_cat = max(by_cat.items(), key=lambda kv: kv[1])[0] if by_cat else None

    # Sentence 1: celebrate wins
    if completed == 0 and not streaked:
        s1 = "This week is a blank canvas — no completions logged yet, so anything you ship counts as a win."
    elif completed and top_cat:
        s1 = f"Strong week: {completed} task{'s' if completed != 1 else ''} done, with most momentum in **{top_cat}**."
    elif completed:
        s1 = f"Solid output — {completed} task{'s' if completed != 1 else ''} completed across the week."
    else:
        s1 = f"You kept consistency alive with {len(streaked)} habit streak{'s' if len(streaked) != 1 else ''} going."

    # Sentence 2: what to improve
    if overdue >= 5:
        s2 = f"Your overdue pile is climbing ({overdue} items) — it's the biggest drag on next week's focus."
    elif overdue:
        s2 = f"A small backlog is forming: {overdue} task{'s' if overdue != 1 else ''} slipped past due."
    elif active >= 15:
        s2 = f"You have {active} active items in flight — risk of context-switching is high."
    elif active:
        s2 = f"There are {active} active task{'s' if active != 1 else ''} on deck; keep the queue lean."
    else:
        s2 = "Nothing is overdue and the queue is clear — a rare and earned position."

    # Sentence 3: actionable tip
    if overdue:
        s3 = f"This week, pick the **2 oldest overdue items** and finish or reschedule them on Monday — don't let them roll forward again."
    elif active >= 15:
        s3 = "Block 25 minutes Monday morning to triage your active list — archive, defer, or commit each one."
    elif top_streak:
        s3 = f"Protect your **{top_streak['title']}** streak ({top_streak['streak']} {top_streak.get('frequency', 'day')}s) — schedule it before anything reactive."
    elif top_cat:
        s3 = f"Double down on **{top_cat}** next week — that's where your wins are clustering."
    else:
        s3 = "Add one tiny daily habit (5 minutes is enough) to start building a streak you can point to next week."

    return f"{s1} {s2} {s3}"


def weekly_report_insight(report_data: Dict) -> str:
    """Return a 3-sentence weekly insight. Uses Claude if available, otherwise a
    deterministic fallback built from report_data so the report tab is never empty."""
    from src.ai_client import ai_complete
    habits_str = ", ".join(
        f"{h['title']} ({h['streak']} day streak)" for h in report_data.get("habits", [])[:3]
    ) or "none tracked"
    cats_str = ", ".join(list(report_data.get("by_category", {}).keys())[:4]) or "various"
    ai_text = ai_complete(
        f"Weekly productivity summary:\n"
        f"- Completed: {report_data['completed_count']} tasks\n"
        f"- Active: {report_data['active_count']}, Overdue: {report_data['overdue_count']}\n"
        f"- Top categories: {cats_str}\n"
        f"- Habits: {habits_str}\n\n"
        f"Write 3 sentences: 1 celebrating wins, 1 noting what to improve, 1 actionable tip for next week.",
        system="You are an encouraging productivity coach. Be warm, specific, and brief.",
        max_tokens=180,
    )
    return ai_text or _fallback_weekly_insight(report_data)


def preferred_hour() -> Optional[int]:
    return get_insights().get("preferred_hour")
