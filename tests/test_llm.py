"""Lecture des réponses JSON de Gemma, sans appeler l'API."""

import json

import pytest

from agent.core.llm import extract_json


def test_extract_json_plain() -> None:
    parsed = extract_json('{"type": "chat", "response": "Bonjour"}')
    assert parsed["type"] == "chat"
    assert parsed["response"] == "Bonjour"


def test_extract_json_with_fence_and_preamble() -> None:
    raw = "Voici la décision :\n```json\n{\"type\": \"command\", \"task\": \"ouvrir chrome\", \"ack\": \"Je lance Chrome.\"}\n```"
    parsed = extract_json(raw)
    assert parsed["type"] == "command"
    assert parsed["task"] == "ouvrir chrome"


def test_extract_json_rejects_non_object() -> None:
    with pytest.raises(json.JSONDecodeError):
        extract_json('["juste une liste"]')
