"""Module de contrôle de la souris."""

import logging
import time

import pyautogui


logger = logging.getLogger(__name__)


class MouseController:
    """Contrôleur de souris utilisant pyautogui."""

    def __init__(self) -> None:
        """Initialise le contrôleur de souris."""
        pyautogui.FAILSAFE = True
        logger.info("Contrôleur de souris initialisé")

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.1,
    ) -> None:
        """Clique sur une position de l'écran.

        Args:
            x: Position X.
            y: Position Y.
            button: Bouton à cliquer (left, right, middle).
            clicks: Nombre de clics.
            interval: Intervalle entre les clics.
        """
        logger.info(f"Clic {button} à ({x}, {y})")
        pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=interval)

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        button: str = "left",
    ) -> None:
        """Fait un glisser-déposer.

        Args:
            start_x: Position X de départ.
            start_y: Position Y de départ.
            end_x: Position X d'arrivée.
            end_y: Position Y d'arrivée.
            duration: Durée du mouvement en secondes.
            button: Bouton à maintenir.
        """
        logger.info(f"Drag de ({start_x}, {start_y}) à ({end_x}, {end_y})")
        pyautogui.drag(
            end_x - start_x,
            end_y - start_y,
            duration=duration,
            button=button,
        )

    def scroll(
        self,
        x: int,
        y: int,
        clicks: int = 5,
        direction: str = "down",
    ) -> None:
        """Fait défiler l'écran.

        Args:
            x: Position X pour le scroll.
            y: Position Y pour le scroll.
            clicks: Nombre de clics de scroll.
            direction: Direction (up, down).
        """
        scroll_amount = -clicks if direction == "up" else clicks
        logger.info(f"Scroll à ({x}, {y}): {direction} {abs(clicks)}")
        pyautogui.scroll(scroll_amount, x=x, y=y)

    def move(
        self,
        x: int,
        y: int,
        duration: float = 0.2,
    ) -> None:
        """Déplace la souris sans cliquer.

        Args:
            x: Position X.
            y: Position Y.
            duration: Durée du mouvement en secondes.
        """
        logger.info(f"Déplacement à ({x}, {y})")
        pyautogui.moveTo(x=x, y=y, duration=duration)

    def get_position(self) -> tuple[int, int]:
        """Récupère la position actuelle de la souris.

        Returns:
            Tuple (x, y) de la position.
        """
        x, y = pyautogui.position()
        return x, y
