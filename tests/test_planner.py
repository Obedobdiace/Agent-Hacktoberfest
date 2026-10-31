"""Tests pour le module de planification."""

import pytest

from agent.core.planner import TaskPlanner, TaskStatus


@pytest.fixture
def planner(tmp_path) -> TaskPlanner:
    """Fixture pour créer un planificateur avec une DB temporaire."""
    db_path = str(tmp_path / "test.db")
    return TaskPlanner(db_path)


def test_plan_task(planner: TaskPlanner) -> None:
    """Test la planification d'une tâche."""
    session_id = "test-session-123"
    instruction = "Ouvrir Chrome et aller sur google.com"

    tasks = planner.plan_task(session_id, instruction)

    assert len(tasks) == 1
    assert tasks[0].description == instruction
    assert tasks[0].status == TaskStatus.PENDING
    assert tasks[0].session_id == session_id


def test_add_subtask(planner: TaskPlanner) -> None:
    """Test l'ajout d'une sous-tâche."""
    session_id = "test-session-123"
    parent_task = planner.plan_task(session_id, "Tâche principale")[0]

    subtask = planner.add_subtask(
        session_id,
        parent_task.id,
        "Sous-tâche 1",
        order=1,
    )

    assert subtask is not None
    assert subtask.description == "Sous-tâche 1"
    assert subtask.parent_id == parent_task.id
    assert subtask.order == 1


def test_update_task_status(planner: TaskPlanner) -> None:
    """Test la mise à jour du statut d'une tâche."""
    session_id = "test-session-123"
    task = planner.plan_task(session_id, "Tâche test")[0]

    updated = planner.update_task_status(task.id, TaskStatus.IN_PROGRESS)

    assert updated is True

    updated_task = planner.get_task(task.id)
    assert updated_task is not None
    assert updated_task.status == TaskStatus.IN_PROGRESS


def test_get_next_pending_task(planner: TaskPlanner) -> None:
    """Test la récupération de la prochaine tâche en attente."""
    session_id = "test-session-123"
    planner.plan_task(session_id, "Tâche 1")
    planner.plan_task(session_id, "Tâche 2")

    next_task = planner.get_next_pending_task(session_id)

    assert next_task is not None
    assert next_task.status == TaskStatus.PENDING
