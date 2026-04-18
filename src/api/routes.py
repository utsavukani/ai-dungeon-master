from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from src.database.database import SessionLocal
from src.database.models import Character, Quest, User, Campaign
import bcrypt
import uuid

api_router = APIRouter()

# ─────────────────────────────────────────────
#  Request/Response Schemas
# ─────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class CreateCampaignRequest(BaseModel):
    user_id: str
    name: str = "New Adventure"


# ─────────────────────────────────────────────
#  Auth Endpoints
# ─────────────────────────────────────────────

@api_router.post("/auth/register")
def register(req: RegisterRequest):
    """Register a new user account."""
    if len(req.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == req.username.strip()).first():
            raise HTTPException(status_code=409, detail="Username already taken.")

        hashed = bcrypt.hashpw(req.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = User(
            id=str(uuid.uuid4()),
            username=req.username.strip(),
            password_hash=hashed
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"status": "success", "user_id": user.id, "username": user.username}
    finally:
        db.close()


@api_router.post("/auth/login")
def login(req: LoginRequest):
    """Login with username and password."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == req.username.strip()).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        if not bcrypt.checkpw(req.password.encode("utf-8"), user.password_hash.encode("utf-8")):
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        return {"status": "success", "user_id": user.id, "username": user.username}
    finally:
        db.close()


# ─────────────────────────────────────────────
#  Campaign Endpoints
# ─────────────────────────────────────────────

@api_router.post("/campaigns")
def create_campaign(req: CreateCampaignRequest):
    """Create a new campaign for a user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == req.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        campaign = Campaign(
            id=str(uuid.uuid4()),
            user_id=req.user_id,
            name=req.name.strip() or "New Adventure"
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return {
            "status": "success",
            "campaign_id": campaign.id,
            "name": campaign.name,
            "created_at": campaign.created_at.isoformat()
        }
    finally:
        db.close()


@api_router.get("/campaigns")
def list_campaigns(user_id: str = Query(..., description="User ID")):
    """List all campaigns belonging to a user."""
    db = SessionLocal()
    try:
        campaigns = db.query(Campaign).filter(Campaign.user_id == user_id).order_by(Campaign.last_played.desc()).all()
        return {
            "status": "success",
            "campaigns": [
                {
                    "id": c.id,
                    "name": c.name,
                    "created_at": c.created_at.isoformat(),
                    "last_played": c.last_played.isoformat() if c.last_played else None
                }
                for c in campaigns
            ]
        }
    finally:
        db.close()


# ─────────────────────────────────────────────
#  Game State Endpoints
# ─────────────────────────────────────────────

@api_router.get("/character")
def get_character(campaign_id: str = Query(..., description="ID of the Campaign Session")):
    """Returns the player's character sheet and full inventory."""
    db = SessionLocal()
    try:
        char = db.query(Character).filter(Character.campaign_id == campaign_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found for this campaign")
        
        return {
            "status": "success",
            "stats": {
                "name": char.name,
                "level": char.level,
                "health": char.health,
                "max_health": char.max_health,
                "experience": char.experience,
                "gold": char.gold,
                "strength": char.strength,
                "intelligence": char.intelligence,
                "charisma": char.charisma
            },
            "inventory": char.inventory,
            "abilities": char.abilities
        }
    finally:
        db.close()


@api_router.get("/quests")
def get_quests(campaign_id: str = Query(..., description="ID of the Campaign Session")):
    """Returns all active and completed quests."""
    db = SessionLocal()
    try:
        active_quests = db.query(Quest).filter(Quest.campaign_id == campaign_id, Quest.status == 'active').all()
        completed_quests = db.query(Quest).filter(Quest.campaign_id == campaign_id, Quest.status == 'completed').all()
        
        return {
            "status": "success",
            "active_quests": [{
                "id": q.id, "description": q.description, "status": q.status, 
                "start_turn": q.start_turn, "progress": q.progress
            } for q in active_quests],
            "completed_quests": [{
                "id": q.id, "description": q.description, "status": q.status, 
                "completion_turn": q.completion_turn, "progress": q.progress
            } for q in completed_quests]
        }
    finally:
        db.close()
