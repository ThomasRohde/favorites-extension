from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

# Schemas for Tag
class TagBase(BaseModel):
    name: str

class TagCreate(TagBase):
    pass

class Tag(TagBase):
    id: int

    class Config:
        orm_mode = True

# Schemas for Folder
class FolderBase(BaseModel):
    name: str
    description: Optional[str] = None

class FolderCreate(FolderBase):
    parent_id: Optional[int] = None

class Folder(FolderBase):
    id: int
    parent_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Schemas for Favorite
class FavoriteBase(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    summary: Optional[str] = None

class FavoriteCreate(FavoriteBase):
    folder_id: Optional[int] = None
    tags: Optional[List[str]] = None

class FavoriteUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    folder_id: Optional[int] = None
    tags: Optional[List[str]] = None

class Favorite(FavoriteBase):
    id: int
    folder_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    tags: List[Tag] = []

    class Config:
        from_attributes = True  # Changed from orm_mode = True

class FavoriteCreate(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    summary: Optional[str] = None
    folder_id: Optional[int] = None
    tags: Optional[List[str]] = None

# Schemas for nested relationships
class FolderWithChildren(Folder):
    children: List['FolderWithChildren'] = []
    favorites: List[Favorite] = []

    class Config:
        from_attributes = True


FolderWithChildren.update_forward_refs()