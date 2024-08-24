import chromadb
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

# Initialize ChromaDB
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="favorites_embeddings")

# Initialize SQLAlchemy
engine = create_engine('sqlite:///favorites.db', echo=True)
Base = declarative_base()

# Define SQLAlchemy models
class Folder(Base):
    __tablename__ = 'folders'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey('folders.id'))
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship('Folder', remote_side=[id], back_populates='children')
    children = relationship('Folder', back_populates='parent')

class Favorite(Base):
    __tablename__ = 'favorites'
    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    title = Column(String)
    summary = Column(String)
    folder_id = Column(Integer, ForeignKey('folders.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    folder = relationship('Folder')
    tags = relationship('Tag', secondary='favorite_tags')

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

favorite_tags = Table('favorite_tags', Base.metadata,
    Column('favorite_id', Integer, ForeignKey('favorites.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

# Create tables
Base.metadata.drop_all(engine)  # Drop existing tables
Base.metadata.create_all(engine)

print("Database initialized successfully.")

# Create initial folders
Session = sessionmaker(bind=engine)
session = Session()

def create_folder(name, parent=None, description=None):
    folder = Folder(name=name, description=description)
    if parent:
        folder.parent = parent
    session.add(folder)
    session.flush()  # This will assign an ID to the folder
    return folder

# Create root folder
root_folder = create_folder("Root", description="Root folder for all categories")

# Create main categories
work = create_folder("Work", root_folder, "Work-related favorites")
personal = create_folder("Personal", root_folder, "Personal favorites")
learning = create_folder("Learning", root_folder, "Educational resources")
entertainment = create_folder("Entertainment", root_folder, "Entertainment-related favorites")

# Create subcategories
create_folder("Projects", work, "Work projects")
create_folder("Meetings", work, "Meeting notes and links")

create_folder("Finance", personal, "Personal finance resources")
create_folder("Health", personal, "Health and wellness resources")

create_folder("Courses", learning, "Online courses and tutorials")
create_folder("Books", learning, "Reading list and book resources")

create_folder("Movies", entertainment, "Movie recommendations and reviews")
create_folder("Music", entertainment, "Music playlists and resources")

session.commit()

print("Initial folders created successfully.")

# Verify folder structure
def print_folder_structure(folder, level=0):
    print("  " * level + f"- {folder.name}")
    for child in folder.children:
        print_folder_structure(child, level + 1)

root = session.query(Folder).filter(Folder.name == "Root").first()
print("\nFolder structure:")
print_folder_structure(root)

session.close()

print("\nDatabase setup complete.")