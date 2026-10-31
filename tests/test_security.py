"""Tests pour le module de sécurité."""

import pytest

from agent.core.security import Action, SecurityGuard, SecurityLevel


def test_safe_action_classification() -> None:
    """Test la classification des actions SAFE."""
    security = SecurityGuard()

    action = Action(action_type="screen_capture", parameters={})
    decision = security.classify(action)

    assert decision.level == SecurityLevel.SAFE
    assert decision.approved is True
    assert decision.requires_confirmation is False


def test_risky_action_classification() -> None:
    """Test la classification des actions RISKY."""
    security = SecurityGuard()

    action = Action(action_type="mouse_click", parameters={"x": 100, "y": 100})
    decision = security.classify(action)

    assert decision.level == SecurityLevel.RISKY
    assert decision.requires_confirmation is True


def test_readonly_mode_blocks_risky() -> None:
    """Test que le mode lecture seule bloque les actions RISKY."""
    security = SecurityGuard(readonly_mode=True)

    action = Action(action_type="mouse_click", parameters={"x": 100, "y": 100})
    decision = security.classify(action)

    assert decision.level == SecurityLevel.RISKY
    assert decision.approved is False
    assert decision.blocked_reason == "Mode lecture seule activé"


def test_blacklisted_operation() -> None:
    """Test que les opérations blacklistées sont bloquées."""
    security = SecurityGuard()

    action = Action(action_type="system_command", parameters={"command": "format C:"})
    decision = security.classify(action)

    assert decision.level == SecurityLevel.CRITICAL
    assert decision.approved is False
    assert "liste noire" in decision.blocked_reason.lower()


def test_protected_path_detection() -> None:
    """Test la détection des chemins protégés."""
    security = SecurityGuard()

    action = Action(
        action_type="file_write",
        parameters={"path": "C:/Windows/system32/config"},
    )
    decision = security.classify(action)

    assert decision.level == SecurityLevel.CRITICAL
    assert decision.approved is False
    assert "chemin protégé" in decision.blocked_reason.lower()
