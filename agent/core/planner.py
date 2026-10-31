"""Module de planification pour décomposer les tâches en sous-tâches."""

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Statuts des tâches."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Tâche à exécuter."""
    id: str
    session_id: str
    parent_id: Optional[str]
    description: str
    status: TaskStatus
    order: int
    created_at: datetime
    completed_at: Optional[datetime] = None


class TaskEntry(BaseModel):
    """Entrée de tâche pour création."""
    description: str
    parent_id: Optional[str] = None
    order: int = 0


class TaskPlanner:
    """Planificateur de tâches pour décomposer les instructions en sous-tâches."""

    def __init__(self, db_path: str) -> None:
        """Initialise le planificateur de tâches.

        Args:
            db_path: Chemin vers la base de données SQLite.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialise la table tâche si elle n'existe pas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tache (
                    id TEXT PRIMARY KEY,
                    id_session TEXT NOT NULL,
                    id_parent TEXT,
                    description TEXT NOT NULL,
                    statut TEXT NOT NULL DEFAULT 'pending',
                    ordre INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (id_session) REFERENCES session(id),
                    FOREIGN KEY (id_parent) REFERENCES tache(id)
                )
                """
            )
            conn.commit()

    def plan_task(
        self,
        session_id: str,
        instruction: str,
        llm_analyzer=None,
    ) -> list[Task]:
        """Décompose une instruction en sous-tâches.

        Args:
            session_id: ID de la session.
            instruction: Instruction en langage naturel.
            llm_analyzer: Optionnel. Objet pour générer les sous-tâches.

        Returns:
            Liste des sous-tâches créées.
        """
        logger.info(f"Planification de la tâche: {instruction}")

        subtasks = []
        if llm_analyzer:
            prompt = f"""Décompose l'instruction suivante en une liste ordonnée de sous-tâches simples.\nInstruction : {instruction}\nRéponds UNIQUEMENT avec un tableau JSON de chaînes de caractères, ex: ["Ouvrir le navigateur", "Rechercher le terme", "Copier le résultat"]. Si la tâche est trop simple et ne nécessite pas de décomposition, renvoie un tableau avec une seule entrée."""
            try:
                import json
                response = llm_analyzer.generate_text(prompt)
                json_str = response.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:-3].strip()
                elif json_str.startswith("```"):
                    json_str = json_str[3:-3].strip()
                subtasks = json.loads(json_str)
            except Exception as e:
                logger.error(f"Erreur lors de la décomposition: {e}")

        if not subtasks or not isinstance(subtasks, list):
            subtasks = [instruction]

        tasks_created = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for i, desc in enumerate(subtasks):
                task_id = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO tache (id, id_session, description, statut, ordre)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (task_id, session_id, desc, TaskStatus.PENDING.value, i),
                )
                tasks_created.append(task_id)
            conn.commit()

        return [self.get_task(tid) for tid in tasks_created if self.get_task(tid) is not None]

    def add_subtask(
        self,
        session_id: str,
        parent_id: str,
        description: str,
        order: int,
    ) -> Optional[Task]:
        """Ajoute une sous-tâche à une tâche existante.

        Args:
            session_id: ID de la session.
            parent_id: ID de la tâche parente.
            description: Description de la sous-tâche.
            order: Ordre d'exécution.

        Returns:
            La sous-tâche créée.
        """
        subtask_id = str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tache (id, id_session, id_parent, description, statut, ordre)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    subtask_id,
                    session_id,
                    parent_id,
                    description,
                    TaskStatus.PENDING.value,
                    order,
                ),
            )
            conn.commit()

        logger.info(f"Sous-tâche ajoutée: {subtask_id}")
        return self.get_task(subtask_id)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Récupère une tâche par son ID.

        Args:
            task_id: ID de la tâche.

        Returns:
            La tâche si trouvée, None sinon.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tache WHERE id = ?", (task_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_task(row)

    def get_session_tasks(
        self,
        session_id: str,
        status: Optional[TaskStatus] = None,
    ) -> list[Task]:
        """Récupère toutes les tâches d'une session.

        Args:
            session_id: ID de la session.
            status: Statut à filtrer (optionnel).

        Returns:
            Liste des tâches.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if status:
                cursor.execute(
                    "SELECT * FROM tache WHERE id_session = ? AND statut = ? ORDER BY ordre",
                    (session_id, status.value),
                )
            else:
                cursor.execute(
                    "SELECT * FROM tache WHERE id_session = ? ORDER BY ordre",
                    (session_id,),
                )

            rows = cursor.fetchall()
            return [self._row_to_task(row) for row in rows]

    def get_subtasks(self, parent_id: str) -> list[Task]:
        """Récupère les sous-tâches d'une tâche.

        Args:
            parent_id: ID de la tâche parente.

        Returns:
            Liste des sous-tâches.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tache WHERE id_parent = ? ORDER BY ordre",
                (parent_id,),
            )
            rows = cursor.fetchall()
            return [self._row_to_task(row) for row in rows]

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
    ) -> bool:
        """Met à jour le statut d'une tâche.

        Args:
            task_id: ID de la tâche.
            status: Nouveau statut.

        Returns:
            True si mis à jour, False sinon.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if status == TaskStatus.COMPLETED:
                cursor.execute(
                    "UPDATE tache SET statut = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status.value, task_id),
                )
            else:
                cursor.execute(
                    "UPDATE tache SET statut = ? WHERE id = ?",
                    (status.value, task_id),
                )

            conn.commit()
            return cursor.rowcount > 0

    def get_next_pending_task(self, session_id: str) -> Optional[Task]:
        """Récupère la prochaine tâche en attente.

        Args:
            session_id: ID de la session.

        Returns:
            La prochaine tâche en attente ou None.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM tache
                WHERE id_session = ? AND statut = ?
                ORDER BY ordre ASC
                LIMIT 1
                """,
                (session_id, TaskStatus.PENDING.value),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_task(row)

    def _row_to_task(self, row: tuple) -> Task:
        """Convertit une ligne de base de données en objet Task.

        Args:
            row: Tuple de la base de données.

        Returns:
            Objet Task.
        """
        created_at = datetime.fromisoformat(row[6])
        completed_at = datetime.fromisoformat(row[7]) if row[7] else None

        return Task(
            id=row[0],
            session_id=row[1],
            parent_id=row[2],
            description=row[3],
            status=TaskStatus(row[4]),
            order=row[5],
            created_at=created_at,
            completed_at=completed_at,
        )
