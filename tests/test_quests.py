import pytest
from src.game.quest_tracker import QuestTracker


def test_quest_detection(test_campaign_id):
    """A new quest is stored and visible in the active list."""
    tracker = QuestTracker(campaign_id=test_campaign_id)
    detected = tracker.add_quest("Find the ancient relic in the dark cave", 1)

    assert detected is True
    active = tracker.get_active_quests()
    assert len(active) == 1
    assert "ancient relic" in active[0]['description'].lower()


def test_quest_completion(test_campaign_id):
    """Completing a quest removes it from active and adds it to completed."""
    tracker = QuestTracker(campaign_id=test_campaign_id)
    tracker.add_quest("Defeat the goblin king", 1)

    active = tracker.get_active_quests()
    assert len(active) == 1
    quest_id = active[0]['id']

    tracker.complete_quest(quest_id, 5)

    assert len(tracker.get_active_quests()) == 0
    assert len(tracker.get_completed_quests()) == 1


def test_auto_completion(test_campaign_id):
    """complete_quest_by_description matches fuzzy quest descriptions."""
    tracker = QuestTracker(campaign_id=test_campaign_id)
    tracker.add_quest("Defeat the dark dragon", 1)

    result = tracker.complete_quest_by_description("Defeated the dark dragon", 2)
    assert "Completed" in result

    assert len(tracker.get_active_quests()) == 0
    assert len(tracker.get_completed_quests()) == 1
