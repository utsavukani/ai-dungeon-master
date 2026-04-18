import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text, ForeignKey
from src.database.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, default="New Adventure")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_played = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Character(Base):
    __tablename__ = "characters"
    id = Column(String, primary_key=True, default=generate_uuid)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    name = Column(String, default="Adventurer")
    level = Column(Integer, default=1)
    health = Column(Integer, default=100)
    max_health = Column(Integer, default=100)
    experience = Column(Integer, default=0)
    gold = Column(Integer, default=50)
    strength = Column(Integer, default=10)
    intelligence = Column(Integer, default=10)
    charisma = Column(Integer, default=10)
    inventory = Column(JSON, default=list)
    abilities = Column(JSON, default=list)
    status_effects = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GameTurn(Base):
    __tablename__ = "game_turns"
    id = Column(String, primary_key=True, default=generate_uuid)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat())
    turn_number = Column(Integer, nullable=False)
    player_input = Column(Text, default="")
    ai_response = Column(Text, default="")
    context = Column(Text, default="{}")
    importance_score = Column(Float, default=1.0)
    summary = Column(Text, default="")
    key_entities = Column(Text, default="[]")

class StorySummary(Base):
    __tablename__ = "story_summaries"
    id = Column(String, primary_key=True, default=generate_uuid)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    turn_range = Column(String)
    summary = Column(Text)
    key_events = Column(Text)
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat())

class NPC(Base):
    __tablename__ = "npcs"
    npc_id = Column(String, primary_key=True) # E.g., UUID or unique string
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    name = Column(String)
    first_met_turn = Column(Integer)
    personality_traits = Column(Text)
    relationship_status = Column(String, default="neutral")
    last_interaction_turn = Column(Integer)
    memory_summary = Column(Text)
    interaction_count = Column(Integer, default=0)

class NPCInteraction(Base):
    __tablename__ = "npc_interactions"
    id = Column(String, primary_key=True, default=generate_uuid)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    npc_id = Column(String, ForeignKey("npcs.npc_id"))
    turn_number = Column(Integer)
    player_action = Column(Text)
    npc_response = Column(Text)
    relationship_change = Column(Text)
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat())

class Quest(Base):
    __tablename__ = "quests"
    id = Column(Integer, primary_key=True, autoincrement=True) 
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, default="active")
    start_turn = Column(Integer)
    completion_turn = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    progress = Column(JSON, default=list)
