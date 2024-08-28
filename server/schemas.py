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
    metadata: Optional[str] = None  # Include metadata for creation, but don't persist it

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
        orm_mode = True

# Schemas for nested relationships
class FolderWithChildren(Folder):
    children: List['FolderWithChildren'] = []
    favorites: List[Favorite] = []

    class Config:
        orm_mode = True

class TaskStatus(BaseModel):
    id: str
    name: str
    status: str
    progress: str

class TaskStatusDetail(TaskStatus):
    result: Optional[str] = None

class TaskCreate(BaseModel):
    name: str

class FavoriteImport(BaseModel):
    url: HttpUrl
    title: str
    metadata: Optional[str] = None

FolderWithChildren.model_rebuild()