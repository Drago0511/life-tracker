from unittest.mock import patch

from src.daemon import _notified, check_reminders
from src.models import Task


@patch("src.daemon.notify")
@patch("src.daemon.load_tasks")
def test_notifies_at_due_time(mock_load, mock_notify):
    _notified.clear()
    task = Task(id=1, title="Stand-up", due_datetime="2026-06-01T09:00")
    mock_load.return_value = [task]
    with patch("src.daemon.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-06-01T09:00"
        check_reminders()
    mock_notify.assert_called_once_with("Due now", "Stand-up")


@patch("src.daemon.notify")
@patch("src.daemon.load_tasks")
def test_no_duplicate_notification(mock_load, mock_notify):
    _notified.clear()
    task = Task(id=1, title="Stand-up", due_datetime="2026-06-01T09:00")
    mock_load.return_value = [task]
    with patch("src.daemon.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-06-01T09:00"
        check_reminders()
        check_reminders()
    assert mock_notify.call_count == 1


@patch("src.daemon.notify")
@patch("src.daemon.load_tasks")
def test_skips_completed_tasks(mock_load, mock_notify):
    _notified.clear()
    task = Task(id=2, title="Done", due_datetime="2026-06-01T09:00", completed=True)
    mock_load.return_value = [task]
    with patch("src.daemon.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-06-01T09:00"
        check_reminders()
    mock_notify.assert_not_called()


@patch("src.daemon.notify")
@patch("src.daemon.load_tasks")
def test_no_notify_wrong_time(mock_load, mock_notify):
    _notified.clear()
    task = Task(id=3, title="Later", due_datetime="2026-06-01T15:00")
    mock_load.return_value = [task]
    with patch("src.daemon.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-06-01T09:00"
        check_reminders()
    mock_notify.assert_not_called()
