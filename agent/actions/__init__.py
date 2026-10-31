"""Modules actions de l'agent."""

from agent.actions.mouse import MouseController
from agent.actions.keyboard import KeyboardController
from agent.actions.apps import AppController

__all__ = ["MouseController", "KeyboardController", "AppController"]
