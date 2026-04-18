import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Mock the database URL before importing anything else
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from src.database.database import Base, SessionLocal, engine

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables in the in-memory database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    """Returns a new database session for a test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback() # ensure isolation
        # Clear out tables manually since sqlite in memory keeps them
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()
