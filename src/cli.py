import argparse
import re
import sys

from src.daemon import run as run_daemon
from src.tasks import add_task, complete_task, delete_task, list_tasks
from src.web import run as run_web


def _validate_time(value: str) -> str:
    if not re.match(r"^\d{2}:\d{2}$", value):
        raise argparse.ArgumentTypeError("Time must be in HH:MM format (e.g. 09:30)")
    h, m = int(value[:2]), int(value[3:])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise argparse.ArgumentTypeError("Invalid time value")
    return value


_PRIORITY_LABEL = {"high": "[!]", "medium": "[-]", "low": "[.]"}


def _print_tasks(tasks) -> None:
    if not tasks:
        print("No tasks.")
        return
    for t in tasks:
        status = "[x]" if t.completed else "[ ]"
        priority = _PRIORITY_LABEL.get(t.priority, "[-]")
        reminder = f"  (remind {t.reminder_time})" if t.reminder_time else ""
        print(f"  {status} {priority} #{t.id} {t.title}{reminder}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="todo", description="To-do list with reminders")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add a task")
    add_p.add_argument("title", help="Task title")
    add_p.add_argument("--remind", metavar="HH:MM", type=_validate_time, help="Reminder time")
    add_p.add_argument("--priority", choices=["high", "medium", "low"], default="medium", help="Priority level")

    complete_p = sub.add_parser("complete", help="Mark a task complete")
    complete_p.add_argument("id", type=int, help="Task ID")

    delete_p = sub.add_parser("delete", help="Delete a task")
    delete_p.add_argument("id", type=int, help="Task ID")

    list_p = sub.add_parser("list", help="List tasks")
    list_p.add_argument("--all", action="store_true", help="Include completed tasks")

    sub.add_parser("daemon", help="Start the reminder daemon")

    web_p = sub.add_parser("web", help="Start the web dashboard")
    web_p.add_argument("--port", type=int, default=8080, help="Port to listen on")

    args = parser.parse_args()

    if args.command == "add":
        task = add_task(args.title, args.remind, args.priority)
        reminder_note = f" (reminder at {task.reminder_time})" if task.reminder_time else ""
        print(f"Added #{task.id}: [{task.priority}] {task.title}{reminder_note}")

    elif args.command == "complete":
        task = complete_task(args.id)
        if task:
            print(f"Completed #{task.id}: {task.title}")
        else:
            print(f"Task #{args.id} not found.", file=sys.stderr)
            sys.exit(1)

    elif args.command == "delete":
        if delete_task(args.id):
            print(f"Deleted #{args.id}")
        else:
            print(f"Task #{args.id} not found.", file=sys.stderr)
            sys.exit(1)

    elif args.command == "list":
        tasks = list_tasks(show_completed=args.all)
        _print_tasks(tasks)

    elif args.command == "daemon":
        run_daemon()

    elif args.command == "web":
        print(f"Dashboard running at http://127.0.0.1:{args.port}")
        run_web(port=args.port)


if __name__ == "__main__":
    main()
