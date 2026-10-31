import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FastParser:
    """Analyseur rapide pour contourner l'API Vision sur des commandes simples."""

    # app_name_in_instruction → executable/URI pour Start-Process
    COMMON_APPS = {
        # — Éditeurs de texte
        "bloc-notes":           "notepad.exe",
        "bloc notes":           "notepad.exe",
        "notepad":              "notepad.exe",
        # — Bureautique
        "calculatrice":         "calc.exe",
        "calc":                 "calc.exe",
        "word":                 "winword",
        "excel":                "excel",
        "powerpoint":           "powerpnt",
        # — Navigateurs
        "navigateur":           "msedge",
        "edge":                 "msedge",
        "chrome":               "chrome",
        "firefox":              "firefox",
        # — Explorateur de fichiers
        "explorateur":          "explorer.exe",
        "explorateur de fichiers": "explorer.exe",
        "gestionnaire de fichiers": "explorer.exe",
        # — Graphique
        "peinture":             "mspaint.exe",
        "paint":                "mspaint.exe",
        # — Média / Photo / Caméra
        "caméra":               "microsoft.windows.camera:",
        "camera":               "microsoft.windows.camera:",
        "webcam":               "microsoft.windows.camera:",
        "photos":               "ms-photos:",
        "spotify":              "spotify",
        "vlc":                  "vlc",
        # — Développement
        "vscode":               "code",
        "vs code":              "code",
        "visual studio code":   "code",
        # — Communication
        "discord":              "discord",
        "teams":                "teams",
        "whatsapp":             "whatsapp",
        "slack":                "slack",
        "telegram":             "telegram",
        "zoom":                 "zoom",
        # — Système
        "cmd":                  "cmd.exe",
        "invite de commande":   "cmd.exe",
        "terminal":             "powershell.exe",
        "powershell":           "powershell.exe",
        "paramètres":           "ms-settings:",
        "parametres":           "ms-settings:",
        "gestionnaire des taches":  "taskmgr.exe",
        "gestionnaire de taches":   "taskmgr.exe",
        "gestionnaire des tâches":  "taskmgr.exe",
        "gestionnaire de tâches":   "taskmgr.exe",
        # — Notes
        "obsidian":             "obsidian",
        "notion":               "notion",
    }

    # exe → nom du processus pour Stop-Process
    PROCESS_NAMES = {
        "notepad.exe":                  "notepad",
        "calc.exe":                     "Calculator",
        "explorer.exe":                 "explorer",
        "winword":                      "WINWORD",
        "excel":                        "EXCEL",
        "powerpnt":                     "POWERPNT",
        "msedge":                       "msedge",
        "chrome":                       "chrome",
        "firefox":                      "firefox",
        "mspaint.exe":                  "mspaint",
        "microsoft.windows.camera:":    "WindowsCamera",
        "ms-photos:":                   "Microsoft.Photos",
        "spotify":                      "Spotify",
        "vlc":                          "vlc",
        "code":                         "Code",
        "discord":                      "Discord",
        "teams":                        "Teams",
        "whatsapp":                     "WhatsApp",
        "slack":                        "slack",
        "telegram":                     "Telegram",
        "zoom":                         "Zoom",
        "powershell.exe":               "powershell",
        "cmd.exe":                      "cmd",
        "taskmgr.exe":                  "Taskmgr",
        "obsidian":                     "Obsidian",
        "notion":                       "Notion",
    }

    def __init__(self):
        pass

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalise les apostrophes Unicode et les espaces insécables."""
        return (
            text
            .replace('\u2019', "'")   # right single quotation mark → ASCII apostrophe
            .replace('\u2018', "'")   # left single quotation mark
            .replace('\u00a0', ' ')   # non-breaking space → regular space
            .lower()
            .strip()
        )

    def _get_process_name(self, exe_name: str) -> Optional[str]:
        """Retourne le nom du processus Windows pour un exe donné."""
        return self.PROCESS_NAMES.get(exe_name)

    def _open_cmd(self, exe_name: str) -> str:
        """Génère la commande PowerShell pour ouvrir une app."""
        if exe_name.endswith(":"):
            # URI scheme (ms-settings:, microsoft.windows.camera:, etc.)
            return f"Start-Process '{exe_name}'"
        elif exe_name.endswith(".exe"):
            return f"Start-Process '{exe_name}'"
        else:
            # Apps tierces (chrome, spotify, code…) — Start-Process les trouve si elles sont dans le PATH
            return f"Start-Process '{exe_name}'"

    def _close_cmd(self, exe_name: str) -> Optional[str]:
        """Génère la commande PowerShell pour fermer une app."""
        if exe_name.endswith(":"):
            # URI-based apps → tuer par nom de processus
            proc = self._get_process_name(exe_name)
            if proc:
                return f"Stop-Process -Name '{proc}' -Force -ErrorAction SilentlyContinue"
            return None
        proc = self._get_process_name(exe_name)
        if proc:
            return f"Stop-Process -Name '{proc}' -Force -ErrorAction SilentlyContinue"
        # Fallback via taskkill
        name = exe_name.replace(".exe", "")
        return f"taskkill /F /IM {name}.exe 2>$null"

    def _match_app(self, text: str) -> Optional[str]:
        """Cherche une app connue de façon stricte. Retourne l'exe_name ou None."""
        text_clean = text.strip()
        return self.COMMON_APPS.get(text_clean)

    def parse(self, instruction: str) -> Optional[str]:
        """Analyse l'instruction et retourne une commande PowerShell si reconnue.

        Returns:
            La commande PowerShell à exécuter, ou None si non reconnue.
        """
        inst = self._normalize(instruction)

        # ── 1. Luminosité ──────────────────────────────────────────────────
        m = re.search(r'lum[a-z]*\s*[àa]?\s*(\d+)', inst)
        if m:
            level = max(0, min(100, int(m.group(1))))
            logger.info(f"FastParser: luminosité → {level}%")
            return (
                f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                f".WmiSetBrightness(1, {level})"
            )

        # ── 2. Volume ──────────────────────────────────────────────────────
        if any(kw in inst for kw in ["muet", "coupe le son", "désactive le son", "silence", "mute"]):
            logger.info("FastParser: mute")
            return "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"

        m = re.search(r'(?:volume|son)\s*[àa]?\s*(\d+)', inst)
        if m:
            level = max(0, min(100, int(m.group(1))))
            logger.info(f"FastParser: volume → {level}%")
            # Méthode PowerShell native via l'objet COM audio
            pct = level / 100.0
            return (
                f"$obj = New-Object -ComObject WScript.Shell; "
                f"1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}; "  # d'abord tout en bas
                f"1..{level} | ForEach-Object {{ $obj.SendKeys([char]175) }}"  # puis monter
            )

        # ── 3. Contrôles média ─────────────────────────────────────────────
        if any(kw in inst for kw in ["musique suivante", "titre suivant", "chanson suivante", "suivant"]):
            return "(New-Object -ComObject WScript.Shell).SendKeys([char]176)"
        if any(kw in inst for kw in ["musique précédente", "titre précédent", "chanson précédente", "précédent"]):
            return "(New-Object -ComObject WScript.Shell).SendKeys([char]177)"
        if any(kw in inst for kw in ["pause musique", "play", "joue la musique", "reprends la musique"]):
            return "(New-Object -ComObject WScript.Shell).SendKeys([char]179)"

        # ── 4. Verrouillage PC ─────────────────────────────────────────────
        if "verrouille" in inst and any(kw in inst for kw in ["pc", "ordinateur", "écran", "ecran", "session"]):
            logger.info("FastParser: verrouillage")
            return "rundll32.exe user32.dll,LockWorkStation"

        # ── 5. Corbeille ───────────────────────────────────────────────────
        if any(kw in inst for kw in ["vide la corbeille", "vider la corbeille", "vide corbeille"]):
            logger.info("FastParser: vider corbeille")
            return "Clear-RecycleBin -Force -Confirm:$false"

        # ── 6. Capture d'écran ─────────────────────────────────────────────
        if any(kw in inst for kw in ["capture d'écran", "screenshot", "prends une photo de l'écran", "imprime écran"]):
            logger.info("FastParser: capture d'écran")
            return (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "[System.Windows.Forms.SendKeys]::SendWait('%{PRTSC}')"
            )

        # ── 7. Fermeture d'applications ────────────────────────────────────
        close_pat = re.compile(
            r"(?:ferme|quitte|arr[eê]te|fermer|quitter|stoppe|stopper|tue|kill|exit)\s+"
            r"(?:l[a'\s]|le\s|les\s|l'application\s|l'app\s|l'appli\s)?(.*)",
            re.IGNORECASE
        )
        m = close_pat.search(inst)
        if m:
            app_target = self._normalize(m.group(1))
            # Nettoyer politesses
            app_target = re.sub(r"\s+s'il\s+te\s+pla[iî]t.*$", "", app_target)
            exe = self._match_app(app_target)
            if exe:
                cmd = self._close_cmd(exe)
                if cmd:
                    logger.info(f"FastParser: fermeture → {exe}")
                    return cmd

        # ── 8. Ouverture d'applications ────────────────────────────────────
        open_pat = re.compile(
            r"(?:ouvre|lance|d[eé]marre|ouvrir|lancer|d[eé]marrer|start)\s+"
            r"(?:l[a'\s]|le\s|les\s|l'application\s|l'app\s|l'appli\s|mon\s|ma\s)?(.*)",
            re.IGNORECASE
        )
        m = open_pat.search(inst)
        if m:
            app_target = self._normalize(m.group(1))
            app_target = re.sub(r"\s+s'il\s+te\s+pla[iî]t.*$", "", app_target)
            app_target = re.sub(r"\s+stp.*$", "", app_target)
            exe = self._match_app(app_target)
            if exe:
                logger.info(f"FastParser: ouverture → {exe}")
                return self._open_cmd(exe)

        # ── 9. Nom seul (sans verbe) ───────────────────────────────────────
        exe = self.COMMON_APPS.get(inst.strip())
        if exe:
            logger.info(f"FastParser: ouverture directe → {exe}")
            return self._open_cmd(exe)

        return None
