import pytest
from src.memory.memory_manager import EnhancedMemoryManager

def test_working_memory(db_session):
    """Test working memory functionality"""
    memory_manager = EnhancedMemoryManager()
    
    # Add some turns
    for i in range(7):  # More than max_turns (5)
        memory_manager.process_turn(
            f"Player input {i}", 
            f"AI response {i}"
        )
    
    # Should only keep last 5
    working_memory = memory_manager.working_memory.get_memory()
    assert len(working_memory) == 5
    
    # Should be the most recent ones
    assert "Player input 6" in working_memory[-1]['player_input']

def test_persistent_memory(db_session):
    """Test persistent memory storage and retrieval"""
    memory_manager = EnhancedMemoryManager()
    
    memory_manager.process_turn("I attack the dragon", "The dragon roars!")
    memory_manager.process_turn("I cast fireball", "Flames engulf the dragon!")
    
    # Test retrieval
    relevant = memory_manager.persistent_memory.retrieve_relevant_turns("dragon")
    assert len(relevant) > 0

def test_context_building(db_session):
    """Test context building for LLM"""
    memory_manager = EnhancedMemoryManager()
    
    memory_manager.process_turn("Hello", "Welcome to the adventure!")
    memory_manager.process_turn("I explore the forest", "You find a clearing!")
    
    context = memory_manager.get_context_for_llm("What do I see?")
    assert "Welcome to the adventure" in context
    assert "forest" in context
