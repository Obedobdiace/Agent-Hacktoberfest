"""L'écoute vocale peut être annulée sans session en cours."""

from agent.voice.listener import cancel_listen


def test_cancel_listen_without_active_session() -> None:
    cancel_listen()
