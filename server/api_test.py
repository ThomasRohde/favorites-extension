import pytest
import logging
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from main import app
from database import Base
from services import favorite_service, folder_service, tag_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a new database session for each test
@pytest.fixture(scope="function")
def db():
    logger.info("Setting up test database")
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        logger.info("Tearing down test database")

# Create a test client
@pytest.fixture(scope="module")
def client():
    logger.info("Creating test client")
    with TestClient(app) as c:
        yield c

# Test favorite endpoints
def test_create_favorite(client, db):
    logger.info("Testing create favorite endpoint")
    response = client.post(
        "/api/favorites/",
        json={"url": "https://example.com", "title": "Example", "summary": "An example website"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com/"  # Note the trailing slash
    assert data["title"] == "Example"
    assert "id" in data
    logger.info(f"Created favorite with id: {data['id']}")

def test_read_favorite(client, db):
    logger.info("Testing read favorite endpoint")
    # First, create a favorite
    create_response = client.post(
        "/api/favorites/",
        json={"url": "https://example.com", "title": "Example", "summary": "An example website"}
    )
    favorite_id = create_response.json()["id"]
    logger.info(f"Created favorite with id: {favorite_id}")

    # Then, read the favorite
    response = client.get(f"/api/favorites/{favorite_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com/"  # Note the trailing slash
    assert data["title"] == "Example"
    logger.info("Read favorite test passed")

def test_update_favorite(client, db):
    logger.info("Testing update favorite endpoint")
    # First, create a favorite
    create_response = client.post(
        "/api/favorites/",
        json={"url": "https://example.com", "title": "Example", "summary": "An example website"}
    )
    favorite_id = create_response.json()["id"]
    logger.info(f"Created favorite with id: {favorite_id}")

    # Then, update the favorite
    response = client.put(
        f"/api/favorites/{favorite_id}",
        json={"title": "Updated Example", "summary": "An updated example website"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Example"
    assert data["summary"] == "An updated example website"
    logger.info("Update favorite test passed")

def test_delete_favorite(client, db):
    logger.info("Testing delete favorite endpoint")
    # First, create a favorite
    create_response = client.post(
        "/api/favorites/",
        json={"url": "https://example.com", "title": "Example", "summary": "An example website"}
    )
    favorite_id = create_response.json()["id"]
    logger.info(f"Created favorite with id: {favorite_id}")

    # Then, delete the favorite
    response = client.delete(f"/api/favorites/{favorite_id}")
    assert response.status_code == 200
    logger.info(f"Deleted favorite with id: {favorite_id}")

    # Verify that the favorite has been deleted
    get_response = client.get(f"/api/favorites/{favorite_id}")
    assert get_response.status_code == 404
    logger.info("Delete favorite test passed")

# Test folder endpoints
def test_create_folder(client, db):
    logger.info("Testing create folder endpoint")
    response = client.post(
        "/api/folders/",
        json={"name": "Test Folder", "description": "A test folder"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Folder"
    assert "id" in data
    logger.info(f"Created folder with id: {data['id']}")

def test_read_folder(client, db):
    logger.info("Testing read folder endpoint")
    # First, create a folder
    create_response = client.post(
        "/api/folders/",
        json={"name": "Test Folder", "description": "A test folder"}
    )
    folder_id = create_response.json()["id"]
    logger.info(f"Created folder with id: {folder_id}")

    # Then, read the folder
    response = client.get(f"/api/folders/{folder_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Folder"
    assert data["description"] == "A test folder"
    logger.info("Read folder test passed")

# Test tag endpoints
def test_create_tag(client, db):
    logger.info("Testing create tag endpoint")
    response = client.post(
        "/api/tags/",
        json={"name": "TestTag"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TestTag"
    assert "id" in data
    logger.info(f"Created tag with id: {data['id']}")

def test_read_tag(client, db):
    logger.info("Testing read tag endpoint")
    # First, create a tag
    create_response = client.post(
        "/api/tags/",
        json={"name": "UniqueTestTag"}  # Use a unique name
    )
    tag_id = create_response.json()["id"]
    logger.info(f"Created tag with id: {tag_id}")

    # Then, read the tag
    response = client.get(f"/api/tags/{tag_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "UniqueTestTag"
    logger.info("Read tag test passed")

# Test search functionality
def test_search_favorites(client, db):
    logger.info("Testing search favorites endpoint")
    # Create some favorites
    client.post("/api/favorites/", json={"url": "https://example1.com", "title": "Example 1", "summary": "First example"})
    client.post("/api/favorites/", json={"url": "https://example2.com", "title": "Example 2", "summary": "Second example"})
    logger.info("Created test favorites for search")

    # Perform a search
    response = client.post("/api/search", json={"query": "First example", "limit": 5})
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}. Response: {response.text}"
    data = response.json()
    assert len(data) > 0
    assert data[0]["title"] == "Example 1"
    logger.info("Search favorites test passed")

# Add more tests as needed for other endpoints and edge cases

if __name__ == "__main__":
    logger.info("Running tests...")
    pytest.main([__file__])
    logger.info("All tests completed.")