"""Module de capture d'écran."""

import logging
from pathlib import Path
from typing import Optional

import mss
import PIL.Image as Image


logger = logging.getLogger(__name__)


class ScreenCapture:
    """Capture d'écran utilisant mss et PIL."""

    def __init__(self, output_dir: Optional[str] = None) -> None:
        """Initialise le module de capture.

        Args:
            output_dir: Répertoire de sortie pour les captures (optionnel).
        """
        self.output_dir = Path(output_dir) if output_dir else Path("./captures")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sct = mss.mss()

    def capture_full_screen(self, save_path: Optional[str] = None) -> str:
        """Capture l'écran complet.

        Args:
            save_path: Chemin de sauvegarde (optionnel).

        Returns:
            Chemin vers l'image capturée.
        """
        monitor = self.sct.monitors[0]  # Écran principal
        screenshot = self.sct.grab(monitor)

        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

        if save_path is None:
            save_path = self.output_dir / f"screenshot_{self._get_timestamp()}.png"
        else:
            save_path = Path(save_path)

        img.save(save_path)
        logger.info(f"Capture sauvegardée: {save_path}")

        return str(save_path)

    def capture_region(
        self,
        top: int,
        left: int,
        width: int,
        height: int,
        save_path: Optional[str] = None,
    ) -> str:
        """Capture une région de l'écran.

        Args:
            top: Position Y du coin supérieur.
            left: Position X du coin gauche.
            width: Largeur de la région.
            height: Hauteur de la région.
            save_path: Chemin de sauvegarde (optionnel).

        Returns:
            Chemin vers l'image capturée.
        """
        monitor = {
            "top": top,
            "left": left,
            "width": width,
            "height": height,
        }

        screenshot = self.sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

        if save_path is None:
            save_path = self.output_dir / f"region_{self._get_timestamp()}.png"
        else:
            save_path = Path(save_path)

        img.save(save_path)
        logger.info(f"Région capturée: {save_path}")

        return str(save_path)

    def _get_timestamp(self) -> str:
        """Génère un timestamp pour le nom de fichier.

        Returns:
            Timestamp formaté.
        """
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")
