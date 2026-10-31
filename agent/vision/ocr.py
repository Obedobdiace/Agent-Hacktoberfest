"""Module OCR pour l'extraction de texte."""

import logging
from typing import Optional

import easyocr


logger = logging.getLogger(__name__)


class OCRProcessor:
    """Processeur OCR utilisant EasyOCR."""

    def __init__(self, languages: list[str] | None = None) -> None:
        """Initialise le processeur OCR.

        Args:
            languages: Liste des langues à détecter (ex: ['en', 'fr']).
        """
        if languages is None:
            languages = ["en"]

        self.languages = languages
        self.reader = None
        self._load_reader()

    def _load_reader(self) -> None:
        """Charge le lecteur OCR."""
        try:
            self.reader = easyocr.Reader(self.languages, gpu=False)
            logger.info(f"Reader OCR chargé pour les langues: {self.languages}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du reader OCR: {e}")
            raise

    def extract_text(self, image_path: str) -> list[dict[str, any]]:
        """Extrait le texte d'une image.

        Args:
            image_path: Chemin vers l'image.

        Returns:
            Liste de résultats avec texte, bbox et confiance.
        """
        if self.reader is None:
            raise RuntimeError("Reader OCR non initialisé")

        try:
            results = self.reader.readtext(image_path)

            formatted_results = []
            for bbox, text, confidence in results:
                formatted_results.append(
                    {
                        "text": text,
                        "bbox": bbox,
                        "confidence": float(confidence),
                    }
                )

            logger.info(f"Texte extrait: {len(formatted_results)} résultats")
            return formatted_results

        except Exception as e:
            logger.error(f"Erreur lors de l'extraction OCR: {e}")
            raise

    def search_text(
        self,
        image_path: str,
        search_text: str,
        case_sensitive: bool = False,
    ) -> list[dict[str, any]]:
        """Recherche un texte spécifique dans une image.

        Args:
            image_path: Chemin vers l'image.
            search_text: Texte à rechercher.
            case_sensitive: Si True, recherche sensible à la casse.

        Returns:
            Liste des résultats correspondants.
        """
        results = self.extract_text(image_path)

        if not case_sensitive:
            search_text = search_text.lower()

        matching_results = []
        for result in results:
            text_to_check = result["text"] if case_sensitive else result["text"].lower()

            if search_text in text_to_check:
                matching_results.append(result)

        logger.info(f"Recherche '{search_text}': {len(matching_results)} correspondances")
        return matching_results
