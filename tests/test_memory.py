"""Tests pour le module de mémoire."""

import pytest

from agent.core.memory import MemoryEntry, MemoryManager, MemoryType


@pytest.fixture
def memory_manager(tmp_path) -> MemoryManager:
    """Fixture pour créer un gestionnaire de mémoire avec une DB temporaire."""
    db_path = str(tmp_path / "test.db")
    return MemoryManager(db_path)


def test_add_memory(memory_manager: MemoryManager) -> None:
    """Test l'ajout d'une mémoire."""
    session_id = "test-session-123"
    entry = MemoryEntry(
        content="Test de mémoire",
        tags=["test"],
        memory_type=MemoryType.SHORT_TERM,
    )

    memory_id = memory_manager.add_memory(session_id, entry)

    assert memory_id is not None

    memory = memory_manager.get_memory(memory_id)
    assert memory is not None
    assert memory.content == "Test de mémoire"
    assert memory.tags == ["test"]


def test_get_session_memories(memory_manager: MemoryManager) -> None:
    """Test la récupération des mémoires d'une session."""
    session_id = "test-session-123"

    memory_manager.add_memory(
        session_id,
        MemoryEntry(content="Mémoire 1", memory_type=MemoryType.SHORT_TERM),
    )
    memory_manager.add_memory(
        session_id,
        MemoryEntry(content="Mémoire 2", memory_type=MemoryType.LONG_TERM),
    )

    memories = memory_manager.get_session_memories(session_id)

    assert len(memories) == 2


def test_search_memories(memory_manager: MemoryManager) -> None:
    """Test la recherche de mémoires."""
    session_id = "test-session-123"

    memory_manager.add_memory(
        session_id,
        MemoryEntry(content="Chrome est ouvert", tags=["chrome"]),
    )
    memory_manager.add_memory(
        session_id,
        MemoryEntry(content="Excel est fermé", tags=["excel"]),
    )

    results = memory_manager.search_memories(session_id, "chrome")

    assert len(results) == 1
    assert "chrome" in results[0].content.lower()


def test_delete_memory(memory_manager: MemoryManager) -> None:
    """Test la suppression d'une mémoire."""
    session_id = "test-session-123"
    memory_id = memory_manager.add_memory(
        session_id,
        MemoryEntry(content="À supprimer"),
    )

    deleted = memory_manager.delete_memory(memory_id)

    assert deleted is True

    memory = memory_manager.get_memory(memory_id)
    assert memory is None
