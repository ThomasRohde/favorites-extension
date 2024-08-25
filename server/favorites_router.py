# favorites_router.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict
from pydantic import ValidationError

from database import get_db
import schemas
from services import favorite_service, folder_service, nlp_service
from task_queue import task_queue

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/", response_model=Dict[str, str])
async def create_favorite(favorite: schemas.FavoriteCreate):
    try:
        result = favorite_service.create_favorite(favorite)
        return {"task_id": result["task_id"]}
    except ValidationError as e:
        logger.error(f"Validation error: {e.json()}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}", response_model=Dict[str, str])
async def get_task_status(task_id: str):
    task_status = task_queue.get_task_status(task_id)
    if task_status is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_status

@router.get("/tasks", response_model=List[Dict[str, str]])
async def get_tasks():
    return task_queue.get_all_tasks()

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