from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from sqlalchemy.sql import func
from database import Base

# Association table for many-to-many relationship between Favorite and Tag
favorite_tags = Table('favorite_tags', Base.metadata,
    Column('favorite_id', Integer, ForeignKey('favorites.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class Folder(Base):
    __tablename__ = 'folders'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey('folders.id'))
    description = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    parent = relationship('Folder', remote_side=[id], back_populates='children')
    children = relationship('Folder', back_populates='parent')
    favorites = relationship('Favorite', back_populates='folder')

class Favorite(Base):
    __tablename__ = 'favorites'

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    title = Column(String)
    summary = Column(Text)
    folder_id = Column(Integer, ForeignKey('folders.id'))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    folder = relationship('Folder', back_populates='favorites')
    tags = relationship('Tag', secondary=favorite_tags, back_populates='favorites')

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    favorites = relationship('Favorite', secondary=favorite_tags, back_populates='tags')

class FavoriteToProcess(Base):
    __tablename__ = 'favorites_to_process'

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    title = Column(String)
    metainfo = Column(String)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    progress = Column(String, nullable=False)
    result = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))