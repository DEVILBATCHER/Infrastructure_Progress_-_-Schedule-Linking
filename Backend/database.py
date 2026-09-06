import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database connection URL (update username, password, or DB name if needed)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./test.db"
)

# Create the database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread":False})

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for your database models to inherit from
Base = declarative_base()

# Dependency function to provide a database session to API routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

