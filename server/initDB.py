import json
import chromadb
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table, DateTime, Text
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

# Define Task model
class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    progress = Column(String, nullable=False)
    result = Column(Text)

# Create tables
Base.metadata.drop_all(engine)  # Drop existing tables
Base.metadata.create_all(engine)

print("Database tables initialized successfully.")

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

def create_folder_structure(structure, parent=None):
    folder = create_folder(structure['name'], parent, structure.get('description'))
    for child in structure.get('children', []):
        create_folder_structure(child, folder)

# Load folder structure from JSON file
with open('folder_structure.json', 'r') as f:
    folder_structure = json.load(f)

# Create folder structure
create_folder_structure(folder_structure)

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

# Clear task table
session.query(Task).delete()
session.commit()
print("\nTask table cleared successfully.")

session.close()

print("\nDatabase setup complete.")