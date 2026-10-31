"""Module de contrôle du clavier."""

import logging

import pyautogui


logger = logging.getLogger(__name__)


class KeyboardController:
    """Contrôleur de clavier utilisant pyautogui."""

    def __init__(self) -> None:
        """Initialise le contrôleur de clavier."""
        logger.info("Contrôleur de clavier initialisé")

    def type(
        self,
        text: str,
        interval: float = 0.01,
    ) -> None:
        """Tape du texte.

        Args:
            text: Texte à taper.
            interval: Intervalle entre chaque caractère.
        """
        logger.info(f"Typage: {text[:50]}...")
        pyautogui.typewrite(text, interval=interval)

    def press(self, key: str) -> None:
        """Appuie sur une touche.

        Args:
            key: Touche à appuyer (ex: enter, escape, space).
        """
        logger.info(f"Touche pressée: {key}")
        pyautogui.press(key)

    def hotkey(self, *keys: str) -> None:
        """Appuie sur une combinaison de touches.

        Args:
            *keys: Touches de la combinaison (ex: 'ctrl', 'c').
        """
        logger.info(f"Hotkey: {'+'.join(keys)}")
        pyautogui.hotkey(*keys)

    def write(self, text: str) -> None:
        """Écrit du texte (alias pour type).

        Args:
            text: Texte à écrire.
        """
        self.type(text)
