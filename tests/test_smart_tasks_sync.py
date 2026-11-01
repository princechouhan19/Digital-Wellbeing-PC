"""
test_smart_tasks_sync.py — Unit tests for Smart Tasks & Dynamic Island synchronization,
exact scheduled time support, and target application selection.
"""
from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import QApplication

from database.repository import Repository
from ui.pages.tasks import TaskCreateDialog, TaskCard
from ui.widgets.ambient_notch import AmbientNotch


def test_repository_smart_task_scheduled_time(qtbot):
    repo = Repository()
    task_id = repo.add_smart_task(
        title="5:50 PM Gym",
        priority=1,
        estimated_minutes=45,
        target_processes=["spotify.exe"],
        scheduled_time="5:50 PM",
    )
    assert task_id > 0

    task = repo.get_smart_task(task_id)
    assert task is not None
    assert task["title"] == "5:50 PM Gym"
    assert task["priority"] == 1
    assert task["estimated_minutes"] == 45
    assert task["scheduled_time"] == "5:50 PM"
    assert "spotify.exe" in task["target_processes"]

    # Clean up
    repo.delete_smart_task(task_id)
    assert repo.get_smart_task(task_id) is None


def test_task_create_dialog_data(qtbot):
    dialog = TaskCreateDialog()
    qtbot.addWidget(dialog)

    # Set title
    dialog._title_edit.setText("Gym & Health Workout")
    # Set time
    dialog._time_check.setChecked(True)
    dialog._time_edit.setTime(QTime(17, 50))
    # Add application via quick selector
    dialog._add_app_chip("chrome.exe", "Google Chrome")
    dialog._add_app_chip("spotify.exe", "Spotify")

    data = dialog.get_data()
    assert data["title"] == "Gym & Health Workout"
    assert data["scheduled_time"] == "5:50 PM"
    assert "chrome.exe" in data["target_processes"]
    assert "spotify.exe" in data["target_processes"]
    assert data["estimated_minutes"] == 25


def test_dynamic_island_tasks_sync(qtbot):
    repo = Repository()
    # Add a test task into the database
    t_id = repo.add_smart_task(
        title="Dynamic Sync Task",
        priority=1,
        estimated_minutes=30,
        scheduled_time="6:15 PM",
        target_processes=["code.exe"],
    )

    notch = AmbientNotch()
    qtbot.addWidget(notch)

    # Notch calendar panel should load from repo
    notch.refresh_calendar_panel()
    assert notch.ev_count_label.text() != "0 tasks"

    # Check edit list has our task
    found = False
    for i in range(notch.edit_list.count()):
        item = notch.edit_list.item(i)
        if "Dynamic Sync Task" in item.text():
            found = True
            break
    assert found, "Task from repository should appear in Dynamic Island task list"

    # Test adding a task directly from Dynamic Island
    notch.edit_name.setText("Notch Created Task")
    notch.edit_time.setText("7:00 PM")
    notch.add_task_integrated()

    # Verify task was written to SQLite repository
    tasks = repo.get_smart_tasks()
    created_task = next((t for t in tasks if t["title"] == "Notch Created Task"), None)
    assert created_task is not None
    assert created_task["scheduled_time"] == "7:00 PM"

    # Clean up
    repo.delete_smart_task(t_id)
    if created_task:
        repo.delete_smart_task(created_task["id"])
