import os

# Get the database directories from environment variables
sqlite_dir = os.environ.get('SQLITE_DIR', '/data/sqlite')
chroma_dir = os.environ.get('CHROMA_DIR', '/data/chroma')

# Ensure the directories exist
os.makedirs(sqlite_dir, exist_ok=True)
os.makedirs(chroma_dir, exist_ok=True)

# Set the database file paths
sqlite_file = os.path.join(sqlite_dir, 'favorites.db')

# Update the SQLite database URL in the configuration
config_file = 'database.py'
with open(config_file, 'r') as file:
    content = file.read()

# Replace the SQLALCHEMY_DATABASE_URL
new_content = content.replace(
    "SQLALCHEMY_DATABASE_URL = \"sqlite:///./favorites.db\"",
    f"SQLALCHEMY_DATABASE_URL = \"sqlite:///{sqlite_file}\""
)

# Write the updated content back to the file
with open(config_file, 'w') as file:
    file.write(new_content)

print(f"SQLite database path updated to: {sqlite_file}")

# Update the Chroma database path
vector_store_file = 'vector_store.py'
with open(vector_store_file, 'r') as file:
    content = file.read()

# Replace the Chroma persistence directory
new_content = content.replace(
    "persist_directory='chroma_db'",
    f"persist_directory='{chroma_dir}'"
)

# Write the updated content back to the file
with open(vector_store_file, 'w') as file:
    file.write(new_content)

print(f"Chroma database path updated to: {chroma_dir}")