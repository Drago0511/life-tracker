import json
import os
import re
import threading
import uuid
from datetime import datetime, timedelta

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFProtect, CSRFError

from src.ai_client import has_ai
from src.habits import (
    add_habit, complete_habit, delete_habit, list_habits,
    uncomplete_habit, update_habit,
)
from src.learning import (
    get_insights, schedule_suggest,
    suggest_subtasks, weekly_report_insight,
)
from src.models import LEADING_REMINDER_LABELS, SCOPES, DURATION_TYPES, HABIT_COLORS
from src.storage import load_tasks
from src.tasks import (
    add_category, add_task, complete_task, delete_category,
    delete_task, handle_overdue_recurring, list_categories,
    list_tasks, pinned_tasks, toggle_subtask, uncomplete_task, update_task,
)
from src.views import (
    compute_weekly_report, day_tasks, month_groups, sixmonth_groups,
    timeblock_data, week_groups, year_groups,
)

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-set-SECRET_KEY-in-production")
csrf = CSRFProtect(app)

_ai_jobs: dict = {}

@app.errorhandler(CSRFError)
def csrf_error(e):
    return redirect(request.referrer or url_for("index"))

_VALID_PRIORITIES = {"high", "medium", "low"}
_VALID_RECURRENCES = {"daily", "weekly", "monthly"}
_VALID_SCOPES = set(SCOPES)
_VALID_DURATIONS = set(DURATION_TYPES)
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.template_filter("fmt_due")
def fmt_due(dt_str: str) -> str:
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str)
        today = datetime.now().date()
        if dt.date() == today:
            return f"Today · {dt.strftime('%H:%M')}"
        if dt.date() == today + timedelta(days=1):
            return f"Tomorrow · {dt.strftime('%H:%M')}"
        return dt.strftime("%b %d · %H:%M")
    except ValueError:
        return dt_str


@app.template_filter("is_overdue")
def is_overdue(dt_str: str) -> bool:
    if not dt_str:
        return False
    try:
        return datetime.fromisoformat(dt_str) < datetime.now()
    except ValueError:
        return False


@app.template_filter("fmt_minutes")
def fmt_minutes(mins) -> str:
    if not mins:
        return ""
    mins = int(mins)
    if mins < 60:
        return f"{mins}m"
    h, m = divmod(mins, 60)
    return f"{h}h {m}m" if m else f"{h}h"


@app.template_filter("fmt_weekday")
def fmt_weekday(date_str: str) -> str:
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now().date()
        if d.date() == today:
            return "Today"
        if d.date() == today + timedelta(days=1):
            return "Tomorrow"
        return d.strftime("%a %b %d")
    except ValueError:
        return date_str


@app.template_filter("fmt_month_key")
def fmt_month_key(ym_str: str) -> str:
    try:
        return datetime.strptime(ym_str, "%Y-%m").strftime("%B %Y")
    except ValueError:
        return ym_str


@app.template_filter("fmt_hour")
def fmt_hour(h: int) -> str:
    if h == 0:
        return "12 AM"
    if h < 12:
        return f"{h} AM"
    if h == 12:
        return "12 PM"
    return f"{h - 12} PM"


def _build_ctx(**extra):
    habits = list_habits()
    insights = get_insights()
    pins = pinned_tasks()
    categories = list_categories()
    return dict(
        pins=pins,
        categories=categories,
        habits=habits,
        insights=insights,
        reminder_labels=LEADING_REMINDER_LABELS,
        scopes=SCOPES,
        duration_types=DURATION_TYPES,
        habit_colors=HABIT_COLORS,
        now=datetime.now(),
        has_ai=has_ai(),
        **extra,
    )


