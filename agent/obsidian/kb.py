"""Module de base de connaissances pour Obsidian."""

import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Base de connaissances structurée."""

    def __init__(self, db_path: str, vault_path: str) -> None:
        """Initialise la base de connaissances.

        Args:
            db_path: Chemin vers la base de données SQLite.
            vault_path: Chemin vers le vault Obsidian.
        """
        self.db_path = db_path
        self.vault_path = Path(vault_path)
        self._init_db()
        self._init_kb_structure()

    def _init_db(self) -> None:
        """Initialise la table connaissance si elle n'existe pas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
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
            conn.commit()

    def _init_kb_structure(self) -> None:
        """Initialise la structure du dossier KB."""
        kb_path = self.vault_path / "KB"
        kb_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Structure KB initialisée: {kb_path}")

    def add_knowledge(
        self,
        application: str,
        category: str,
        title: str,
        description: str,
    ) -> str:
        """Ajoute une connaissance à la base.

        Args:
            application: Nom de l'application.
            category: Catégorie de la connaissance.
            title: Titre de la connaissance.
            description: Description de la connaissance.

        Returns:
            ID de la connaissance créée.
        """
        knowledge_id = str(uuid.uuid4())

        # Ajouter à la base de données
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO connaissance (id, application, categorie, titre, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (knowledge_id, application, category, title, description),
            )
            conn.commit()

        # Créer la note Obsidian
        self._create_kb_note(
            application,
            category,
            title,
            description,
        )

        logger.info(f"Connaissance ajoutée: {knowledge_id}")
        return knowledge_id

    def _create_kb_note(
        self,
        application: str,
        category: str,
        title: str,
        description: str,
    ) -> str:
        """Crée une note de connaissance dans Obsidian.

        Args:
            application: Nom de l'application.
            category: Catégorie de la connaissance.
            title: Titre de la connaissance.
            description: Description de la connaissance.

        Returns:
            Chemin vers la note créée.
        """
        # Nettoyer le titre pour le nom de fichier
        safe_title = title.replace(" ", "_").replace("/", "_")
        filename = f"{safe_title}.md"

        # Créer le chemin: KB/Application/Categorie/Titre.md
        app_path = self.vault_path / "KB" / application
        cat_path = app_path / category
        cat_path.mkdir(parents=True, exist_ok=True)

        filepath = cat_path / filename

        content = f"""---
date: {datetime.now().strftime("%Y-%m-%d")}
tags: [kb, {application.lower()}]
application: {application}
categorie: {category}
---

# {title}

## Application
{application}

## Description
{description}

## Comment l'utiliser
À compléter manuellement

## Exemples
À compléter manuellement

## Date de découverte
{datetime.now().strftime("%Y-%m-%d")}

"""

        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Note KB créée: {filepath}")

        return str(filepath)

    def get_knowledge(
        self,
        application: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        """Récupère des connaissances de la base.

        Args:
            application: Filtre par application (optionnel).
            category: Filtre par catégorie (optionnel).

        Returns:
            Liste des connaissances.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if application and category:
                cursor.execute(
                    "SELECT * FROM connaissance WHERE application = ? AND categorie = ?",
                    (application, category),
                )
            elif application:
                cursor.execute(
                    "SELECT * FROM connaissance WHERE application = ?",
                    (application,),
                )
            elif category:
                cursor.execute(
                    "SELECT * FROM connaissance WHERE categorie = ?",
                    (category,),
                )
            else:
                cursor.execute("SELECT * FROM connaissance")

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "application": row[1],
                    "category": row[2],
                    "title": row[3],
                    "description": row[4],
                    "created_at": row[5],
                }
                for row in rows
            ]
