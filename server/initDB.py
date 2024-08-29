import json
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from database import Base, engine
from models import Folder, Favorite, Tag, Task, FavoriteToProcess, favorite_tags

# Initialize SQLAlchemy
engine = create_engine('sqlite:///favorites.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

def clear_non_embedding_tables():
    # Get all table names
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()

    # Tables to keep (related to vector embeddings)
    tables_to_keep = []  # We're not keeping any tables now, as favorites_embeddings is not in SQLite

    # Drop tables not related to embeddings
    for table in all_tables:
        if table not in tables_to_keep:
            session.execute(text(f"DELETE FROM {table}"))
            print(f"Cleared table: {table}")

    session.commit()
    print("Cleared all non-embedding tables.")

    # Recreate tables (this step is necessary if any tables were completely dropped)
    Base.metadata.create_all(engine)
    print("Ensured all tables exist.")

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

def print_folder_structure(folder, level=0):
    print("  " * level + f"- {folder.name}")
    for child in folder.children:
        print_folder_structure(child, level + 1)

if __name__ == "__main__":
    print("Clearing non-embedding tables...")
    clear_non_embedding_tables()

    print("\nCreating initial folders...")
    # Load folder structure from JSON file
    with open('folder_structure.json', 'r') as f:
        folder_structure = json.load(f)

    # Create folder structure
    create_folder_structure(folder_structure)
    session.commit()

    print("Initial folders created successfully.")

    # Verify folder structure
    root = session.query(Folder).filter(Folder.name == "Favorites").first()
    print("\nFolder structure:")
    print_folder_structure(root)

    session.close()
    print("\nDatabase setup complete.")