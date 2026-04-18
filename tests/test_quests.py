import pytest
from src.game.quest_tracker import QuestTracker

def test_quest_detection(db_session):
    tracker = QuestTracker()
    quest_desc = "Find the ancient relic in the dark cave"
    
    # Simulate Pydantic JSON extraction calling this:
    detected = tracker.add_quest(quest_desc, 1)
    assert detected is True
    
    active = tracker.get_active_quests()
    assert len(active) == 1
    assert "ancient relic" in active[0]['description'].lower()

def test_quest_completion(db_session):
    tracker = QuestTracker()
    tracker.add_quest("Defeat the goblin king", 1)
    
    active = tracker.get_active_quests()
    assert len(active) == 1
    quest_id = active[0]['id']
    
    tracker.complete_quest(quest_id, 5)
    
    assert len(tracker.get_active_quests()) == 0
    assert len(tracker.get_completed_quests()) == 1

def test_auto_completion(db_session):
    tracker = QuestTracker()
    tracker.add_quest("Defeat the dark dragon", 1)
    
    # Simulate Pydantic JSON extraction calling this:
    result = tracker.complete_quest_by_description("Defeated the dark dragon", 2)
    assert "Completed" in result
    
    assert len(tracker.get_active_quests()) == 0
    assert len(tracker.get_completed_quests()) == 1
