# favorites_router.py
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict
from pydantic import ValidationError
from rich import print as rprint
from database import get_db
import schemas
from services import favorite_service, folder_service, nlp_service
from task_queue import task_queue
from models import Task, FavoriteToProcess
from vector_store import vector_store
from fastapi.templating import Jinja2Templates
from rich import print as rprint
import builtins

builtins.print = rprint

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
    
@router.post("/", response_model=Dict[str, str])
async def create_favorite(favorite: schemas.FavoriteCreate):
    try:
        task_name = f"Create Favorite: {favorite.title}"
        result = favorite_service.create_favorite(favorite, task_name)
        return {"task_id": result["task_id"]}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}", response_model=schemas.TaskStatusDetail)
async def get_task_status(task_id: str):
    task_status = task_queue.get_task_status(task_id)
    if task_status is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return schemas.TaskStatusDetail(**task_status)

@router.get("/tasks", response_model=List[schemas.TaskStatus])
async def get_tasks(db: Session = Depends(get_db)):
    tasks = task_queue.get_all_tasks()
    
    # Check if there are any running tasks or existing restartable tasks
    running_tasks = [task for task in tasks if task["status"] == "processing"]
    restartable_tasks = [task for task in tasks if task["status"] == "restartable"]
    
    if not running_tasks and not restartable_tasks:
        # Check for unprocessed tasks in favorites_to_process
        unprocessed_count = db.query(FavoriteToProcess).filter(FavoriteToProcess.processed == False).count()
        
        if unprocessed_count > 0:
            # Create a new restartable task
            restartable_task = Task(
                id=task_queue.generate_task_id(),
                name="Restart Import Favorites",
                status="restartable",
                progress="0",
                result=f"{unprocessed_count} favorites need to be processed"
            )
            db.add(restartable_task)
            db.commit()
            
            # Add the new restartable task to the list of tasks
            tasks.append({
                "id": restartable_task.id,
                "name": restartable_task.name,
                "status": restartable_task.status,
                "progress": restartable_task.progress
            })
    
    return [schemas.TaskStatus(**task) for task in tasks]

@router.post("/restart-import", response_model=Dict[str, str])
async def restart_import():
    try:
        task_name = "Restart Import Favorites"
        result = await favorite_service.restart_import_task(task_name)
        return {"task_id": result["task_id"]}
    except Exception as e:
        logger.error(f"Unexpected error during import restart: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.delete("/", response_model=Dict[str, str])
async def delete_all_favorites():
    try:
        task_name = "Delete All Favorites"
        result = favorite_service.delete_all_favorites(task_name)
        return {"task_id": result["task_id"]}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import", response_model=Dict[str, str])
async def import_favorites(favorites: List[schemas.FavoriteImport]):
    try:
        task_name = f"Import Favorites: {len(favorites)} items"
        result = favorite_service.import_favorites(favorites, task_name)
        return {"task_id": result["task_id"]}
    except Exception as e:
        logger.error(f"Unexpected error during import: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/search/vector", response_model=List[schemas.Favorite])
async def vector_search_favorites(
    query: str = Query(..., description="The search query"),
    limit: int = Query(10, ge=1, le=100, description="The maximum number of results to return"),
    db: Session = Depends(get_db)
):
    try:
        search_results = vector_store.search_favorites(query, limit)
        favorite_ids = [result["id"] for result in search_results]
        favorites = favorite_service.get_favorites_by_ids(db, favorite_ids)
        return favorites
    except Exception as e:
        logger.error(f"Error searching favorites: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while searching favorites")


# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

@router.get("/search/html", response_class=HTMLResponse)
async def html_search_favorites(
    request: Request,
    query: str = Query(..., description="The search query"),
    limit: int = Query(10, ge=1, le=100, description="The maximum number of results to return"),
    db: Session = Depends(get_db)
):
    try:
        search_results = vector_store.search_favorites(query, limit)
        favorite_ids = [result["id"] for result in search_results]
        favorites = favorite_service.get_favorites_by_ids(db, favorite_ids)
        return templates.TemplateResponse("search_results.html", {
            "request": request,
            "favorites": favorites,
            "query": query
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while searching favorites: {str(e)}")