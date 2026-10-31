"""Modèles de base de données et gestionnaire."""

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Statuts de session."""
    EN_COURS = "en_cours"
    TERMINEE = "terminee"
    ANNULEE = "annulee"
    ERREUR = "erreur"


@dataclass
class Session:
    """Session de l'agent."""
    id: str
    debut: datetime
    fin: Optional[datetime]
    instruction_initiale: str
    statut: SessionStatus
    readonly_mode: bool


@dataclass
class ActionRecord:
    """Enregistrement d'action."""
    id: str
    task_id: str
    action_type: str
    parameters: str
    security_level: str
    user_approved: Optional[bool]
    blocked_reason: Optional[str]
    resultat: Optional[str]
    timestamp: datetime


class DatabaseManager:
    """Gestionnaire de base de données SQLite."""

    def __init__(self, db_path: str) -> None:
        """Initialise le gestionnaire de base de données.

        Args:
            db_path: Chemin vers le fichier SQLite.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialise toutes les tables si elles n'existent pas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Table session
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session (
                    id TEXT PRIMARY KEY,
                    debut TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    fin TIMESTAMP,
                    instruction_initiale TEXT NOT NULL,
                    statut TEXT NOT NULL DEFAULT 'en_cours',
                    readonly_mode BOOLEAN DEFAULT 0
                )
                """
            )

            # Table tache
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

            # Table action
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS action (
                    id TEXT PRIMARY KEY,
                    id_tache TEXT NOT NULL,
                    type_action TEXT NOT NULL,
                    parametres TEXT NOT NULL,
                    security_level TEXT NOT NULL,
                    user_approved BOOLEAN,
                    blocked_reason TEXT,
                    resultat TEXT,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_tache) REFERENCES tache(id)
                )
                """
            )

            # Table capture
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS capture (
                    id TEXT PRIMARY KEY,
                    id_action TEXT,
                    chemin_fichier TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ocr_resultat TEXT,
                    FOREIGN KEY (id_action) REFERENCES action(id)
                )
                """
            )

            # Table memoire
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

            # Table note_obsidian
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS note_obsidian (
                    id TEXT PRIMARY KEY,
                    id_session TEXT NOT NULL,
                    chemin_fichier TEXT NOT NULL,
                    type_note TEXT NOT NULL,
                    titre TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_session) REFERENCES session(id)
                )
                """
            )

            # Table connaissance
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS connaissance (
                    id TEXT PRIMARY KEY,
                    application TEXT NOT NULL,
                    categorie TEXT NOT NULL,
                    titre TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    embedding_id TEXT
                )
                """
            )

            # Créer les index
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tache_session ON tache(id_session)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tache_parent ON tache(id_parent)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_action_tache ON action(id_tache)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_capture_action ON capture(id_action)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memoire_session ON memoire(id_session)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_note_session ON note_obsidian(id_session)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_connaissance_app ON connaissance(application)")

            conn.commit()

        logger.info("Base de données initialisée")

    def create_session(
        self,
        instruction: str,
        readonly_mode: bool = False,
    ) -> str:
        """Crée une nouvelle session.

        Args:
            instruction: Instruction initiale.
            readonly_mode: Mode lecture seule.

        Returns:
            ID de la session créée.
        """
        session_id = str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO session (id, instruction_initiale, readonly_mode)
                VALUES (?, ?, ?)
                """,
                (session_id, instruction, readonly_mode),
            )
            conn.commit()

        logger.info(f"Session créée: {session_id}")
        return session_id

    def log_action(
        self,
        task_id: str,
        action_type: str,
        parameters: str,
        security_level: str,
        user_approved: Optional[bool] = None,
        blocked_reason: Optional[str] = None,
        resultat: Optional[str] = None,
    ) -> str:
        """Log une action dans la base de données.

        Args:
            task_id: ID de la tâche.
            action_type: Type de l'action.
            parameters: Paramètres JSON.
            security_level: Niveau de sécurité.
            user_approved: Si l'utilisateur a approuvé.
            blocked_reason: Raison du blocage.
            resultat: Résultat de l'action.

        Returns:
            ID de l'action créée.
        """
        action_id = str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO action
                (id, id_tache, type_action, parametres, security_level, user_approved, blocked_reason, resultat)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_id,
                    task_id,
                    action_type,
                    parameters,
                    security_level,
                    user_approved,
                    blocked_reason,
                    resultat,
                ),
            )
            conn.commit()

        return action_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """Récupère une session par son ID.

        Args:
            session_id: ID de la session.

        Returns:
            Session si trouvée, None sinon.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM session WHERE id = ?", (session_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return Session(
                id=row[0],
                debut=datetime.fromisoformat(row[1]),
                fin=datetime.fromisoformat(row[2]) if row[2] else None,
                instruction_initiale=row[3],
                statut=SessionStatus(row[4]),
                readonly_mode=bool(row[5]),
            )

    def get_session_actions(self, session_id: str) -> list[ActionRecord]:
        """Récupère toutes les actions d'une session.

        Args:
            session_id: ID de la session.

        Returns:
            Liste des actions.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT a.* FROM action a
                JOIN tache t ON a.id_tache = t.id
                WHERE t.id_session = ?
                ORDER BY a.timestamp
                """,
                (session_id,),
            )
            rows = cursor.fetchall()

            return [
                ActionRecord(
                    id=row[0],
                    task_id=row[1],
                    action_type=row[2],
                    parameters=row[3],
                    security_level=row[4],
                    user_approved=row[5],
                    blocked_reason=row[6],
                    resultat=row[7],
                    timestamp=datetime.fromisoformat(row[8]),
                )
                for row in rows
            ]
