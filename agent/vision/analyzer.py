"""Module d'analyse vision utilisant l'API Gemini."""

import logging
from pathlib import Path
from typing import Optional

from google import genai


logger = logging.getLogger(__name__)


class VisionAnalyzer:
    """Analyseur vision utilisant l'API Gemini pour l'analyse d'images."""

    def __init__(self, api_key: str) -> None:
        """Initialise l'analyseur vision.

        Args:
            api_key: Clé API Google.
        """
        from google import genai as google_genai
        self.client = google_genai.Client(api_key=api_key)
        self.model = "gemini-2.0-flash"

    def analyze_screen(
        self,
        image_path: str,
        question: str,
        context: Optional[str] = None,
    ) -> str:
        """Analyse une capture d'écran avec une question.

        Args:
            image_path: Chemin vers l'image.
            question: Question à poser sur l'image.
            context: Contexte additionnel (optionnel).

        Returns:
            Réponse de l'analyse.
        """
        try:
            # Lire l'image
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image non trouvée: {image_path}")

            # Construire le prompt
            prompt = question
            if context:
                prompt = f"Contexte: {context}\n\nQuestion: {question}"

            # Lire les bytes
            image_bytes = image_path.read_bytes()

            # Appeler l'API Gemini avec le nouveau SDK (google-genai)
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    prompt,
                    {"mime_type": "image/png", "data": image_bytes}
                ],
            )

            logger.info(f"Analyse vision terminée: {len(response.text)} caractères")

            return response.text

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse vision: {e}")
            raise

    def generate_text(self, prompt: str) -> str:
        """Génère du texte via Gemini (sans image).

        Args:
            prompt: Le texte ou la question pour le modèle.

        Returns:
            La réponse textuelle.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
            )
            logger.info(f"Génération de texte terminée: {len(response.text)} caractères")
            return response.text
        except Exception as e:
            logger.error(f"Erreur lors de la génération de texte: {e}")
            return f"Erreur de génération : {e}"

    def find_element(
        self,
        image_path: str,
        element_description: str,
        context: Optional[str] = None,
    ) -> dict[str, any]:
        """Trouve un élément spécifique sur l'écran.

        Args:
            image_path: Chemin vers l'image.
            element_description: Description de l'élément à trouver.
            context: Contexte additionnel (optionnel).

        Returns:
            Dictionnaire avec les coordonnées et informations de l'élément.
        """
        prompt = f"Trouve l'élément suivant sur l'écran: {element_description}."
        prompt += " Réponds avec les coordonnées (x, y) du centre de l'élément."
        prompt += " Si l'élément n'est pas trouvé, réponds 'NOT_FOUND'."

        if context:
            prompt = f"Contexte: {context}\n\n{prompt}"

        response = self.analyze_screen(image_path, prompt, context)

        # Parser la réponse pour extraire les coordonnées
        if "NOT_FOUND" in response.upper():
            return {"found": False, "reason": "Élément non trouvé"}

        try:
            # Tentative d'extraction des coordonnées
            import re

            coords_match = re.search(r"x[:\s]*(\d+).*y[:\s]*(\d+)", response, re.IGNORECASE)

            if coords_match:
                x = int(coords_match.group(1))
                y = int(coords_match.group(2))
                return {
                    "found": True,
                    "x": x,
                    "y": y,
                    "description": element_description,
                }

            return {"found": False, "reason": "Coordonnées non extraites"}

        except Exception as e:
            logger.error(f"Erreur lors du parsing des coordonnées: {e}")
            return {"found": False, "reason": f"Erreur de parsing: {e}"}
