import re
import json
from typing import List, Dict
from datetime import datetime
from src.database.database import SessionLocal
from src.database.models import Quest


class QuestTracker:
    """Automatic quest detection and tracking system bound to a Campaign"""

    def __init__(self, campaign_id: str):
        self.campaign_id = campaign_id

    def get_active_quests(self) -> List[Dict]:
        db = SessionLocal()
        try:
            qs = db.query(Quest).filter(Quest.campaign_id == self.campaign_id, Quest.status == 'active').all()
            return [self._quest_to_dict(q) for q in qs]
        finally:
            db.close()

    def get_completed_quests(self) -> List[Dict]:
        db = SessionLocal()
        try:
            qs = db.query(Quest).filter(Quest.campaign_id == self.campaign_id, Quest.status == 'completed').all()
            return [self._quest_to_dict(q) for q in qs]
        finally:
            db.close()

    def _quest_to_dict(self, quest: Quest) -> Dict:
        return {
            'id': quest.id,
            'description': quest.description,
            'status': quest.status,
            'start_turn': quest.start_turn,
            'completion_turn': quest.completion_turn,
            'created_at': quest.created_at.isoformat() if quest.created_at else None,
            'completed_at': quest.completed_at.isoformat() if quest.completed_at else None,
            'progress': quest.progress
        }

    def add_quest(self, description: str, turn_number: int) -> bool:
        """Explicitly add a new quest (called by Structured Output JSON)"""
        if len(description) < 5 or self._is_duplicate_quest(description):
            return False

        db = SessionLocal()
        try:
            new_quest = Quest(
                campaign_id=self.campaign_id,
                description=description,
                status='active',
                start_turn=turn_number,
                progress=["Quest started"]
            )
            db.add(new_quest)
            db.commit()
            return True
        finally:
            db.close()

    def _is_duplicate_quest(self, description: str) -> bool:
        active_quests = self.get_active_quests()
        for quest in active_quests:
            if self._similarity(quest['description'].lower(), description.lower()) > 0.7:
                return True
        return False

    def _similarity(self, a: str, b: str) -> float:
        words_a = set(a.split())
        words_b = set(b.split())
        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)
        return len(intersection) / len(union) if union else 0



    def complete_quest(self, quest_id: int, turn_number: int) -> str:
        db = SessionLocal()
        try:
            q = db.query(Quest).filter(Quest.id == quest_id).first()
            if q:
                q.status = 'completed'
                q.completion_turn = turn_number
                q.completed_at = datetime.utcnow()
                db.commit()
                return f"✅ Quest Completed: {q.description}"
            return f"Quest {quest_id} not found."
        finally:
            db.close()

    def add_progress(self, quest_id: int, progress_note: str):
        db = SessionLocal()
        try:
            q = db.query(Quest).filter(Quest.id == quest_id).first()
            if q:
                current_progress = list(q.progress)
                current_progress.append({
                    'note': progress_note,
                    'timestamp': datetime.utcnow().isoformat()
                })
                q.progress = current_progress
                db.commit()
                return f"Progress added to quest {quest_id}"
            return f"Quest {quest_id} not found."
        finally:
            db.close()

    def complete_quest_by_description(self, quest_description: str, turn_number: int) -> str:
        """Explicitly complete a quest based on structured output string"""
        active_quests = self.get_active_quests()
        for quest in active_quests:
            if self._similarity(quest['description'].lower(), quest_description.lower()) >= 0.5:
                return self.complete_quest(quest['id'], turn_number)
        return ""

    def display_quests(self):
        active_quests = self.get_active_quests()
        completed_quests = self.get_completed_quests()

        print(f"\n{'='*40}")
        print(f"QUEST LOG")
        print(f"{'='*40}")

        if active_quests:
            print(f"\n🔥 ACTIVE QUESTS ({len(active_quests)}):")
            for quest in active_quests:
                print(f"  [{quest['id']}] {quest['description']}")
                if quest['progress']:
                    print(f"      Progress: {len(quest['progress'])} updates")
        else:
            print("\n🔥 ACTIVE QUESTS: None")

        if completed_quests:
            print(f"\n✅ COMPLETED QUESTS ({len(completed_quests)}):")
            for quest in completed_quests[-5:]:  # Show last 5
                print(f"  [{quest['id']}] {quest['description']}")

        print(f"{'='*40}")

    def get_stats(self) -> Dict:
        active = len(self.get_active_quests())
        completed = len(self.get_completed_quests())
        total = active + completed
        return {
            'active_count': active,
            'completed_count': completed,
            'total_quests': total,
            'completion_rate': (completed / max(1, total)) * 100
        }
