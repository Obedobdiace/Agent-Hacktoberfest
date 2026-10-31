"""Contrôle des applications installées sur le PC."""

import logging

from agent.actions.app_catalog import (
    AppCatalog,
    InstalledApp,
    launch_app,
    process_candidates,
    taskkill,
)

logger = logging.getLogger(__name__)


class AppController:
    """Ouvre, ferme et focalise n'importe quelle application installée."""

    def __init__(self, catalog: AppCatalog | None = None) -> None:
        self.catalog = catalog or AppCatalog()
        logger.info("Contrôleur d'applications initialisé")

    def resolve(self, app_name: str) -> InstalledApp | None:
        return self.catalog.resolve(app_name)

    def can_open(self, app_name: str) -> bool:
        return self.resolve(app_name) is not None

    def resolve_name(self, app_name: str) -> str | None:
        app = self.resolve(app_name)
        return app.name if app else None

    def open(self, app_name: str, args: list[str] | None = None) -> bool:
        """Ouvre une application par son nom (Bloc-notes, Spotify, Chrome, etc.)."""
        app = self.resolve(app_name)
        if app is None:
            logger.error("Aucune application installée ne correspond à %r", app_name)
            return False
        logger.info("AppController.open: %r → %s (%s)", app_name, app.name, app.target)
        return launch_app(app, args)

    def close(self, app_name: str, force: bool = True) -> bool:
        """Ferme une application déjà résolue dans le catalogue."""
        app = self.resolve(app_name)
        if app is None:
            logger.error("Impossible de fermer %r : application inconnue", app_name)
            return False
        killed = False
        for image in process_candidates(app):
            logger.info("AppController.close: %s → %s", app.name, image)
            killed = taskkill(image, force=force) or killed
        return killed

    def focus(self, app_name: str) -> bool:
        """Met le focus sur la fenêtre dont le titre correspond à l'application."""
        app = self.resolve(app_name)
        keywords = []
        if app is not None:
            keywords.append(app.name.lower())
            if app.process_name:
                keywords.append(app.process_name.lower())
        keywords.append(app_name.lower().strip())

        try:
            import pygetwindow as gw

            windows = gw.getAllWindows()
        except ImportError:
            try:
                import pyautogui

                windows = pyautogui.getAllWindows()
            except Exception:
                logger.warning("pygetwindow / pyautogui non disponible pour focus()")
                return False
        except Exception as exc:
            logger.error("Erreur getAllWindows: %s", exc)
            return False

        for window in windows:
            title = (window.title or "").lower()
            if not title:
                continue
            if not any(keyword and keyword in title for keyword in keywords):
                continue
            try:
                if getattr(window, "isMinimized", False):
                    window.restore()
                window.activate()
                logger.info("Focus: '%s'", window.title)
                return True
            except Exception as exc:
                logger.warning("Impossible d'activer '%s': %s", window.title, exc)

        logger.warning("Fenêtre non trouvée pour %s", app_name)
        return False

    def list_running(self) -> list[str]:
        """Noms des applications du catalogue dont le processus tourne."""
        import subprocess

        try:
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []
        running = {line.split(",")[0].strip('"').lower() for line in result.stdout.splitlines() if line}
        names: list[str] = []
        for app in self.catalog.apps:
            image = (app.process_name or "").lower()
            if not image:
                continue
            exe = image if image.endswith(".exe") else f"{image}.exe"
            if exe in running or image in running:
                names.append(app.name)
        return names
