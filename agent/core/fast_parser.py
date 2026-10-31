import logging
import re

logger = logging.getLogger(__name__)


class FastParser:
    """Analyseur rapide pour contourner l'API Vision sur des commandes simples."""

    _ARTICLE = r"(?:l'application |l'appli |l'app |les |le |la |l'|mon |ma |un |une )?"
    _OPEN_VERB = (
        r"(?:ouvrir|ouvres|ouvre(?:-moi)?|lancer|lances|lance(?:-moi)?|"
        r"d[eé]marrer|d[eé]marres|d[eé]marre(?:-moi)?|start|open)"
    )
    _CLOSE_VERB = (
        r"(?:fermer|fermes|ferme|quitter|quittes|quitte|arr[eê]ter|arr[eê]tes|"
        r"arr[eê]te|stopper|stoppe|stop|tue|kill|exit)"
    )

    def __init__(self) -> None:
        pass

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalise les apostrophes Unicode et les espaces insécables."""
        return (
            text
            .replace("\u2019", "'")
            .replace("\u2018", "'")
            .replace("\u00a0", " ")
            .lower()
            .strip()
        )

    def _clean_app_target(self, raw: str) -> str:
        """Retire politesses et ponctuation autour du nom d'application."""
        target = self._normalize(raw)
        target = re.sub(r"\s+s'il\s+te\s+pla[iî]t.*$", "", target)
        target = re.sub(r"\s+stp.*$", "", target)
        target = re.sub(r"\s+svp.*$", "", target)
        target = re.split(r"\s+et\s+(?:cherche|tape|écri|ecri|va)\b", target, maxsplit=1)[0]
        return target.strip(" .!?,;:")

    def parse_app_action(self, instruction: str) -> tuple[str, str] | None:
        """Détecte une demande d'ouverture ou de fermeture d'application.

        Returns:
            ("open"|"close"|"open_maybe", nom) ou None.
            open_maybe = le message est seulement un nom, à confirmer dans le catalogue.
        """
        inst = self._normalize(instruction)
        if not inst or "?" in inst:
            return None

        close_pat = re.compile(
            rf"{self._CLOSE_VERB}\s+{self._ARTICLE}(.*)",
            re.IGNORECASE,
        )
        match = close_pat.search(inst)
        if match:
            target = self._clean_app_target(match.group(1))
            if target and not target.startswith("recherche"):
                return ("close", target)

        open_pat = re.compile(
            rf"{self._OPEN_VERB}\s+{self._ARTICLE}(.*)",
            re.IGNORECASE,
        )
        match = open_pat.search(inst)
        if match:
            target = self._clean_app_target(match.group(1))
            if target and not re.search(r"\brecherche\b", target):
                return ("open", target)

        words = inst.split()
        if 1 <= len(words) <= 4 and not any(
            word in inst for word in ("cherche", "recherche", "volume", "luminosite", "bonjour", "salut")
        ):
            return ("open_maybe", inst)
        return None

    def parse(self, instruction: str) -> str | None:
        """Analyse l'instruction et retourne une commande PowerShell si reconnue.

        L'ouverture d'applications n'est pas traitée ici : elle passe par
        parse_app_action puis le catalogue des applications installées.
        """
        inst = self._normalize(instruction)

        m = re.search(r"lumi\w*\s*[àa]?\s*(\d+)", inst)
        if m:
            level = max(0, min(100, int(m.group(1))))
            logger.info(f"FastParser: luminosité → {level}%")
            return (
                "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                f".WmiSetBrightness(1, {level})"
            )

        if any(kw in inst for kw in ["muet", "coupe le son", "désactive le son", "silence", "mute"]):
            logger.info("FastParser: mute")
            return "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"

        m = re.search(r"(?:volume|son)\s*[àa]?\s*(\d+)", inst)
        if m:
            level = max(0, min(100, int(m.group(1))))
            logger.info(f"FastParser: volume → {level}%")
            return (
                "$obj = New-Object -ComObject WScript.Shell; "
                "1..50 | ForEach-Object { $obj.SendKeys([char]174) }; "
                f"1..{level} | ForEach-Object {{ $obj.SendKeys([char]175) }}"
            )

        if any(kw in inst for kw in ["musique suivante", "titre suivant", "chanson suivante", "suivant"]):
            return "(New-Object -ComObject WScript.Shell).SendKeys([char]176)"
        if any(kw in inst for kw in ["musique précédente", "titre précédent", "chanson précédente", "précédent"]):
            return "(New-Object -ComObject WScript.Shell).SendKeys([char]177)"
        if any(kw in inst for kw in ["pause musique", "play", "joue la musique", "reprends la musique"]):
            return "(New-Object -ComObject WScript.Shell).SendKeys([char]179)"

        if "verrouille" in inst and any(kw in inst for kw in ["pc", "ordinateur", "écran", "ecran", "session"]):
            logger.info("FastParser: verrouillage")
            return "rundll32.exe user32.dll,LockWorkStation"

        if any(kw in inst for kw in ["vide la corbeille", "vider la corbeille", "vide corbeille"]):
            logger.info("FastParser: vider corbeille")
            return "Clear-RecycleBin -Force -Confirm:$false"

        if any(kw in inst for kw in ["capture d'écran", "screenshot", "prends une photo de l'écran", "imprime écran"]):
            logger.info("FastParser: capture d'écran")
            return (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "[System.Windows.Forms.SendKeys]::SendWait('%{PRTSC}')"
            )

        return None
