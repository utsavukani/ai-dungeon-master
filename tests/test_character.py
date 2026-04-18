import pytest
from src.game.character_sheet import CharacterSheet

def test_character_creation(db_session):
    sheet = CharacterSheet()
    assert sheet.stats['name'] == 'Adventurer'
    assert sheet.stats['level'] == 1
    assert sheet.stats['health'] == 100
    assert sheet.character_id is not None

def test_character_persistence(db_session):
    sheet1 = CharacterSheet()
    char_id = sheet1.character_id
    sheet1.take_damage(20)
    sheet1.gain_experience(150) # Level up
    
    sheet2 = CharacterSheet(character_id=char_id)
    assert sheet2.stats['health'] == 120 # Health scales with level
    assert sheet2.stats['level'] == 2

def test_inventory_management(db_session):
    sheet = CharacterSheet()
    sheet.add_item("Magic Sword")
    assert "Magic Sword" in sheet.inventory
    sheet.remove_item("Magic Sword")
    assert "Magic Sword" not in sheet.inventory

def test_health_management(db_session):
    sheet = CharacterSheet()
    sheet.take_damage(30)
    assert sheet.stats['health'] == 70
    sheet.heal(20)
    assert sheet.stats['health'] == 90
