import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, init_db
import models
from favorites_router import router as favorites_router
from folders_router import router as folders_router
from tags_router import router as tags_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize database
init_db()

# Include routers
app.include_router(favorites_router, prefix="/api/favorites", tags=["favorites"])
app.include_router(folders_router, prefix="/api/folders", tags=["folders"])
app.include_router(tags_router, prefix="/api/tags", tags=["tags"])

@app.get("/", tags=["root"])
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Intelligent Favorites Extension API"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting the Intelligent Favorites Extension API")
    uvicorn.run(app, host="127.0.0.1", port=8000)