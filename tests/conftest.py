import os
import uuid
import pytest
from unittest.mock import MagicMock

# ── 1. Point at in-memory SQLite before any src imports ──────────────────────
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from src.database.database import Base, SessionLocal, engine
from src.database.models import Campaign, User

# ── 2. Create all tables once per session ────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# ── 3. Isolated DB session per test ──────────────────────────────────────────
@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()

# ── 4. A ready-made campaign in the test DB ───────────────────────────────────
@pytest.fixture
def test_campaign_id(db_session):
    """Creates a user + campaign in the in-memory DB and returns the campaign_id."""
    user = User(user_id=str(uuid.uuid4()), username="test_user", password_hash="hashed")
    db_session.add(user)
    db_session.flush()

    campaign_id = str(uuid.uuid4())
    campaign = Campaign(
        campaign_id=campaign_id,
        user_id=user.user_id,
        name="Test Campaign",
    )
    db_session.add(campaign)
    db_session.commit()
    return campaign_id

# ── 5. Mock ChromaDB so tests never download the ~90MB sentence-transformer ───
@pytest.fixture(autouse=True)
def mock_chroma_memory(monkeypatch):
    """
    Patch ChromaMemory so CI doesn't download the sentence-transformers model.
    Each test still exercises the full SQL memory stack.
    """
    mock = MagicMock()
    mock.return_value.add_turn.return_value = None
    mock.return_value.retrieve_similar.return_value = []
    monkeypatch.setattr("src.memory.memory_manager.ChromaMemory", mock)
