"""Module pour les actions de recherche web."""

import logging
from typing import Optional
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class SearchController:
    """Contrôleur pour les recherches sur le web."""

    def __init__(self) -> None:
        """Initialise le contrôleur de recherche."""
        pass

    def search_web(self, query: str, max_results: int = 5) -> list[dict]:
        """Effectue une recherche web via DuckDuckGo.

        Args:
            query: La requête de recherche.
            max_results: Le nombre maximum de résultats.

        Returns:
            Une liste de dictionnaires contenant 'title', 'body', et 'href'.
        """
        logger.info(f"Recherche web: '{query}'")
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(r)
            return results
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return []

    def format_results(self, results: list[dict]) -> str:
        """Formate les résultats de recherche en texte lisible.

        Args:
            results: Liste de résultats de search_web.

        Returns:
            Texte formaté.
        """
        if not results:
            return "Aucun résultat trouvé."

        formatted = ""
        for i, res in enumerate(results, 1):
            title = res.get('title', 'Sans titre')
            body = res.get('body', 'Aucune description.')
            href = res.get('href', '')
            formatted += f"### {i}. {title}\n"
            formatted += f"{body}\n"
            formatted += f"Lien: {href}\n\n"
        
        return formatted
