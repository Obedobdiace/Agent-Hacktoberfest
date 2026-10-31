"""Module de sécurité pour la classification et validation des actions."""

import logging
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Niveaux de sécurité pour les actions."""
    SAFE = "SAFE"
    RISKY = "RISKY"
    CRITICAL = "CRITICAL"


class Action(BaseModel):
    """Modèle d'action à classifier."""
    action_type: str
    parameters: dict = Field(default_factory=dict)


class SecurityDecision(BaseModel):
    """Résultat de la classification de sécurité."""
    level: SecurityLevel
    approved: bool
    blocked_reason: Optional[str] = None
    requires_confirmation: bool = False


class SecurityGuard:
    """Gardien de sécurité pour classifier et valider les actions."""

    # Chemins protégés - jamais écrire ou modifier
    PROTECTED_PATHS = [
        "C:/Windows",
        "C:/Program Files",
        "C:/Program Files (x86)",
        "~/.ssh",
        "~/.env",
        "~/.gitconfig",
        "~/AppData/Roaming",
    ]

    # Liste noire absolue - jamais exécuter sans validation
    BLACKLISTED_OPERATIONS = {
        "os.remove",
        "os.unlink",
        "shutil.rmtree",
        "rmdir",
        "DROP TABLE",
        "DELETE FROM",
        "TRUNCATE",
        "RegDeleteKey",
        "RegDeleteValue",
        "format",
        "rd /s",
    }

    # Actions SAFE - lecture uniquement
    SAFE_ACTIONS = {
        "screen_capture",
        "element_capture",
        "ocr_extract",
        "ocr_search",
        "analyze_screen",
        "find_element",
        "list_directory",
        "create_directory",
        "move_file",
        "copy_file",
    }

    # Actions CRITICAL - destruction ou modification système
    CRITICAL_ACTIONS = {
        "file_delete",
        "system_command",
    }

    def __init__(self, readonly_mode: bool = False) -> None:
        """Initialise le gardien de sécurité.

        Args:
            readonly_mode: Si True, bloque toutes les actions RISKY et CRITICAL.
        """
        self.readonly_mode = readonly_mode

    def classify(self, action: Action) -> SecurityDecision:
        """Classifie une action selon son niveau de sécurité.

        Args:
            action: L'action à classifier.

        Returns:
            SecurityDecision avec le niveau et la décision d'approbation.
        """
        # Vérifier si l'action est dans la liste noire
        if self._is_blacklisted(action):
            return SecurityDecision(
                level=SecurityLevel.CRITICAL,
                approved=False,
                blocked_reason="Action dans la liste noire absolue",
                requires_confirmation=True,
            )

        # Vérifier si l'action touche un chemin protégé
        if self._touches_protected_path(action):
            return SecurityDecision(
                level=SecurityLevel.CRITICAL,
                approved=False,
                blocked_reason="Action sur un chemin protégé",
                requires_confirmation=True,
            )

        # Classifier selon le type d'action
        if action.action_type in self.SAFE_ACTIONS:
            return SecurityDecision(
                level=SecurityLevel.SAFE,
                approved=True,
                requires_confirmation=False,
            )

        if action.action_type in self.CRITICAL_ACTIONS:
            return SecurityDecision(
                level=SecurityLevel.CRITICAL,
                approved=False,
                requires_confirmation=True,
            )

        # Par défaut, les autres actions sont RISKY
        if self.readonly_mode:
            return SecurityDecision(
                level=SecurityLevel.RISKY,
                approved=False,
                blocked_reason="Mode lecture seule activé",
                requires_confirmation=True,
            )

        return SecurityDecision(
            level=SecurityLevel.RISKY,
            approved=False,
            requires_confirmation=True,
        )

    def _is_blacklisted(self, action: Action) -> bool:
        """Vérifie si l'action contient une opération blacklistée.

        Args:
            action: L'action à vérifier.

        Returns:
            True si l'action est blacklistée.
        """
        params_str = str(action.parameters).lower()
        action_str = action.action_type.lower()

        for op in self.BLACKLISTED_OPERATIONS:
            if op.lower() in params_str or op.lower() in action_str:
                return True

        return False

    def _touches_protected_path(self, action: Action) -> bool:
        """Vérifie si l'action touche un chemin protégé.

        Args:
            action: L'action à vérifier.

        Returns:
            True si l'action touche un chemin protégé.
        """
        if "path" not in action.parameters and "file_path" not in action.parameters:
            return False

        path = action.parameters.get("path") or action.parameters.get("file_path", "")
        if not path:
            return False

        path_obj = Path(path).expanduser()

        for protected in self.PROTECTED_PATHS:
            protected_path = Path(protected).expanduser()
            try:
                if path_obj.is_relative_to(protected_path) or path_obj == protected_path:
                    return True
            except (ValueError, RuntimeError):
                # Path.is_relative_to peut échouer sur certains chemins
                continue

        return False

    def confirm_critical_action(self, action: Action) -> bool:
        """Demande confirmation pour une action critique.

        Args:
            action: L'action critique à confirmer.

        Returns:
            True si l'utilisateur confirme, False sinon.
        """
        decision = self.classify(action)

        if decision.level == SecurityLevel.SAFE:
            return True

        if decision.level == SecurityLevel.CRITICAL:
            logger.warning(
                f"Action CRITICAL requiert confirmation: {action.action_type}"
            )
            # Dans une implémentation réelle, ceci afficherait une UI
            # Pour l'instant, on retourne False pour forcer la validation manuelle
            return False

        return False
