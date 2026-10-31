"""Catalogue des applications installées sous Windows.

Résout un nom dit par l'utilisateur (français ou anglais) vers un lanceur
réel : raccourci du menu Démarrer, application du Store, chemin App Paths
ou exécutable connu. Aucun appel à un modèle de langage.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
import time
import unicodedata
import winreg
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_TTL_S = 300.0
_cache_lock = threading.Lock()
_cache_apps: list[InstalledApp] | None = None
_cache_at = 0.0

# Processus qu'on ne tue jamais, même si un nom d'app s'en approche.
_NEVER_KILL = {
    "csrss",
    "dwm",
    "lsass",
    "registry",
    "services",
    "smss",
    "svchost",
    "system",
    "wininit",
    "winlogon",
}

_SKIP_FRAGMENTS = ("uninstall", "desinstall", "unins000", "crashpad")


@dataclass(frozen=True)
class InstalledApp:
    """Une application lançable."""

    name: str
    norm: str
    target: str
    kind: str  # exe | lnk | appx | uri
    process_name: str | None = None


def _norm(text: str) -> str:
    """Minuscules, sans accents, ponctuation légère conservée (+ et #)."""
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = folded.lower().replace("'", " ").replace("_", " ")
    folded = re.sub(r"[^a-z0-9.+# ]+", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def _skip_name(name: str) -> bool:
    norm = _norm(name)
    if len(norm) < 2:
        return True
    return any(fragment in norm for fragment in _SKIP_FRAGMENTS)


def _system(name: str, target: str, kind: str, process_name: str | None) -> InstalledApp:
    return InstalledApp(name=name, norm=_norm(name), target=target, kind=kind, process_name=process_name)


# Applications toujours présentes, ou protocoles Windows. La clé est le nom normalisé.
_SYSTEM: dict[str, InstalledApp] = {}


def _add_system(aliases: list[str], target: str, kind: str, process_name: str | None, label: str) -> None:
    app = _system(label, target, kind, process_name)
    for alias in aliases:
        _SYSTEM[_norm(alias)] = app


_add_system(["notepad", "bloc-notes", "bloc notes"], "notepad.exe", "exe", "notepad", "Bloc-notes")
_add_system(["calc", "calculatrice", "calculator"], "calc.exe", "exe", "CalculatorApp", "Calculatrice")
_add_system(
    ["explorer", "explorateur", "explorateur de fichiers", "gestionnaire de fichiers"],
    "explorer.exe",
    "exe",
    "explorer",
    "Explorateur de fichiers",
)
_add_system(["paint", "peinture", "mspaint"], "mspaint.exe", "exe", "mspaint", "Paint")
_add_system(
    ["taskmgr", "gestionnaire des taches", "gestionnaire de taches"],
    "taskmgr.exe",
    "exe",
    "Taskmgr",
    "Gestionnaire des tâches",
)
_add_system(["cmd", "invite de commande", "invite de commandes"], "cmd.exe", "exe", "cmd", "Invite de commandes")
_add_system(["powershell"], "powershell.exe", "exe", "powershell", "PowerShell")
_add_system(["paramètres", "parametres", "settings"], "ms-settings:", "uri", None, "Paramètres")
_add_system(
    ["caméra", "camera", "webcam"],
    "microsoft.windows.camera:",
    "uri",
    "WindowsCamera",
    "Caméra",
)
_add_system(["photos"], "ms-photos:", "uri", None, "Photos")
_add_system(["snipping tool", "outil capture"], "snippingtool.exe", "exe", "SnippingTool", "Outil Capture")

_wt = shutil.which("wt")
if _wt:
    _add_system(["terminal", "windows terminal"], _wt, "exe", "WindowsTerminal", "Terminal Windows")

# Quand le nom dit ne correspond pas au raccourci (Word → WINWORD, VS Code → « Visual Studio Code »).
_FALLBACKS: dict[str, list[str]] = {
    "word": ["microsoft word", "winword"],
    "winword": ["microsoft word", "word"],
    "excel": ["microsoft excel"],
    "powerpoint": ["microsoft powerpoint", "powerpnt"],
    "power point": ["powerpoint", "microsoft powerpoint"],
    "chrome": ["google chrome"],
    "google chrome": ["chrome"],
    "edge": ["microsoft edge", "msedge"],
    "navigateur": ["microsoft edge", "google chrome", "firefox"],
    "firefox": ["mozilla firefox"],
    "mozilla": ["mozilla firefox"],
    "vscode": ["visual studio code", "code"],
    "vs code": ["visual studio code", "code"],
    "visual studio code": ["code"],
    "code": ["visual studio code"],
    "teams": ["microsoft teams"],
    "vlc": ["vlc media player"],
    "whatsapp": ["whatsapp"],
    "telegram": ["telegram"],
    "spotify": ["spotify"],
    "discord": ["discord"],
    "obsidian": ["obsidian"],
    "notion": ["notion"],
    "zoom": ["zoom"],
    "slack": ["slack"],
    "terminal": ["windows terminal", "terminal"],
    "outlook": ["outlook"],
    "onenote": ["onenote"],
    "store": ["microsoft store"],
    "microsoft store": ["store"],
}


def score_name(query: str, name: str) -> float:
    """Score de 0 à 1 entre un nom demandé et un nom installé, déjà normalisés."""
    if not query or not name:
        return 0.0
    if query == name:
        return 1.0
    q_tokens = query.split()
    n_tokens = name.split()
    if q_tokens and all(token in n_tokens for token in q_tokens):
        extra = len(n_tokens) - len(q_tokens)
        return max(0.84, 0.96 - extra * 0.03)
    return SequenceMatcher(None, query, name).ratio()


def best_match(
    query: str,
    apps: list[InstalledApp],
    min_score: float = 0.84,
) -> tuple[InstalledApp | None, float]:
    """Choisit l'application la plus proche, ou aucune si le nom est ambigu."""
    scored: list[tuple[float, int, InstalledApp]] = []
    for app in apps:
        value = score_name(query, app.norm)
        if value >= min_score:
            scored.append((value, len(app.norm.split()), app))
    if not scored:
        return None, 0.0

    scored.sort(key=lambda item: (-item[0], item[1], item[2].norm))
    best_score, best_len, best = scored[0]
    if best_score >= 0.98:
        return best, best_score

    tied = [
        app
        for value, length, app in scored
        if abs(value - best_score) < 0.001 and length == best_len and app.norm != best.norm
    ]
    if tied:
        return None, best_score
    return best, best_score


def _add(found: dict[str, InstalledApp], app: InstalledApp) -> None:
    if _skip_name(app.name):
        return
    found.setdefault(app.norm, app)


def _shortcut_dirs() -> list[Path]:
    home = Path.home()
    program_data = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
    appdata = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
    public = Path(os.environ.get("PUBLIC", r"C:\Users\Public"))
    return [
        appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        program_data / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        home / "Desktop",
        public / "Desktop",
    ]


def _collect_shortcuts(found: dict[str, InstalledApp]) -> None:
    for folder in _shortcut_dirs():
        if not folder.is_dir():
            continue
        for link in folder.rglob("*.lnk"):
            _add(
                found,
                InstalledApp(
                    name=link.stem,
                    norm=_norm(link.stem),
                    target=str(link),
                    kind="lnk",
                ),
            )


def _reg_str(key: winreg.HKEYType, name: str) -> str:
    try:
        value, _typ = winreg.QueryValueEx(key, name)
    except OSError:
        return ""
    return str(value).strip() if value else ""


def _reg_dword(key: winreg.HKEYType, name: str) -> int:
    try:
        value, _typ = winreg.QueryValueEx(key, name)
    except OSError:
        return 0
    return int(value) if isinstance(value, int) else 0


def _collect_app_paths(found: dict[str, InstalledApp]) -> None:
    roots = (
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
    )
    for hive, path in roots:
        try:
            root = winreg.OpenKey(hive, path)
        except OSError:
            continue
        with root:
            count = winreg.QueryInfoKey(root)[0]
            for index in range(count):
                try:
                    exe_name = winreg.EnumKey(root, index)
                    with winreg.OpenKey(root, exe_name) as sub:
                        target = _reg_str(sub, "")
                except OSError:
                    continue
                stem = Path(exe_name).stem
                if not target or not os.path.isfile(target) or _skip_name(stem):
                    continue
                _add(
                    found,
                    InstalledApp(
                        name=stem,
                        norm=_norm(stem),
                        target=target,
                        kind="exe",
                        process_name=stem,
                    ),
                )


def _collect_uninstall(found: dict[str, InstalledApp]) -> None:
    roots = (
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    )
    for hive, path in roots:
        try:
            root = winreg.OpenKey(hive, path)
        except OSError:
            continue
        with root:
            count = winreg.QueryInfoKey(root)[0]
            for index in range(count):
                try:
                    sub_name = winreg.EnumKey(root, index)
                    with winreg.OpenKey(root, sub_name) as sub:
                        if _reg_dword(sub, "SystemComponent") == 1:
                            continue
                        if _reg_str(sub, "ParentDisplayName"):
                            continue
                        release = _reg_str(sub, "ReleaseType").lower()
                        if release in {"update", "security update", "hotfix", "update rollup"}:
                            continue
                        display = _reg_str(sub, "DisplayName")
                        icon = _reg_str(sub, "DisplayIcon")
                except OSError:
                    continue
                if not display or not icon or _skip_name(display):
                    continue
                exe = icon.split(",")[0].strip().strip('"')
                if not exe.lower().endswith(".exe") or not os.path.isfile(exe):
                    continue
                _add(
                    found,
                    InstalledApp(
                        name=display,
                        norm=_norm(display),
                        target=exe,
                        kind="exe",
                        process_name=Path(exe).stem,
                    ),
                )


def _collect_start_apps(found: dict[str, InstalledApp]) -> None:
    script = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "Get-StartApps | ForEach-Object { $_.Name + \"`t\" + $_.AppID }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=25,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Get-StartApps indisponible: %s", exc)
        return
    if result.returncode != 0:
        logger.warning("Get-StartApps a échoué: %s", (result.stderr or "").strip()[:300])
        return
    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue
        name, app_id = line.split("\t", 1)
        name = name.strip()
        app_id = app_id.strip()
        if not name or not app_id or _skip_name(name):
            continue
        process = app_id.split("!")[-1] if "!" in app_id else None
        _add(
            found,
            InstalledApp(
                name=name,
                norm=_norm(name),
                target=app_id,
                kind="appx",
                process_name=process,
            ),
        )


def load_installed_apps() -> list[InstalledApp]:
    """Construit la liste des applications lançables. Le menu Démarrer gagne sur le reste."""
    found: dict[str, InstalledApp] = {}
    _collect_shortcuts(found)
    _collect_app_paths(found)
    _collect_uninstall(found)
    _collect_start_apps(found)
    apps = list(found.values())
    logger.info("Catalogue d'applications: %s entrée(s)", len(apps))
    return apps


def get_cached_apps(force: bool = False) -> list[InstalledApp]:
    """Retourne le catalogue, reconstruit au plus toutes les 5 minutes."""
    global _cache_apps, _cache_at
    now = time.monotonic()
    with _cache_lock:
        if not force and _cache_apps is not None and now - _cache_at < _CACHE_TTL_S:
            return _cache_apps
        apps = load_installed_apps()
        _cache_apps = apps
        _cache_at = time.monotonic()
        return apps


def warm_catalog() -> None:
    """Précharge le catalogue (à appeler au démarrage du serveur)."""
    try:
        get_cached_apps()
    except Exception:
        logger.exception("Échec du préchargement du catalogue d'applications")


def _query_chain(raw: str) -> list[str]:
    chain = [raw, *_FALLBACKS.get(raw, [])]
    seen: list[str] = []
    for item in chain:
        if item and item not in seen:
            seen.append(item)
    return seen


def _direct_file(query: str) -> InstalledApp | None:
    candidate = query.strip().strip('"')
    if not candidate or any(ch in candidate for ch in "\n\r|&$;`"):
        return None
    path = Path(candidate)
    if path.suffix.lower() not in {".exe", ".lnk"} or not path.is_file():
        return None
    return InstalledApp(
        name=path.stem,
        norm=_norm(path.stem),
        target=str(path),
        kind="lnk" if path.suffix.lower() == ".lnk" else "exe",
        process_name=path.stem,
    )


class AppCatalog:
    """Résout un nom d'application vers une entrée lançable."""

    def __init__(self, apps: list[InstalledApp] | None = None) -> None:
        self._injected = apps
        self._apps: list[InstalledApp] = list(apps) if apps is not None else []

    def ensure_loaded(self) -> None:
        if self._injected is not None:
            self._apps = list(self._injected)
            return
        self._apps = get_cached_apps()

    @property
    def apps(self) -> list[InstalledApp]:
        self.ensure_loaded()
        return self._apps

    def resolve(self, query: str) -> InstalledApp | None:
        """Trouve l'application à lancer. None si rien ne correspond assez clairement."""
        direct = _direct_file(query)
        if direct:
            return direct

        raw = _norm(query)
        if len(raw) < 2 or any(ch in query for ch in "\n\r|&$;`"):
            return None
        system = _SYSTEM.get(raw)
        if system:
            return system

        self.ensure_loaded()
        best: InstalledApp | None = None
        best_score = 0.0
        for candidate in _query_chain(raw):
            hit, value = best_match(candidate, self._apps)
            if hit is not None and value > best_score:
                best, best_score = hit, value
                if value >= 0.98:
                    break
        if best is not None:
            return best

        which = shutil.which(raw) or shutil.which(f"{raw}.exe")
        if which:
            stem = Path(which).stem
            return InstalledApp(name=stem, norm=_norm(stem), target=which, kind="exe", process_name=stem)
        return None


def launch_app(app: InstalledApp, args: list[str] | None = None) -> bool:
    """Lance une application déjà résolue. Ne passe pas par un shell."""
    try:
        if app.kind == "appx":
            subprocess.Popen(
                ["explorer.exe", f"shell:AppsFolder\\{app.target}"],
                close_fds=True,
            )
            return True
        if args and app.kind == "exe":
            subprocess.Popen([app.target, *args], close_fds=True)
            return True
        os.startfile(app.target)  # noqa: S606 — lanceur d'applications Windows, cible déjà résolue
        return True
    except OSError as exc:
        logger.error("Impossible de lancer %s (%s): %s", app.name, app.target, exc)
        return False


def process_candidates(app: InstalledApp) -> list[str]:
    """Noms de processus probables pour fermer l'application."""
    names: list[str] = []

    def push(value: str | None) -> None:
        if not value:
            return
        stem = Path(value).stem
        if stem and stem.lower() not in {item.lower() for item in names}:
            names.append(stem)

    push(app.process_name)
    if app.kind == "exe":
        push(app.target)
    if app.kind == "lnk":
        push(_lnk_target(app.target))
    if app.kind == "appx" and app.process_name:
        push(app.process_name)
    return [name for name in names if name.lower() not in _NEVER_KILL]


def _lnk_target(path: str) -> str | None:
    quoted = path.replace("'", "''")
    script = f"(New-Object -ComObject WScript.Shell).CreateShortcut('{quoted}').TargetPath"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    target = (result.stdout or "").strip()
    return target or None


def taskkill(image: str, force: bool = True) -> bool:
    """Termine un processus par son nom d'image. Refuse les processus système."""
    stem = Path(image).stem
    if not stem or stem.lower() in _NEVER_KILL:
        return False
    exe = f"{stem}.exe"
    command = ["taskkill", "/IM", exe]
    if force:
        command.insert(1, "/F")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error("taskkill %s: %s", exe, exc)
        return False
    return result.returncode == 0
