"""Module de gestion de la mémoire (court terme et long terme)."""

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types de mémoire."""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


@dataclass
class Memory:
    """Mémoire stockée."""
    id: str
    session_id: str
    memory_type: MemoryType
    content: str
    tags: list[str]
    created_at: datetime
    last_accessed: Optional[datetime] = None


class MemoryEntry(BaseModel):
    """Entrée de mémoire pour création."""
    content: str
    tags: list[str] = Field(default_factory=list)
    memory_type: MemoryType = MemoryType.SHORT_TERM


class MemoryManager:
    """Gestionnaire de mémoire pour stocker et récupérer les informations."""

    def __init__(self, db_path: str) -> None:
        """Initialise le gestionnaire de mémoire.

        Args:
            db_path: Chemin vers la base de données SQLite.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialise la table mémoire si elle n'existe pas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS memoire (
                    id TEXT PRIMARY KEY,
                    id_session TEXT NOT NULL,
                    type TEXT NOT NULL,
                    contenu TEXT NOT NULL,
                    tags TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP,
                    FOREIGN KEY (id_session) REFERENCES session(id)
                )
                """
            )
            conn.commit()

    def add_memory(
        self,
        session_id: str,
        entry: MemoryEntry,
    ) -> str:
        """Ajoute une mémoire à la base de données.

        Args:
            session_id: ID de la session.
            entry: Entrée de mémoire à ajouter.

        Returns:
            ID de la mémoire créée.
        """
        memory_id = str(uuid.uuid4())
        tags_json = json.dumps(entry.tags)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memoire (id, id_session, type, contenu, tags)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    session_id,
                    entry.memory_type.value,
                    entry.content,
                    tags_json,
                ),
            )
            conn.commit()

        logger.info(f"Mémoire ajoutée: {memory_id} (type: {entry.memory_type.value})")
        return memory_id

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Récupère une mémoire par son ID.

        Args:
            memory_id: ID de la mémoire.

        Returns:
            La mémoire si trouvée, None sinon.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM memoire WHERE id = ?",
                (memory_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            # Mettre à jour last_accessed
            cursor.execute(
                "UPDATE memoire SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                (memory_id,),
            )
            conn.commit()

            return self._row_to_memory(row)

    def get_session_memories(
        self,
        session_id: str,
        memory_type: Optional[MemoryType] = None,
    ) -> list[Memory]:
        """Récupère toutes les mémoires d'une session.

        Args:
            session_id: ID de la session.
            memory_type: Type de mémoire à filtrer (optionnel).

        Returns:
            Liste des mémoires.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if memory_type:
                cursor.execute(
                    "SELECT * FROM memoire WHERE id_session = ? AND type = ? ORDER BY created_at DESC",
                    (session_id, memory_type.value),
                )
            else:
                cursor.execute(
                    "SELECT * FROM memoire WHERE id_session = ? ORDER BY created_at DESC",
                    (session_id,),
                )

            rows = cursor.fetchall()
            return [self._row_to_memory(row) for row in rows]

    def search_memories(
        self,
        session_id: str,
        query: str,
        memory_type: Optional[MemoryType] = None,
    ) -> list[Memory]:
        """Recherche des mémoires par contenu ou tags.

        Args:
            session_id: ID de la session.
            query: Recherche textuelle.
            memory_type: Type de mémoire à filtrer (optionnel).

        Returns:
            Liste des mémoires correspondantes.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            query_pattern = f"%{query}%"

            if memory_type:
                cursor.execute(
                    """
                    SELECT * FROM memoire
                    WHERE id_session = ? AND type = ?
                    AND (contenu LIKE ? OR tags LIKE ?)
                    ORDER BY created_at DESC
                    """,
                    (session_id, memory_type.value, query_pattern, query_pattern),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM memoire
                    WHERE id_session = ?
                    AND (contenu LIKE ? OR tags LIKE ?)
                    ORDER BY created_at DESC
                    """,
                    (session_id, query_pattern, query_pattern),
                )

            rows = cursor.fetchall()
            return [self._row_to_memory(row) for row in rows]

    def delete_memory(self, memory_id: str) -> bool:
        """Supprime une mémoire.

        Args:
            memory_id: ID de la mémoire à supprimer.

        Returns:
            True si supprimée, False sinon.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memoire WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_memory(self, row: tuple) -> Memory:
        """Convertit une ligne de base de données en objet Memory.

        Args:
            row: Tuple de la base de données.

        Returns:
            Objet Memory.
        """
        tags = json.loads(row[4]) if row[4] else []
        created_at = datetime.fromisoformat(row[5])
        last_accessed = datetime.fromisoformat(row[6]) if row[6] else None

        return Memory(
            id=row[0],
            session_id=row[1],
            memory_type=MemoryType(row[2]),
            content=row[3],
            tags=tags,
            created_at=created_at,
            last_accessed=last_accessed,
        )
