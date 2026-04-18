import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv(override=True)

# Ensure data directory exists (for local SQLite / ChromaDB)
os.makedirs("data", exist_ok=True)

# Use DATABASE_URL from env; fall back to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/ai_dm.db")

# Neon (and some other cloud Postgres providers) gives URLs starting with
# "postgres://" which SQLAlchemy 2.x requires as "postgresql+psycopg2://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Build engine — pass SSL args for cloud Postgres, skip for SQLite
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """
    Create all tables that don't exist yet.
    Safe to call on every startup — skips tables that already exist.
    Called automatically at the bottom of this module.
    """
    # Import models here so Base knows about them before create_all runs
    import src.database.models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Auto-initialise on import so every entry-point gets working tables
init_db()
