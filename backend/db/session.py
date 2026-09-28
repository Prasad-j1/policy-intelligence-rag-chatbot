from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

# The engine is the core interface to the database itself.
# check_same_thread=False is required for SQLite specifically, since
# FastAPI can handle requests across multiple threads, and SQLite's
# default behavior blocks that.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# SessionLocal is a factory that creates new database sessions on demand.
# Each request gets its own session, used and closed within that request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is what all your SQLAlchemy models (models.py) will inherit from.
# It's what lets SQLAlchemy map your Python classes to actual database tables.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency — provides a database session to a route,
    and guarantees it gets closed afterward, even if an error occurs.

    Usage in a route:
        @router.post("/ask")
        def ask_question(request: ChatRequest, db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Creates all tables defined in models.py, if they don't already exist.
    Called once at app startup (main.py), similar to how we warm up the
    embedding model.
    """
    # Import models here (not at top of file) so Base knows about all
    # tables before create_all() runs, without causing a circular import
    # between session.py and models.py
    from backend.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)