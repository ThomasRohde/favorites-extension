# tags_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import schemas
from services import tag_service

router = APIRouter()

@router.post("/", response_model=schemas.Tag)
def create_tag(tag: schemas.TagCreate, db: Session = Depends(get_db)):
    return tag_service.create_tag(db, tag)

@router.get("/{tag_id}", response_model=schemas.Tag)
def read_tag(tag_id: int, db: Session = Depends(get_db)):
    db_tag = tag_service.get_tag(db, tag_id)
    if db_tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return db_tag

@router.get("/", response_model=List[schemas.Tag])
def read_tags(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return tag_service.get_tags(db, skip=skip, limit=limit)

@router.put("/{tag_id}", response_model=schemas.Tag)
def update_tag(tag_id: int, tag: schemas.TagCreate, db: Session = Depends(get_db)):
    updated_tag = tag_service.update_tag(db, tag_id, tag)
    if updated_tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return updated_tag

@router.delete("/{tag_id}", response_model=schemas.Tag)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    deleted_tag = tag_service.delete_tag(db, tag_id)
    if deleted_tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return deleted_tag

@router.get("/search/{query}", response_model=List[schemas.Tag])
def search_tags(query: str, db: Session = Depends(get_db)):
    return tag_service.search_tags(db, query)

@router.get("/{tag_id}/favorites", response_model=List[schemas.Favorite])
def get_tag_favorites(tag_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    favorites = tag_service.get_tag_favorites(db, tag_id, skip, limit)
    if favorites is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return favorites

@router.post("/suggest", response_model=List[str])
async def suggest_tags(content: str, db: Session = Depends(get_db)):
    return await tag_service.suggest_tags(content)

@router.get("/popular", response_model=List[schemas.Tag])
def get_popular_tags(limit: int = 10, db: Session = Depends(get_db)):
    return tag_service.get_popular_tags(db, limit)