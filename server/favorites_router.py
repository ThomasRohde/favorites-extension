# favorites_router.py
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict
import asyncio
import uuid
from pydantic import ValidationError

from database import get_db
import schemas
from services import favorite_service, folder_service, nlp_service

router = APIRouter()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to store task statuses
task_status = {}

async def create_favorite_background(task_id: str, favorite: schemas.FavoriteCreate, db: Session):
    try:
        logger.info(f"Starting background task {task_id} for favorite creation")
        
        # Generate summary
        if not favorite.summary:
            logger.info(f"Generating summary for {favorite.url}")
            favorite.summary = await nlp_service.summarize_content(str(favorite.url))
        
        # Suggest tags based on summary
        if not favorite.tags:
            logger.info(f"Suggesting tags for {favorite.url}")
            favorite.tags = await nlp_service.suggest_tags(favorite.summary)
        
        # Suggest folder based on summary
        if not favorite.folder_id:
            logger.info(f"Suggesting folder for {favorite.url}")
            suggested_folder_id = await nlp_service.suggest_folder(db, favorite.summary)
            favorite.folder_id = suggested_folder_id
        
        logger.info(f"Creating favorite in database: {favorite}")
        created_favorite = favorite_service.create_favorite(db, favorite)
        task_status[task_id] = {"status": "completed", "favorite_id": str(created_favorite.id)}
        logger.info(f"Favorite created successfully: {created_favorite.id}")
    except IntegrityError as e:
        logger.error(f"IntegrityError in create_favorite_background: {str(e)}")
        task_status[task_id] = {"status": "failed", "error": f"IntegrityError: {str(e)}"}
    except Exception as e:
        logger.error(f"Error in create_favorite_background: {str(e)}", exc_info=True)
        task_status[task_id] = {"status": "failed", "error": str(e)}

@router.post("/", response_model=Dict[str, str])
async def create_favorite(favorite: schemas.FavoriteCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        task_id = str(uuid.uuid4())
        task_status[task_id] = {"status": "processing"}
        background_tasks.add_task(create_favorite_background, task_id, favorite, db)
        return {"task_id": task_id, "status": "processing"}
    except ValidationError as e:
        logger.error(f"Validation error: {e.json()}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}", response_model=Dict[str, str])
async def get_task_status(task_id: str):
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_status[task_id]

@router.get("/tasks", response_model=List[Dict[str, str]])
async def get_tasks():
    return [
        {
            "id": task_id,
            "title": f"Processing Favorite {task_id[:8]}",
            "status": task_info["status"],
            "progress": str(100 if task_info["status"] == "completed" else (0 if task_info["status"] == "failed" else 50))
        }
        for task_id, task_info in task_status.items()
    ]

@router.get("/{favorite_id}", response_model=schemas.Favorite)
def read_favorite(favorite_id: int, db: Session = Depends(get_db)):
    db_favorite = favorite_service.get_favorite(db, favorite_id)
    if db_favorite is None:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return db_favorite

@router.get("/", response_model=List[schemas.Favorite])
def read_favorites(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return favorite_service.get_favorites(db, skip=skip, limit=limit)

@router.put("/{favorite_id}", response_model=schemas.Favorite)
def update_favorite(favorite_id: int, favorite: schemas.FavoriteUpdate, db: Session = Depends(get_db)):
    updated_favorite = favorite_service.update_favorite(db, favorite_id, favorite)
    if updated_favorite is None:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return updated_favorite

@router.delete("/{favorite_id}", response_model=schemas.Favorite)
def delete_favorite(favorite_id: int, db: Session = Depends(get_db)):
    deleted_favorite = favorite_service.delete_favorite(db, favorite_id)
    if deleted_favorite is None:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return deleted_favorite

@router.post("/suggest-tags", response_model=List[str])
async def suggest_tags(favorite: schemas.FavoriteCreate, db: Session = Depends(get_db)):
    return await nlp_service.suggest_tags(str(favorite.url))

@router.post("/suggest-folder", response_model=int)
async def suggest_folder(favorite: schemas.FavoriteCreate, db: Session = Depends(get_db)):
    return await nlp_service.suggest_folder(db, str(favorite.url))