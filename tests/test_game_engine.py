import pytest
from src.game.game_engine import UltimateGameEngine


@pytest.mark.asyncio
async def test_engine_initializes_for_campaign(test_campaign_id):
    """Game engine initialises correctly for an existing campaign."""
    engine = UltimateGameEngine(campaign_id=test_campaign_id)

    assert engine.game_started is False
    assert "total_turns" in engine.game_stats
    assert engine.memory_manager is not None
    assert engine.character_sheet is not None
    assert engine.quest_tracker is not None