@app.get("/")
def index():
    handle_overdue_recurring()
    tab = request.args.get("tab", "tasks")
    category = request.args.get("category") or "all"
    show_completed = request.args.get("all") == "1"
    cat_filter = None if category == "all" else category
    current_view = request.args.get("view", "day")
    cal_view = request.args.get("calview", "month")
    selected_date = request.args.get("date")

    tasks = list_tasks(show_completed=show_completed, category=cat_filter)
    all_tasks = list_tasks(show_completed=True)
    habits = list_habits()

    view_data = {}
    if tab == "tasks":
        if current_view == "day":
            view_data = day_tasks(tasks, selected_date)
        elif current_view == "week":
            view_data = week_groups(tasks)
        elif current_view == "month":
            view_data = month_groups(tasks)
        elif current_view == "6m":
            view_data = sixmonth_groups(tasks)
        elif current_view == "year":
            view_data = year_groups(tasks)
    elif tab == "timeblock":
        view_data = timeblock_data(tasks, selected_date)
    elif tab == "report":
        view_data = compute_weekly_report(all_tasks, habits)

    ctx = _build_ctx(
        tasks=tasks,
        all_tasks=all_tasks,
        current_category=category,
        show_completed=show_completed,
        current_view=current_view,
        cal_view=cal_view,
        view_data=view_data,
        tab=tab,
        selected_date=selected_date,
    )
    return render_template("index.html", **ctx)


@app.post("/add")
def add():
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(request.referrer or url_for("index"))

    priority = request.form.get("priority", "medium")
    if priority not in _VALID_PRIORITIES:
        priority = "medium"

    category = request.form.get("category", "general").strip()
    new_cat = request.form.get("new_category", "").strip().lower()
    if new_cat:
        add_category(new_cat)
        category = new_cat

    due = request.form.get("due_datetime", "").strip() or None
    if due and not _DATETIME_RE.match(due):
        due = None

    recurring = request.form.get("recurring") or None
    if recurring not in _VALID_RECURRENCES:
        recurring = None

    leading = [r for r in request.form.getlist("leading") if r in LEADING_REMINDER_LABELS]
    scope = request.form.get("scope", "daily")
    if scope not in _VALID_SCOPES:
        scope = "daily"
    duration_type = request.form.get("duration_type", "quick")
    if duration_type not in _VALID_DURATIONS:
        duration_type = "quick"

    est = request.form.get("estimated_minutes", "").strip()
    estimated_minutes = int(est) if est.isdigit() else None

    start_date = request.form.get("start_date", "").strip() or None
    if start_date and not _DATE_RE.match(start_date):
        start_date = None

    try:
        subtasks = json.loads(request.form.get("subtasks_json", "[]"))
    except (ValueError, TypeError):
        subtasks = []

    add_task(title, category=category, due_datetime=due, priority=priority,
             recurring=recurring, leading_reminders=leading, scope=scope,
             duration_type=duration_type, estimated_minutes=estimated_minutes,
             start_date=start_date, subtasks=subtasks)

    return redirect(request.form.get("back", url_for("index")))


@app.post("/complete/<int:task_id>")
def complete(task_id: int):
    actual = request.form.get("actual_minutes", "").strip()
    actual_minutes = int(actual) if actual.isdigit() else None
    complete_task(task_id, actual_minutes=actual_minutes)
    return redirect(request.referrer or url_for("index"))


@app.post("/uncomplete/<int:task_id>")
def uncomplete(task_id: int):
    uncomplete_task(task_id)
    return redirect(request.referrer or url_for("index"))


@app.post("/delete/<int:task_id>")
def delete(task_id: int):
    delete_task(task_id)
    return redirect(request.referrer or url_for("index"))


@app.get("/task/<int:task_id>")
def task_json(task_id: int):
    for task in load_tasks():
        if task.id == task_id:
            return jsonify(task.to_dict())
    return jsonify({"error": "not found"}), 404


@app.post("/edit/<int:task_id>")
def edit(task_id: int):
    title = request.form.get("title", "").strip()
    if not title:
        return redirect(request.referrer or url_for("index"))

    priority = request.form.get("priority", "medium")
    if priority not in _VALID_PRIORITIES:
        priority = "medium"

    category = request.form.get("category", "general").strip()
    new_cat = request.form.get("new_category", "").strip().lower()
    if new_cat:
        add_category(new_cat)
        category = new_cat

    description = request.form.get("description", "").strip() or None
    due = request.form.get("due_datetime", "").strip() or ""
    if due and not _DATETIME_RE.match(due):
        due = ""
    recurring = request.form.get("recurring", "") or ""
    if recurring not in _VALID_RECURRENCES:
        recurring = ""
    leading = [r for r in request.form.getlist("leading") if r in LEADING_REMINDER_LABELS]
    scope = request.form.get("scope", "daily")
    if scope not in _VALID_SCOPES:
        scope = "daily"
    duration_type = request.form.get("duration_type", "quick")
    if duration_type not in _VALID_DURATIONS:
        duration_type = "quick"
    est = request.form.get("estimated_minutes", "").strip()
    estimated_minutes = int(est) if est.isdigit() else None
    start_date = request.form.get("start_date", "").strip() or None
    if start_date and not _DATE_RE.match(start_date):
        start_date = None
    try:
        subtasks = json.loads(request.form.get("subtasks_json", "null"))
    except (ValueError, TypeError):
        subtasks = None

    update_task(task_id, title=title, description=description, category=category,
                due_datetime=due, priority=priority, recurring=recurring,
                leading_reminders=leading, scope=scope, duration_type=duration_type,
                estimated_minutes=estimated_minutes, start_date=start_date,
                subtasks=subtasks)
    return redirect(request.referrer or url_for("index"))


