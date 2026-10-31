"""Cerveau Gemma, appelé par l'API Google (pas en local)."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def use_gemma() -> bool:
    """Vrai quand la conversation et les actions passent par l'API Gemma."""
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider in {"gemini"}:
        return False
    if provider in {"gemma", "google", "api"}:
        return True
    return bool(os.getenv("GEMMA_API_KEY"))


def redact(text: str) -> str:
    """Retire les clés API d'un message d'erreur avant de l'afficher ou de le journaliser."""
    cleaned = text
    for name in ("GEMMA_API_KEY", "GOOGLE_API_KEY"):
        secret = os.getenv(name) or ""
        if secret:
            cleaned = cleaned.replace(secret, "***")
    return cleaned


def extract_json(raw: str) -> dict:
    """Récupère l'objet JSON même si le modèle a ajouté du texte ou une clôture."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return parsed[0]
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("objet attendu", text, 0)
    return parsed


class GemmaModel:
    """Même rôle que l'analyseur Gemini, mais avec le modèle Gemma de l'API Google."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMMA_API_KEY") or ""
        self.model = model or os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")

    def describe_status(self) -> str:
        """Vérifie que la clé et le modèle répondent."""
        if not self.api_key:
            return "Gemma non connecté : GEMMA_API_KEY est absente du fichier .env."
        try:
            reply = self._generate("Réponds uniquement le mot ok.", timeout_ms=20000)
        except Exception as exc:
            return f"Gemma non connecté ({self.model}) : {redact(str(exc))}"
        if not reply:
            return f"Gemma a répondu vide ({self.model})."
        return f"Gemma connecté ({self.model})."

    def generate_text(self, prompt: str) -> str:
        """Génère du texte. En cas d'échec, renvoie le message d'erreur."""
        try:
            return self._generate(prompt)
        except Exception as exc:
            logger.error("Génération Gemma: %s", redact(str(exc)))
            return f"Erreur de génération : {redact(str(exc))}"

    def analyze_screen(self, image_path: str, question: str, context: str | None = None) -> str:
        """Choisit la prochaine action. Si le modèle refuse l'image, il continue sur le texte."""
        prompt = question if not context else f"Contexte: {context}\n\nQuestion: {question}"
        try:
            return self._generate(prompt, image_path=image_path)
        except Exception as exc:
            logger.warning("Capture illisible par Gemma (%s), poursuite sans image.", redact(str(exc)))
            return self.generate_text(prompt + "\n\nLa capture d'écran n'est pas disponible.")

    def complete(
        self,
        system: str,
        history: list[dict],
        user_message: str,
        json_mode: bool = False,
    ) -> str:
        """Conversation. La consigne système est mise dans le message, Gemma n'a pas de rôle système séparé."""
        del json_mode
        lines = [system, "", "Historique récent :"]
        for turn in history:
            who = "Utilisateur" if turn.get("role") == "user" else "Hacktoberfest"
            content = str(turn.get("content", "")).strip()
            if content:
                lines.append(f"{who} : {content}")
        lines.append(f"Utilisateur : {user_message}")
        lines.append("Réponds maintenant avec le JSON demandé, et rien d'autre.")
        return self._generate("\n".join(lines))

    def _generate(self, prompt: str, image_path: str | None = None, timeout_ms: int = 120000) -> str:
        if not self.api_key:
            raise RuntimeError("GEMMA_API_KEY est absente")
        from google import genai

        client = genai.Client(api_key=self.api_key, http_options={"timeout": timeout_ms})
        contents: list = [prompt]
        if image_path:
            contents.append({"mime_type": "image/png", "data": Path(image_path).read_bytes()})
        response = client.models.generate_content(model=self.model, contents=contents)
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise RuntimeError("Gemma a renvoyé une réponse vide")
        return text
