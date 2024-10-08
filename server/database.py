from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get the SQLite database directory from the environment variable
sqlite_dir = os.environ.get('SQLITE_DIR', '.')
database_url = f"sqlite:///{sqlite_dir}/favorites.db"

SQLALCHEMY_DATABASE_URL = database_url

# Create SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to initialize the database
def init_db():
    Base.metadata.create_all(bind=engine)