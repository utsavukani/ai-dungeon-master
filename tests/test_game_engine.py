import pytest
from unittest.mock import patch
from src.game.game_engine import UltimateGameEngine

def test_engine_init(db_session):
    engine = UltimateGameEngine()
    assert engine.game_started is False
    assert "total_turns" in engine.game_stats
    assert engine.memory_manager is not None
    assert engine.character_sheet is not None
