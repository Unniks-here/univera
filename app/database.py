from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings

# SQLAlchemy engine and session setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for getting DB session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
