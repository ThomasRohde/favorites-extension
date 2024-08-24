# folders_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import schemas
from services import folder_service

router = APIRouter()

@router.post("/", response_model=schemas.Folder)
def create_folder(folder: schemas.FolderCreate, db: Session = Depends(get_db)):
    return folder_service.create_folder(db, folder)

@router.get("/{folder_id}", response_model=schemas.FolderWithChildren)
def read_folder(folder_id: int, db: Session = Depends(get_db)):
    db_folder = folder_service.get_folder(db, folder_id)
    if db_folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return db_folder

@router.get("/", response_model=List[schemas.FolderWithChildren])
def read_folders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return folder_service.get_folders(db, skip=skip, limit=limit)

@router.put("/{folder_id}", response_model=schemas.Folder)
def update_folder(folder_id: int, folder: schemas.FolderCreate, db: Session = Depends(get_db)):
    updated_folder = folder_service.update_folder(db, folder_id, folder)
    if updated_folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return updated_folder

@router.delete("/{folder_id}", response_model=schemas.Folder)
def delete_folder(folder_id: int, move_to_parent: bool = False, db: Session = Depends(get_db)):
    deleted_folder = folder_service.delete_folder(db, folder_id, move_to_parent)
    if deleted_folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return deleted_folder

@router.get("/structure", response_model=schemas.FolderWithChildren)
def get_folder_structure(db: Session = Depends(get_db)):
    return folder_service.get_folder_structure(db)

@router.post("/{folder_id}/move", response_model=schemas.Folder)
def move_folder(folder_id: int, new_parent_id: int, db: Session = Depends(get_db)):
    moved_folder = folder_service.move_folder(db, folder_id, new_parent_id)
    if moved_folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return moved_folder

@router.get("/{folder_id}/favorites", response_model=List[schemas.Favorite])
def get_folder_favorites(folder_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    favorites = folder_service.get_folder_favorites(db, folder_id, skip, limit)
    if favorites is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    return favorites