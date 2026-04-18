import json
from typing import Dict, List
from src.database.database import SessionLocal
from src.database.models import Character


class CharacterSheet:
    """Player character tracking system bound to a specific DB Campaign"""

    def __init__(self, campaign_id: str):
        self.campaign_id = campaign_id
        self.character_id = None
        self._load_or_create()

    def _load_or_create(self):
        db = SessionLocal()
        # Find the character linked strictly to this campaign
        char = db.query(Character).filter(Character.campaign_id == self.campaign_id).first()
        
        # If no character exists for this campaign, create one
        if not char:
            char = Character(campaign_id=self.campaign_id)
            db.add(char)
            db.commit()
            db.refresh(char)
            
        self.character_id = char.id
        self._load_from_db(char)
        db.close()

    def _load_from_db(self, char):
        self.stats = {
            'name': char.name,
            'level': char.level,
            'health': char.health,
            'max_health': char.max_health,
            'experience': char.experience,
            'gold': char.gold,
            'strength': char.strength,
            'intelligence': char.intelligence,
            'charisma': char.charisma
        }
        self.inventory = list(char.inventory)
        self.abilities = list(char.abilities)
        self.status_effects = list(char.status_effects)

    def _save(self):
        db = SessionLocal()
        try:
            char = db.query(Character).filter(Character.id == self.character_id).first()
            if char:
                char.name = self.stats['name']
                char.level = self.stats['level']
                char.health = self.stats['health']
                char.max_health = self.stats['max_health']
                char.experience = self.stats['experience']
                char.gold = self.stats['gold']
                char.strength = self.stats['strength']
                char.intelligence = self.stats['intelligence']
                char.charisma = self.stats['charisma']
                char.inventory = self.inventory
                char.abilities = self.abilities
                char.status_effects = self.status_effects
                db.commit()
        finally:
            db.close()

    def add_item(self, item: str):
        """Add item to inventory"""
        if item and item not in self.inventory:
            self.inventory.append(item)
            self._save()
            return f"Added {item} to inventory!"
        return f"{item} already in inventory."

    def remove_item(self, item: str):
        """Remove item from inventory"""
        if item in self.inventory:
            self.inventory.remove(item)
            self._save()
            return f"Removed {item} from inventory."
        return f"{item} not found in inventory."

    def gain_experience(self, xp: int):
        """Add experience points"""
        self.stats['experience'] += xp
        old_level = self.stats['level']

        # Level up check
        while self.stats['experience'] >= self.stats['level'] * 100:
            self._level_up_internal()

        self._save()
        if self.stats['level'] > old_level:
            return f"Gained {xp} XP! Level up! Now level {self.stats['level']}"
        return f"Gained {xp} experience points."

    def _level_up_internal(self):
        self.stats['level'] += 1
        self.stats['max_health'] += 20
        self.stats['health'] = self.stats['max_health']
        self.stats['strength'] += 2
        self.stats['intelligence'] += 2
        self.stats['charisma'] += 1

    def level_up(self):
        """Level up character manually"""
        self._level_up_internal()
        self._save()

    def take_damage(self, damage: int):
        """Apply damage to character"""
        self.stats['health'] = max(0, self.stats['health'] - damage)
        self._save()
        if self.stats['health'] == 0:
            return "You have fallen unconscious!"
        return f"Took {damage} damage. Health: {self.stats['health']}/{self.stats['max_health']}"

    def heal(self, amount: int):
        """Heal character"""
        old_health = self.stats['health']
        self.stats['health'] = min(
            self.stats['max_health'], self.stats['health'] + amount)
        self._save()
        healed = self.stats['health'] - old_health
        return f"Healed {healed} HP. Health: {self.stats['health']}/{self.stats['max_health']}"

    def display_sheet(self):
        """Display character information"""
        print(f"\n{'='*30}")
        print(f"CHARACTER SHEET")
        print(f"{'='*30}")
        print(f"Name: {self.stats['name']}")
        print(
            f"Level: {self.stats['level']} (XP: {self.stats['experience']}/{self.stats['level'] * 100})")
        print(f"Health: {self.stats['health']}/{self.stats['max_health']}")
        print(f"Gold: {self.stats['gold']}")
        print(f"\nAttributes:")
        print(f"  Strength: {self.stats['strength']}")
        print(f"  Intelligence: {self.stats['intelligence']}")
        print(f"  Charisma: {self.stats['charisma']}")
        print(f"\nInventory ({len(self.inventory)} items):")
        for item in self.inventory:
            print(f"  - {item}")
        print(f"\nAbilities:")
        for ability in self.abilities:
            print(f"  - {ability}")
        if self.status_effects:
            print(f"\nStatus Effects:")
            for effect in self.status_effects:
                print(f"  - {effect}")
        print(f"{'='*30}")

    def to_dict(self) -> Dict:
        """Convert to dictionary for saving"""
        return {
            'character_id': self.character_id,
            'stats': self.stats,
            'inventory': self.inventory,
            'abilities': self.abilities,
            'status_effects': self.status_effects
        }

    def from_dict(self, data: Dict):
        """Load from dictionary"""
        pass # Not used with persistence model handled automatically
