import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from database import Base, engine, SessionLocal
import models
from favorites_router import router as favorites_router
from folders_router import router as folders_router
from tags_router import router as tags_router
from vector_store import vector_store
import os
import json
import schemas
from services import favorite_service
from task_queue import task_queue

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_tables():
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    tables_to_keep = []  # We're not keeping any tables now, as favorites_embeddings is not in SQLite

    with SessionLocal() as session:
        for table in all_tables:
            if table not in tables_to_keep:
                session.execute(text(f"DELETE FROM {table}"))
                logger.info(f"Cleared table: {table}")
        session.commit()

    logger.info("Cleared all non-embedding tables.")
    Base.metadata.create_all(engine)
    logger.info("Ensured all tables exist.")

def create_folder(session, name, parent=None, description=None):
    folder = models.Folder(name=name, description=description)
    if parent:
        folder.parent = parent
    session.add(folder)
    session.flush()
    return folder

def create_folder_structure(session, structure, parent=None):
    folder = create_folder(session, structure['name'], parent, structure.get('description'))
    for child in structure.get('children', []):
        create_folder_structure(session, child, folder)

def check_running_tasks():
    tasks = task_queue.get_all_tasks()
    running_tasks = [task for task in tasks if task["status"] == "processing"]
    return len(running_tasks) > 0

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Clear the tasks table and handle unprocessed favorites
    db = SessionLocal()
    try:
        # Clear all tasks
        db.query(models.Task).delete()
        db.commit() 
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        db.rollback()
    finally:
        db.close()
    
    yield  # This is where the app runs
    
    # Shutdown: Add any cleanup code here if needed
    pass

def create_application() -> FastAPI:
    application = FastAPI(
        lifespan=lifespan,
        title="Intelligent Favorites Extension API",
        description="""
        This API provides endpoints for managing an intelligent favorites system. 
        It allows users to create, retrieve, update, and delete favorites, folders, and tags. 
        The system also provides intelligent features such as automatic summarization, 
        tag suggestion, and folder recommendation.
        """,
        version="1.0.0",
    )

    # Set up CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )

    # Initialize database
    Base.metadata.create_all(bind=engine)

    # Include routers
    application.include_router(favorites_router, prefix="/api/favorites", tags=["favorites"])
    application.include_router(folders_router, prefix="/api/folders", tags=["folders"])
    application.include_router(tags_router, prefix="/api/tags", tags=["tags"])

    return application

app = create_application()

@app.get("/", tags=["root"])
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Intelligent Favorites Extension API"}

@app.post("/api/reset/", tags=["root"])
async def reset_database():
    if check_running_tasks():
        raise HTTPException(status_code=409, detail="Cannot reset database while tasks are running")
    
    try:
        clear_tables()
        
        # Recreate initial folder structure
        with SessionLocal() as session:
            with open('folder_structure.json', 'r') as f:
                folder_structure = json.load(f)
            create_folder_structure(session, folder_structure)
            session.commit()
        
        return {"message": "Database reset successful"}
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise HTTPException(status_code=500, detail="Error resetting database")

@app.post("/api/reindex/", tags=["root"])
async def reindex_database(db: Session = Depends(SessionLocal)):
    if check_running_tasks():
        raise HTTPException(status_code=409, detail="Cannot reindex database while tasks are running")
    
    try:
        # Get all existing favorites
        existing_favorites = db.query(models.Favorite).all()
        
        # Clear and recreate tables
        clear_tables()
        
        # Recreate initial folder structure
        with open('folder_structure.json', 'r') as f:
            folder_structure = json.load(f)
        create_folder_structure(db, folder_structure)
        db.commit()
        
        # Prepare favorites for reindexing
        favorites_to_import = []
        for favorite in existing_favorites:
            metadata = {
                "summary": favorite.summary,
                "tags": [tag.name for tag in favorite.tags]
            }
            favorite_data = schemas.FavoriteImport(
                url=favorite.url,
                title=favorite.title,
                metadata=json.dumps(metadata)
            )
            favorites_to_import.append(favorite_data)
        
        # Use import_favorites function to reindex
        task_name = f"Reindex Favorites: {len(favorites_to_import)} items"
        result = favorite_service.import_favorites(favorites_to_import, task_name)
        
        return {"message": f"Database reindexing started with {len(favorites_to_import)} favorites", "task_id": result["task_id"]}
    except Exception as e:
        logger.error(f"Error reindexing database: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reindexing database")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting the Intelligent Favorites Extension API")
    chroma_db_path = os.path.abspath("chroma_db")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        # reload=False,
        # reload_includes="*.py",
        # reload_excludes=[chroma_db_path],
        log_level="info"
    )