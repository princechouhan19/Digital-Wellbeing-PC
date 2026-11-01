"""
test_smart_tasks_sync.py — Unit tests for Smart Tasks 2.0, exact start/end times,
templates, day-by-day notes, water intake tracking, and Dynamic Island synchronization.
"""
from datetime import datetime
from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import QApplication

from database.repository import Repository
from ui.pages.tasks import TaskEditDialog, TaskCreateDialog, TaskCard
from ui.widgets.ambient_notch import AmbientNotch


def test_repository_smart_task_strict_scheduling(qtbot):
    repo = Repository()
    task_id = repo.add_smart_task(
        title="5:50 PM Gym Routine",
        category="Health",
        priority=1,
        estimated_minutes=70,
        start_time="5:50 PM",
        end_time="7:00 PM",
        scheduled_time="5:50 PM – 7:00 PM",
        repeat_days=[0, 1, 2, 3, 4, 5],
        day_notes_json={
            "0": "Chest + Biceps + Forearms",
            "1": "Back + Triceps + Traps",
        },
        target_processes=["spotify.exe"],
    )
    assert task_id > 0

    task = repo.get_smart_task(task_id)
    assert task is not None
    assert task["title"] == "5:50 PM Gym Routine"
    assert task["start_time"] == "5:50 PM"
    assert task["end_time"] == "7:00 PM"
    assert task["repeat_days"] == [0, 1, 2, 3, 4, 5]
    assert task["day_notes_json"]["0"] == "Chest + Biceps + Forearms"

    # Test update
    ok = repo.update_smart_task(
        task_id=task_id,
        title="Updated Gym Routine",
        category="Fitness",
        priority=1,
        estimated_minutes=75,
        start_time="6:00 PM",
        end_time="7:15 PM",
        scheduled_time="6:00 PM – 7:15 PM",
        repeat_days=[0, 1, 2, 3, 4],
        day_notes_json={"0": "Chest Only"},
        target_processes=["spotify.exe"],
    )
    assert ok is True
    updated = repo.get_smart_task(task_id)
    assert updated["title"] == "Updated Gym Routine"
    assert updated["start_time"] == "6:00 PM"
    assert updated["repeat_days"] == [0, 1, 2, 3, 4]

    # Clean up
    repo.delete_smart_task(task_id)
    assert repo.get_smart_task(task_id) is None


def test_gym_template_and_dialog(qtbot):
    dialog = TaskEditDialog()
    qtbot.addWidget(dialog)

    # Click Gym template
    dialog._apply_gym_template()
    data = dialog.get_data()

    assert data["title"] == "Gym Session"
    assert data["category"] == "Health"
    assert data["start_time"] == "5:50 PM"
    assert data["end_time"] == "7:00 PM"
    assert data["estimated_minutes"] == 70
    assert 0 in data["repeat_days"]
    assert "Chest + Biceps + Forearms" in data["day_notes_json"]["0"]
    assert "spotify.exe" in data["target_processes"]


def test_college_template_and_dialog(qtbot):
    dialog = TaskEditDialog()
    qtbot.addWidget(dialog)

    # Click College template
    dialog._apply_college_template()
    data = dialog.get_data()

    assert "College" in data["title"]
    assert data["category"] == "Study"
    assert data["start_time"] == "9:00 AM"
    assert data["end_time"] == "4:00 PM"
    assert data["repeat_days"] == [0, 1, 2, 3, 4]
    assert "Instagram API" in data["day_notes_json"]["0"]


def test_water_intake_tracking():
    repo = Repository()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Reset initial state
    repo.reset_water_intake(today_str)
    initial = repo.get_water_intake(today_str)
    assert initial["current_ml"] == 0

    # Add 500 ml checkpoint
    r1 = repo.add_water_intake(500, today_str)
    assert r1["current_ml"] == 500
    assert len(r1["checkpoints"]) == 1

    # Add 1000 ml checkpoint
    r2 = repo.add_water_intake(1000, today_str)
    assert r2["current_ml"] == 1500
    assert len(r2["checkpoints"]) == 2

    # Reset
    repo.reset_water_intake(today_str)
    res = repo.get_water_intake(today_str)
    assert res["current_ml"] == 0


def test_monthly_task_stats():
    repo = Repository()
    stats = repo.get_monthly_task_stats()
    assert len(stats) >= 28
    assert "completion_rate" in stats[0]
    assert "is_today" in stats[0]


def test_dynamic_island_tasks_sync(qtbot):
    repo = Repository()
    t_id = repo.add_smart_task(
        title="Dynamic Sync Task",
        priority=1,
        estimated_minutes=30,
        start_time="6:15 PM",
        scheduled_time="6:15 PM",
        day_notes_json={"0": "Dynamic test note"},
        target_processes=["code.exe"],
    )

    notch = AmbientNotch()
    qtbot.addWidget(notch)

    # Refresh calendar panel
    notch.refresh_calendar_panel()
    assert notch.ev_count_label.text() != "0 tasks"

    # Test adding a task directly from Dynamic Island
    notch.edit_name.setText("Notch Created Task")
    notch.edit_time.setText("7:00 PM")
    notch.add_task_integrated()

    tasks = repo.get_smart_tasks()
    created_task = next((t for t in tasks if t["title"] == "Notch Created Task"), None)
    assert created_task is not None
    assert created_task["scheduled_time"] == "7:00 PM"

    # Clean up
    repo.delete_smart_task(t_id)
    if created_task:
        repo.delete_smart_task(created_task["id"])
