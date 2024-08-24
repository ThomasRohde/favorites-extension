import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, init_db
import models
from favorites_router import router as favorites_router
from folders_router import router as folders_router
from tags_router import router as tags_router
from web_router import router as web_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    application = FastAPI(
        title="Intelligent Favorites Extension API",
        description="An API for managing intelligent favorites with automatic summarization and tagging.",
        version="1.0.0",
        openapi_tags=[
            {
                "name": "favorites",
                "description": "Operations with favorites",
            },
            {
                "name": "folders",
                "description": "Manage folders for organizing favorites",
            },
            {
                "name": "tags",
                "description": "Manage tags for categorizing favorites",
            },
        ],
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

    # Mount static files
    application.mount("/static", StaticFiles(directory="static"), name="static")

    # Include routers
    application.include_router(favorites_router, prefix="/api/favorites", tags=["favorites"])
    application.include_router(folders_router, prefix="/api/folders", tags=["folders"])
    application.include_router(tags_router, prefix="/api/tags", tags=["tags"])
    application.include_router(web_router, tags=["web"])

    return application

app = create_application()

@app.get("/", tags=["root"])
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Intelligent Favorites Extension API"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting the Intelligent Favorites Extension API")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)