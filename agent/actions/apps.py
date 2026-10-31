"""Module de contrôle des applications — version PowerShell robuste."""

import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Mappings ────────────────────────────────────────────────────────────────

# nom_agent → commande PowerShell d'ouverture
_OPEN_CMDS: dict[str, str] = {
    "notepad":      "Start-Process 'notepad.exe'",
    "calc":         "Start-Process 'calc.exe'",
    "explorer":     "Start-Process 'explorer.exe'",
    "mspaint":      "Start-Process 'mspaint.exe'",
    "taskmgr":      "Start-Process 'taskmgr.exe'",
    "cmd":          "Start-Process 'cmd.exe'",
    "powershell":   "Start-Process 'powershell.exe'",
    "msedge":       "Start-Process 'msedge'",
    "chrome":       "Start-Process 'chrome'",
    "firefox":      "Start-Process 'firefox'",
    "winword":      "Start-Process 'winword'",
    "excel":        "Start-Process 'excel'",
    "powerpnt":     "Start-Process 'powerpnt'",
    # URI schemes
    "ms-settings:":                 "Start-Process 'ms-settings:'",
    "microsoft.windows.camera:":    "Start-Process 'microsoft.windows.camera:'",
    "ms-photos:":                   "Start-Process 'ms-photos:'",
    # Apps tierces (doivent être dans le PATH ou avoir un raccourci shell)
    "spotify":      "Start-Process 'spotify'",
    "discord":      "Start-Process 'discord'",
    "code":         "Start-Process 'code'",
    "obsidian":     "Start-Process 'obsidian'",
    "notion":       "Start-Process 'notion'",
    "teams":        "Start-Process 'teams'",
    "zoom":         "Start-Process 'zoom'",
    "whatsapp":     "Start-Process 'whatsapp'",
    "slack":        "Start-Process 'slack'",
    "telegram":     "Start-Process 'telegram'",
    "vlc":          "Start-Process 'vlc'",
}

# nom_agent → nom du processus pour Stop-Process / taskkill
_PROCESS_NAMES: dict[str, str] = {
    "notepad":      "notepad",
    "calc":         "Calculator",
    "explorer":     "explorer",
    "mspaint":      "mspaint",
    "taskmgr":      "Taskmgr",
    "cmd":          "cmd",
    "powershell":   "powershell",
    "msedge":       "msedge",
    "chrome":       "chrome",
    "firefox":      "firefox",
    "winword":      "WINWORD",
    "excel":        "EXCEL",
    "powerpnt":     "POWERPNT",
    "microsoft.windows.camera:": "WindowsCamera",
    "ms-photos:":   "Microsoft.Photos",
    "spotify":      "Spotify",
    "discord":      "Discord",
    "code":         "Code",
    "obsidian":     "Obsidian",
    "notion":       "Notion",
    "teams":        "Teams",
    "zoom":         "Zoom",
    "whatsapp":     "WhatsApp",
    "slack":        "slack",
    "telegram":     "Telegram",
    "vlc":          "vlc",
}

# titre de fenêtre → app_name (pour focus())
_WINDOW_KEYWORDS: dict[str, list[str]] = {
    "notepad":      ["bloc-notes", "notepad", "untitled"],
    "chrome":       ["google chrome", "chrome"],
    "msedge":       ["microsoft edge", "edge"],
    "firefox":      ["firefox", "mozilla"],
    "winword":      ["word", ".docx", ".doc"],
    "excel":        ["excel", ".xlsx", ".xls"],
    "powerpnt":     ["powerpoint", ".pptx"],
    "explorer":     ["file explorer", "explorateur de fichiers", "this pc", "ce pc"],
    "obsidian":     ["obsidian"],
    "discord":      ["discord"],
    "code":         ["visual studio code", "vscode"],
    "spotify":      ["spotify"],
    "vlc":          ["vlc"],
    "teams":        ["microsoft teams", "teams"],
    "zoom":         ["zoom"],
}


def _run_ps(command: str) -> tuple[bool, str]:
    """Exécute une commande PowerShell. Retourne (succès, output)."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, check=False, timeout=10
        )
        success = result.returncode == 0
        output = result.stdout.strip() or result.stderr.strip()
        return success, output
    except Exception as e:
        logger.error(f"PowerShell error: {e}")
        return False, str(e)


class AppController:
    """Contrôleur d'applications — toutes les opérations passent par PowerShell."""

    def __init__(self) -> None:
        logger.info("Contrôleur d'applications initialisé")

    def open(self, app_name: str, args: Optional[list[str]] = None) -> bool:
        """Ouvre une application.

        app_name peut être le nom court (notepad, chrome, explorer…) ou
        une URI (ms-settings:, microsoft.windows.camera:).
        """
        key = app_name.lower().strip()
        cmd = _OPEN_CMDS.get(key)

        if not cmd:
            # Fallback générique — essaie quand même
            if key.endswith(":"):
                cmd = f"Start-Process '{key}'"
            else:
                cmd = f"Start-Process '{key}'"

        logger.info(f"AppController.open: {key} → {cmd}")
        success, out = _run_ps(cmd)
        if not success:
            logger.error(f"Échec ouverture {key}: {out}")
        return success

    def close(self, app_name: str, force: bool = True) -> bool:
        """Ferme une application par son nom de processus."""
        key = app_name.lower().strip()
        proc = _PROCESS_NAMES.get(key, key)

        # Stop-Process est plus propre que taskkill
        cmd = f"Stop-Process -Name '{proc}' -Force -ErrorAction SilentlyContinue"
        logger.info(f"AppController.close: {key} → Stop-Process '{proc}'")
        success, out = _run_ps(cmd)

        if not success:
            # Fallback taskkill
            cmd2 = f"taskkill /F /IM {proc}.exe 2>$null"
            success, _ = _run_ps(cmd2)

        return success

    def focus(self, app_name: str) -> bool:
        """Met le focus sur la première fenêtre correspondant à app_name."""
        key = app_name.lower().strip()
        keywords = _WINDOW_KEYWORDS.get(key, [key])

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
        except Exception as e:
            logger.error(f"Erreur getAllWindows: {e}")
            return False

        for w in windows:
            title = (w.title or "").lower()
            if not title:
                continue
            for kw in keywords:
                if kw.lower() in title:
                    try:
                        if getattr(w, 'isMinimized', False):
                            w.restore()
                        w.activate()
                        logger.info(f"Focus: '{w.title}'")
                        return True
                    except Exception as e:
                        logger.warning(f"Impossible d'activer '{w.title}': {e}")

        # Dernier recours : Alt+Tab via PowerShell
        logger.warning(f"Fenêtre non trouvée pour {key}, tentative Alt+Tab")
        return False

    def list_running(self) -> list[str]:
        """Retourne la liste des processus en cours dont on connaît le nom."""
        known = list(_PROCESS_NAMES.values())
        cmd = "Get-Process | Select-Object -ExpandProperty Name"
        _, out = _run_ps(cmd)
        running = set(out.splitlines())
        return [name for name in known if name in running]
