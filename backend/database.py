"""
NetSync Gov — Session SQLAlchemy pour FastAPI
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import config

engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    """Dependency FastAPI — fournit une session BDD et la ferme après la requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