@app.post("/task/<int:task_id>/reschedule")
@csrf.exempt
def reschedule(task_id: int):
    new_dt = request.json.get("due_datetime", "") if request.is_json else ""
    if new_dt and _DATETIME_RE.match(new_dt):
        update_task(task_id, due_datetime=new_dt)
        return jsonify({"ok": True})
    return jsonify({"error": "invalid datetime"}), 400


@app.post("/subtask/<int:task_id>/<int:idx>/toggle")
def subtask_toggle(task_id: int, idx: int):
    toggle_subtask(task_id, idx)
    return redirect(request.referrer or url_for("index"))


@app.post("/categories/add")
def category_add():
    name = request.form.get("name", "").strip().lower()
    if name:
        add_category(name)
    return redirect(request.referrer or url_for("index"))


@app.post("/categories/delete/<name>")
def category_delete(name: str):
    delete_category(name)
    return redirect(url_for("index"))


@app.post("/habits/add")
def habit_add():
    title = request.form.get("title", "").strip()
    if title:
        add_habit(
            title=title,
            category=request.form.get("category", "general"),
            frequency=request.form.get("frequency", "daily"),
            color=request.form.get("color", "sage"),
        )
    return redirect(url_for("index", tab="habits"))


@app.post("/habits/<int:habit_id>/complete")
def habit_complete(habit_id: int):
    complete_habit(habit_id)
    return redirect(request.referrer or url_for("index", tab="habits"))


@app.post("/habits/<int:habit_id>/uncomplete")
def habit_uncomplete(habit_id: int):
    uncomplete_habit(habit_id)
    return redirect(request.referrer or url_for("index", tab="habits"))


@app.post("/habits/<int:habit_id>/delete")
def habit_delete(habit_id: int):
    delete_habit(habit_id)
    return redirect(url_for("index", tab="habits"))


@app.post("/habits/<int:habit_id>/edit")
def habit_edit(habit_id: int):
    update_habit(
        habit_id,
        title=request.form.get("title", "").strip() or None,
        category=request.form.get("category"),
        frequency=request.form.get("frequency"),
        color=request.form.get("color"),
    )
    return redirect(url_for("index", tab="habits"))


@app.get("/suggest-subtasks")
def suggest():
    title = request.args.get("title", "")
    duration_type = request.args.get("duration_type", "medium")
    return jsonify(suggest_subtasks(title, duration_type))


@app.get("/ai/schedule-suggest")
def ai_schedule():
    tasks = list_tasks(show_completed=False)
    unscheduled = [t for t in tasks if not t.due_datetime]
    insights = get_insights()
    suggestions = schedule_suggest(unscheduled, insights)
    return jsonify({"suggestions": suggestions, "tasks": [t.to_dict() for t in unscheduled]})


@app.post("/ai/weekly-report/start")
def ai_report_start():
    all_tasks = list_tasks(show_completed=True)
    habits = list_habits()
    report_data = compute_weekly_report(all_tasks, habits)
    job_id = str(uuid.uuid4())
    if len(_ai_jobs) > 50:
        for k in list(_ai_jobs.keys())[:25]:
            del _ai_jobs[k]
    _ai_jobs[job_id] = {"status": "running"}

    def _run():
        try:
            insight = weekly_report_insight(report_data)
            _ai_jobs[job_id] = {"status": "done", "insight": insight}
        except Exception:
            _ai_jobs[job_id] = {"status": "error", "insight": "Analysis unavailable."}

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.get("/ai/weekly-report/poll/<job_id>")
def ai_report_poll(job_id: str):
    job = _ai_jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify(job)


def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    app.run(host=host, port=port)
