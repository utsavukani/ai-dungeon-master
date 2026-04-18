import pytest
from src.memory.memory_manager import EnhancedMemoryManager


def test_working_memory(test_campaign_id):
    """Working memory evicts oldest turns once the window is full."""
    memory_manager = EnhancedMemoryManager(campaign_id=test_campaign_id)

    for i in range(7):          # More than max_turns (5)
        memory_manager.process_turn(
            f"Player input {i}",
            f"AI response {i}"
        )

    working_memory = memory_manager.working_memory.get_memory()
    assert len(working_memory) == 5                               # Window capped
    assert "Player input 6" in working_memory[-1]['player_input'] # Most recent kept


def test_persistent_memory(test_campaign_id):
    """Turns written to PostgreSQL can be retrieved by keyword search."""
    memory_manager = EnhancedMemoryManager(campaign_id=test_campaign_id)

    memory_manager.process_turn("I attack the dragon", "The dragon roars!")
    memory_manager.process_turn("I cast fireball",     "Flames engulf the dragon!")

    relevant = memory_manager.persistent_memory.retrieve_relevant_turns("dragon")
    assert len(relevant) > 0


def test_context_building(test_campaign_id):
    """Context string passed to the LLM contains recent turns."""
    memory_manager = EnhancedMemoryManager(campaign_id=test_campaign_id)

    memory_manager.process_turn("Hello",             "Welcome to the adventure!")
    memory_manager.process_turn("I explore the forest", "You find a clearing!")

    context = memory_manager.get_context_for_llm("What do I see?")
    assert "Welcome to the adventure" in context
    assert "forest" in context
