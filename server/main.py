import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uuid
from contextlib import asynccontextmanager
from database import engine, init_db, SessionLocal
import models
from favorites_router import router as favorites_router
from folders_router import router as folders_router
from tags_router import router as tags_router
from vector_store import vector_store
from tqdm import tqdm

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Clear the tasks table and handle unprocessed favorites
    db = SessionLocal()
    try:
        # Clear all tasks
        db.query(models.Task).delete()
        db.commit() 

        # Initialize vector store with existing favorites
        favorites = db.query(models.Favorite).all()
        vector_store.populate_from_database(favorites)
        
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

        Key features:
        * Manage favorites with automatic content summarization
        * Organize favorites into folders
        * Tag favorites for easy categorization and retrieval
        * Intelligent tag and folder suggestions based on content analysis
        * Search functionality for favorites and tags
        * Asynchronous processing for time-consuming tasks
        """,
        version="1.0.0",
        openapi_tags=[
            {
                "name": "favorites",
                "description": "Operations with favorites, including creation, retrieval, update, and deletion.",
            },
            {
                "name": "folders",
                "description": "Manage folders for organizing favorites, including creation, retrieval, update, and deletion.",
            },
            {
                "name": "tags",
                "description": "Manage tags for categorizing favorites, including creation, retrieval, update, and deletion.",
            },
        ]
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
    init_db()

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

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting the Intelligent Favorites Extension API")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, reload_includes="*.py", log_level="warning") 