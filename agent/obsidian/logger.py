"""Module de logging vers Obsidian."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


class ObsidianLogger:
    """Logger pour écrire des notes dans Obsidian."""

    def __init__(self, vault_path: str) -> None:
        """Initialise le logger Obsidian.

        Args:
            vault_path: Chemin absolu vers le vault Obsidian.
        """
        self.vault_path = Path(vault_path)
        self._init_structure()

    def _init_structure(self) -> None:
        """Initialise la structure du vault."""
        directories = [
            "Sessions",
            "Tâches",
            "Erreurs",
            "KB",
            "Recherches",
        ]

        for directory in directories:
            dir_path = self.vault_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Structure Obsidian initialisée: {self.vault_path}")

    def create_session_note(
        self,
        session_id: str,
        instruction: str,
        resume: str,
        tasks: Optional[list[str]] = None,
        status: str = "terminee",
    ) -> str:
        """Crée une note de session.

        Args:
            session_id: ID de la session.
            instruction: Instruction initiale.
            resume: Résumé de la session.
            tasks: Liste des tâches exécutées.
            status: Statut de la session.

        Returns:
            Chemin vers la note créée.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"{timestamp}_session.md"
        filepath = self.vault_path / "Sessions" / filename

        tasks_list = "\n".join(f"- [x] {task}" for task in (tasks or []))

        content = f"""---
date: {datetime.now().strftime("%Y-%m-%d")}
tags: [session]
---

# Session {timestamp}

## Instruction Initiale
{instruction}

## Résumé
{resume}

## Tâches Exécutées
{tasks_list}

## Statut
{status}

## Notes
"""

        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Note de session créée: {filepath}")

        return str(filepath)

    def create_task_note(
        self,
        session_id: str,
        task_description: str,
        subtasks: Optional[list[str]] = None,
        result: str = "succès",
    ) -> str:
        """Crée une note de tâche.

        Args:
            session_id: ID de la session.
            task_description: Description de la tâche.
            subtasks: Liste des sous-tâches.
            result: Résultat de la tâche.

        Returns:
            Chemin vers la note créée.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"{timestamp}_tache_{session_id[:8]}.md"
        filepath = self.vault_path / "Tâches" / filename

        subtasks_list = "\n".join(f"- [x] {subtask}" for subtask in (subtasks or []))

        content = f"""---
date: {datetime.now().strftime("%Y-%m-%d")}
tags: [tache]
---

# Tâche : {task_description}

## Contexte
Session : {session_id}

## Sous-tâches
{subtasks_list}

## Résultat
{result}

"""

        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Note de tâche créée: {filepath}")

        return str(filepath)

    def log_error(
        self,
        session_id: str,
        error_type: str,
        description: str,
        screenshot_path: Optional[str] = None,
    ) -> str:
        """Log une erreur.

        Args:
            session_id: ID de la session.
            error_type: Type de l'erreur.
            description: Description de l'erreur.
            screenshot_path: Chemin vers le screenshot (optionnel).

        Returns:
            Chemin vers la note créée.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"{timestamp}_erreur_{error_type}.md"
        filepath = self.vault_path / "Erreurs" / filename

        screenshot_section = f"\n## Screenshot\n![]({screenshot_path})" if screenshot_path else ""

        content = f"""---
date: {datetime.now().strftime("%Y-%m-%d")}
tags: [erreur]
---

# Erreur : {error_type}

## Contexte
Session : {session_id}

## Description de l'Erreur
{description}
{screenshot_section}

## Analyse
À compléter manuellement

## Suggestions d'Amélioration
- [ ] Suggestion 1
- [ ] Suggestion 2

"""

        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Note d'erreur créée: {filepath}")

        return str(filepath)

    def create_research_note(
        self,
        session_id: str,
        query: str,
        content: str,
        references: list[dict],
    ) -> str:
        """Crée une note de recherche.

        Args:
            session_id: ID de la session.
            query: La requête de recherche.
            content: Le contenu de la recherche (résultats formatés).
            references: Liste des références (dictionnaires avec 'title' et 'href').

        Returns:
            Chemin vers la note créée.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        safe_query = "".join(c if c.isalnum() else "_" for c in query)[:30]
        filename = f"{timestamp}_recherche_{safe_query}.md"
        filepath = self.vault_path / "Recherches" / filename

        refs_list = "\n".join(f"- [{ref.get('title', 'Lien')}]({ref.get('href', '')})" for ref in references if ref.get('href'))

        file_content = f"""---
date: {datetime.now().strftime("%Y-%m-%d")}
tags: [recherche]
session: {session_id}
requete: "{query}"
---

# Recherche : {query}

## Résultats
{content}

## Références
{refs_list}

"""

        filepath.write_text(file_content, encoding="utf-8")
        logger.info(f"Note de recherche créée: {filepath}")

        return str(filepath)
