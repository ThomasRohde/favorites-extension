# services.py
from sqlalchemy import func, case
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
import models, schemas
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import logging
from threading import Thread
import re
from typing import Union
from task_queue import task_queue
from database import SessionLocal, engine
import asyncio
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
from urllib.parse import urlparse
from llm import llm_service
from rich import print as rprint
import builtins
import json
from jinja2 import Environment, FileSystemLoader
import os
from content_extractor import ContentExtractor
from typing import List
import math
from vector_store import vector_store

builtins.print = rprint

logger = logging.getLogger(__name__)


class FavoriteService:
    async def create_favorite_task(self, task_id: str, favorite_data: dict):
        db = SessionLocal()
        try:
            favorite = schemas.FavoriteCreate(**favorite_data)
            
            task_queue._update_task(task_id, "processing", 10, None)
            # Generate summary if not provided
            if not favorite.summary:
                favorite.summary = await nlp_service.summarize_content(str(favorite.url), favorite.metadata)
            
            task_queue._update_task(task_id, "processing", 40, None)
            # Suggest tags if not provided
            if not favorite.tags:
                favorite.tags = await nlp_service.suggest_tags(favorite.summary, favorite.metadata)
            
            task_queue._update_task(task_id, "processing", 70, None)
            # Suggest folder if not provided
            if not favorite.folder_id:
                favorite.folder_id = await nlp_service.suggest_folder(db, favorite.summary, favorite.metadata)
            
            # Prepare the favorite data
            favorite_data = {
                "url": str(favorite.url),
                "title": favorite.title,
                "summary": favorite.summary,
                "folder_id": favorite.folder_id
            }

            # Try to get existing favorite or create a new one
            db_favorite = db.query(models.Favorite).filter(models.Favorite.url == str(favorite.url)).first()
            if db_favorite:
                # Update existing favorite
                for key, value in favorite_data.items():
                    setattr(db_favorite, key, value)
            else:
                # Create new favorite
                db_favorite = models.Favorite(**favorite_data)
                db.add(db_favorite)

            db.flush()

            for tag_name in favorite.tags:
                tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
                if not tag:
                    tag = models.Tag(name=tag_name)
                    db.add(tag)
                    db.flush()
                db_favorite.tags.append(tag)

            db.commit()

            # Add or update the favorite in the vector store
            vector_store.add_favorite(db_favorite.id, db_favorite.url, db_favorite.title, db_favorite.summary)

            return db_favorite.id
        except Exception as e:
            logger.error(f"Error creating favorite: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()

    def _run_task_wrapper(self, task_id, task_func):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(task_func(task_id))
            task_queue._update_task(task_id, "completed", "100", result)
        except Exception as e:
            logger.error(f"Error in _run_task_wrapper: {str(e)}", exc_info=True)
            task_queue._update_task(task_id, "failed", "0", str(e))
        finally:
            loop.close()

    def get_favorites_by_ids(self, db: Session, favorite_ids: List[int]) -> List[models.Favorite]:
        # Create a case statement for ordering
        # Use negative index to reverse the order
        order = case(
            {id_: -index for index, id_ in enumerate(favorite_ids)},
            value=models.Favorite.id
        )
        
        # Query favorites and order them
        favorites = (db.query(models.Favorite)
                    .filter(models.Favorite.id.in_(favorite_ids))
                    .order_by(order)
                    .all())
        
        return favorites

    def create_favorite(self, favorite: schemas.FavoriteCreate, task_name: str):
        task_id = task_queue.add_task(
            self.create_favorite_task, task_name, favorite.dict()
        )
        return {"task_id": task_id}

    def get_favorite(self, db: Session, favorite_id: int) -> Optional[models.Favorite]:
        return (
            db.query(models.Favorite).filter(models.Favorite.id == favorite_id).first()
        )

    def get_favorites(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[models.Favorite]:
        return db.query(models.Favorite).offset(skip).limit(limit).all()

    def update_favorite(
        self, db: Session, favorite_id: int, favorite: schemas.FavoriteUpdate
    ) -> Optional[models.Favorite]:
        db_favorite = (
            db.query(models.Favorite).filter(models.Favorite.id == favorite_id).first()
        )
        if db_favorite:
            update_data = favorite.model_dump(exclude_unset=True)
            
            # Handle tags separately
            if 'tags' in update_data:
                new_tags = update_data.pop('tags')
                # Clear existing tags
                db_favorite.tags.clear()
                # Add new tags
                for tag_name in new_tags:
                    tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
                    if not tag:
                        tag = models.Tag(name=tag_name)
                        db.add(tag)
                    db_favorite.tags.append(tag)
            
            # Update other fields
            for key, value in update_data.items():
                setattr(db_favorite, key, value)
            
            db.commit()
            db.refresh(db_favorite)

            # Update the favorite in the vector store
            vector_store.update_favorite(db_favorite.id, db_favorite.url, db_favorite.title, db_favorite.summary)

        return db_favorite

    def delete_favorite(
        self, db: Session, favorite_id: int
    ) -> Optional[models.Favorite]:
        db_favorite = (
            db.query(models.Favorite).filter(models.Favorite.id == favorite_id).first()
        )
        if db_favorite:
            db.delete(db_favorite)
            db.commit()

            # Delete the favorite from the vector store
            vector_store.delete_favorite(favorite_id)
            
        return db_favorite

    async def delete_all_favorites_task(self, task_id: str):
        db = SessionLocal()
        try:
            task_queue._update_task(task_id, "processing", 10, None)
            
            # Delete all favorites
            db.query(models.Favorite).delete()
            db.commit()
            
            task_queue._update_task(task_id, "processing", 90, None)
            
            return "All favorites deleted successfully"
        except Exception as e:
            logger.error(f"Error deleting all favorites: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()

    def delete_all_favorites(self, task_name: str):
        task_id = task_queue.add_task(
            self.delete_all_favorites_task, task_name
        )
        return {"task_id": task_id}

    async def import_favorites_task(self, task_id: str, favorites: List[schemas.FavoriteImport]):
        db = SessionLocal()
        try:
            total_favorites = len(favorites)
            
            # Store all favorites to process
            for favorite in favorites:
                db_favorite_to_process = models.FavoriteToProcess(
                    url=str(favorite.url),
                    title=favorite.title,
                    metainfo=favorite.metadata
                )
                db.add(db_favorite_to_process)
            db.commit()

            # Process favorites
            processed_count = 0
            for favorite_to_process in db.query(models.FavoriteToProcess).filter(models.FavoriteToProcess.processed == False).all():
                try:
                    summary = await nlp_service.summarize_content(str(favorite_to_process.url), favorite_to_process.metainfo)
                    suggested_tags = await nlp_service.suggest_tags(summary, favorite_to_process.metainfo)
                    suggested_folder_id = await nlp_service.suggest_folder(db, summary, favorite_to_process.metainfo)
                    
                    db_favorite = models.Favorite(
                        url=favorite_to_process.url,
                        title=favorite_to_process.title,
                        summary=summary,
                        folder_id=suggested_folder_id
                    )
                    db.add(db_favorite)
                    db.flush()

                    for tag_name in suggested_tags:
                        tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
                        if not tag:
                            tag = models.Tag(name=tag_name)
                            db.add(tag)
                            db.flush()
                        db_favorite.tags.append(tag)

                    db.commit()

                except Exception as e:
                    logger.error(f"Error processing favorite {favorite_to_process.url}: {str(e)}")
                    db.rollback()

                finally:
                    # Delete the processed favorite from FavoriteToProcess, regardless of success or failure
                    db.delete(favorite_to_process)
                    db.commit()

                    processed_count += 1
                    progress = int((processed_count / total_favorites) * 100)
                    task_queue._update_task(task_id, "processing", str(progress), None)

                # Add a small delay between processing favorites
                await asyncio.sleep(1)

            return f"Successfully processed {processed_count} out of {total_favorites} favorites"
        except Exception as e:
            logger.error(f"Error importing favorites: {str(e)}")
            raise
        finally:
            db.close()

    def import_favorites(self, favorites: List[schemas.FavoriteImport], task_name: str):
        task_id = task_queue.add_task(
            self.import_favorites_task, task_name, favorites
        )
        return {"task_id": task_id}
    
    async def restart_import_task(self, task_name: str):
        db = SessionLocal()
        try:
            # Find the restartable task
            restartable_task = db.query(models.Task).filter(models.Task.status == "restartable").first()
            if restartable_task:
                # Update its status to processing
                restartable_task.status = "processing"
                db.commit()
                
                # Start processing remaining favorites without creating a new task
                Thread(target=self._run_task_wrapper, args=(restartable_task.id, self.process_remaining_favorites)).start()
                
                return {"task_id": restartable_task.id}
            else:
                # If no restartable task exists, create a new one (this should not happen in your scenario)
                logger.warning("No restartable task found when trying to restart import.")
                task_id = task_queue.add_task(
                    self.process_remaining_favorites, task_name
                )
                return {"task_id": task_id}
        finally:
            db.close()

    async def process_remaining_favorites(self, task_id: str):
        db = SessionLocal()
        try:
            total_favorites = db.query(models.FavoriteToProcess).filter(models.FavoriteToProcess.processed == False).count()
            processed_count = 0

            for favorite_to_process in db.query(models.FavoriteToProcess).filter(models.FavoriteToProcess.processed == False).all():
                try:
                    summary = await nlp_service.summarize_content(str(favorite_to_process.url), favorite_to_process.metadata)
                    suggested_tags = await nlp_service.suggest_tags(summary, favorite_to_process.metadata)
                    suggested_folder_id = await nlp_service.suggest_folder(db, summary, favorite_to_process.metadata)
                    
                    db_favorite = models.Favorite(
                        url=favorite_to_process.url,
                        title=favorite_to_process.title,
                        summary=summary,
                        folder_id=suggested_folder_id
                    )
                    db.add(db_favorite)
                    db.flush()

                    for tag_name in suggested_tags:
                        tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
                        if not tag:
                            tag = models.Tag(name=tag_name)
                            db.add(tag)
                            db.flush()
                        db_favorite.tags.append(tag)

                    favorite_to_process.processed = True
                    db.commit()

                    processed_count += 1
                    progress = int((processed_count / total_favorites) * 100)
                    task_queue._update_task(task_id, "processing", str(progress), None)

                except Exception as e:
                    logger.error(f"Error processing favorite {favorite_to_process.url}: {str(e)}")
                    db.rollback()

                # Add a small delay between processing favorites
                await asyncio.sleep(1)

            return f"Successfully processed {processed_count} out of {total_favorites} remaining favorites"
        except Exception as e:
            logger.error(f"Error processing remaining favorites: {str(e)}")
            raise
        finally:
            db.close()

class FolderService:
    def create_folder(self, db: Session, folder: schemas.FolderCreate) -> models.Folder:
        db_folder = models.Folder(**folder.dict())
        db.add(db_folder)
        db.commit()
        db.refresh(db_folder)
        return db_folder

    def get_folder(self, db: Session, folder_id: int) -> Optional[models.Folder]:
        return db.query(models.Folder).filter(models.Folder.id == folder_id).first()

    def get_folders(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[models.Folder]:
        return (
            db.query(models.Folder)
            .filter(models.Folder.parent_id == None)
            .options(joinedload(models.Folder.children))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_folder(
        self, db: Session, folder_id: int, folder: schemas.FolderCreate
    ) -> Optional[models.Folder]:
        db_folder = (
            db.query(models.Folder).filter(models.Folder.id == folder_id).first()
        )
        if db_folder:
            for key, value in folder.dict().items():
                setattr(db_folder, key, value)
            db.commit()
            db.refresh(db_folder)
        return db_folder

    def delete_folder(
        self, db: Session, folder_id: int, move_to_parent: bool = False
    ) -> Optional[models.Folder]:
        db_folder = (
            db.query(models.Folder).filter(models.Folder.id == folder_id).first()
        )
        if db_folder:
            if move_to_parent and db_folder.parent_id:
                for child_folder in db_folder.children:
                    child_folder.parent_id = db_folder.parent_id
                for favorite in db_folder.favorites:
                    favorite.folder_id = db_folder.parent_id
            else:
                for child_folder in db_folder.children:
                    child_folder.parent_id = None
                for favorite in db_folder.favorites:
                    favorite.folder_id = None
            db.delete(db_folder)
            db.commit()
        return db_folder

    def get_folder_structure(self, db: Session):
        def build_structure(folder):
            return {
                "id": folder.id,
                "name": folder.name,
                "parent_id": folder.parent_id,
                "description": folder.description,
                "children": [
                    build_structure(child)
                    for child in folder.children
                    if isinstance(child, models.Folder)
                ],
            }

        root_folders = (
            db.query(models.Folder)
            .filter(models.Folder.parent_id == None)
            .options(joinedload(models.Folder.children))
            .all()
        )
        return [build_structure(folder) for folder in root_folders]

    def get_folder_favorites(
        self, db: Session, folder_id: int, skip: int = 0, limit: int = 100
    ):
        folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
        if folder:
            return (
                db.query(models.Favorite)
                .filter(models.Favorite.folder_id == folder_id)
                .offset(skip)
                .limit(limit)
                .all()
            )
        return None


class TagService:
    def create_tag(self, db: Session, tag: schemas.TagCreate) -> models.Tag:
        db_tag = models.Tag(**tag.dict())
        db.add(db_tag)
        db.commit()
        db.refresh(db_tag)
        return db_tag

    def get_tag(self, db: Session, tag_id: int) -> Optional[models.Tag]:
        return db.query(models.Tag).filter(models.Tag.id == tag_id).first()

    def get_tags(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[models.Tag]:
        return db.query(models.Tag).offset(skip).limit(limit).all()

    def update_tag(
        self, db: Session, tag_id: int, tag: schemas.TagCreate
    ) -> Optional[models.Tag]:
        db_tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
        if db_tag:
            for key, value in tag.dict().items():
                setattr(db_tag, key, value)
            db.commit()
            db.refresh(db_tag)
        return db_tag

    def delete_tag(self, db: Session, tag_id: int) -> Optional[models.Tag]:
        db_tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
        if db_tag:
            db.delete(db_tag)
            db.commit()
        return db_tag

    def search_tags(self, db: Session, query: str) -> List[models.Tag]:
        return db.query(models.Tag).filter(models.Tag.name.ilike(f"%{query}%")).all()

    def get_tag_favorites(
        self, db: Session, tag_id: int, skip: int = 0, limit: int = 100
    ) -> Optional[List[models.Favorite]]:
        tag = self.get_tag(db, tag_id)
        if tag:
            return tag.favorites[skip : skip + limit]
        return None

    async def suggest_tags(self, content: str) -> List[str]:
        return await nlp_service.suggest_tags(content)

    def get_popular_tags(self, db: Session, limit: int = 10) -> List[models.Tag]:
        return (
            db.query(models.Tag)
            .join(models.favorite_tags)
            .group_by(models.Tag.id)
            .order_by(func.count(models.favorite_tags.c.favorite_id).desc())
            .limit(limit)
            .all()
        )
    
    def get_favorites_by_fuzzy_tag(self, db: Session, tag_query: str, skip: int = 0, limit: int = 100) -> List[models.Favorite]:
        # Convert the query to lowercase and surround with wildcards
        fuzzy_query = f"%{tag_query.lower()}%"
        return (db.query(models.Favorite)
                  .join(models.favorite_tags)
                  .join(models.Tag)
                  .filter(func.lower(models.Tag.name).like(fuzzy_query))
                  .offset(skip)
                  .limit(limit)
                  .all())

class NLPService:
    def __init__(self):
        self.session = requests.Session()
        retries = Retry(
            total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

        # Initialize ContentExtractor
        self.content_extractor = ContentExtractor(self.fetch_with_retries)

    def get_random_user_agent(self):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
        ]
        return random.choice(user_agents)

    async def fetch_with_retries(self, url, max_retries=3):
        for attempt in range(max_retries):
            headers = {
                "User-Agent": self.get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            try:
                await asyncio.sleep(random.uniform(1, 3))  # Random delay
                response = await asyncio.to_thread(
                    self.session.get, url, headers=headers, timeout=15
                )
                response.raise_for_status()
                return response
            except requests.HTTPError as e:
                if e.response.status_code == 403:
                    logger.warning(
                        f"403 Forbidden encountered on attempt {attempt + 1}. Retrying..."
                    )
                    if attempt == max_retries - 1:
                        logger.error(
                            f"Max retries reached for URL {url}. Unable to fetch content."
                        )
                        raise
                else:
                    raise
            except requests.RequestException as e:
                logger.error(
                    f"Error fetching URL {url} on attempt {attempt + 1}: {str(e)}"
                )
                if attempt == max_retries - 1:
                    raise

    def generate_fallback_description(self, url: str, metadata: str) -> str:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path

        template = self.jinja_env.get_template("generate_fallback_description.j2")
        prompt = template.render(url=url, metadata=metadata)

        return llm_service.generate(prompt)

    async def summarize_content(self, url: str, metadata: str) -> str:
        try:
            content = await self.content_extractor.extract_content(url)

            template = self.jinja_env.get_template("summarize_content.j2")
            prompt = template.render(metadata=metadata, content=content)

            return llm_service.generate(prompt)

        except requests.RequestException as e:
            logger.error(f"Error fetching URL {url}: {str(e)}")
            return self.generate_fallback_description(url, metadata)
        except Exception as e:
            logger.error(f"Unexpected error while summarizing content for {url}: {str(e)}")
            raise

    async def suggest_tags(self, summary: str, metadata: str) -> List[str]:
        try:
            template = self.jinja_env.get_template("suggest_tags.j2")
            prompt = template.render(summary=summary, metadata=metadata)

            response = llm_service.generate(prompt)
            cleaned_response = response.split("\n")[0]
            tags = cleaned_response.split(",")

            formatted_tags = []
            for tag in tags:
                tag = tag.strip()
                if tag:
                    tag = tag.replace("-", " ").replace("_", " ")
                    if tag[0].isalpha():
                        tag = tag[0].upper() + tag[1:]
                    formatted_tags.append(tag)

            return formatted_tags

        except Exception as e:
            logger.error(f"Unexpected error while suggesting tags: {str(e)}")
            raise

    def get_folder_structure(self, db: Session):
        def build_structure(folder, level=0):
            return {
                "name": folder.name,
                "id": folder.id,
                "level": level,
                "children": [
                    build_structure(child, level + 1) for child in folder.children
                ],
            }

        root = db.query(models.Folder).filter(models.Folder.parent_id == None).first()
        return build_structure(root)

    def format_folder_structure(self, structure, level=0):
        result = "  " * level + f"- {structure['name']} (ID: {structure['id']})\n"
        for child in structure["children"]:
            result += self.format_folder_structure(child, level + 1)
        return result

    async def suggest_folder(self, db: Session, summary: str, metadata: str) -> int:
        try:
            folder_structure = self.get_folder_structure(db)
            formatted_structure = self.format_folder_structure(folder_structure)

            template = self.jinja_env.get_template("suggest_folder.j2")
            prompt = template.render(
                summary=summary, metadata=metadata, formatted_structure=formatted_structure
            )

            suggestion = llm_service.generate(prompt)
            suggestion_json = json.loads(suggestion)

            parent_folder_id = suggestion_json.get("id")
            suggested_folder = suggestion_json["children"][0]

            parent_folder = db.query(models.Folder).filter(models.Folder.id == parent_folder_id).first()
            if not parent_folder:
                logger.warning(f"Suggested parent folder ID {parent_folder_id} does not exist. Using root folder.")
                parent_folder_id = folder_structure["id"]

            if "id" in suggested_folder:
                existing_folder = db.query(models.Folder).filter(models.Folder.id == suggested_folder["id"]).first()
                if existing_folder:
                    return existing_folder.id
                else:
                    logger.warning(f"Suggested folder ID {suggested_folder['id']} does not exist. Creating a new folder.")

            return self.create_new_folder(db, parent_folder_id, suggested_folder["name"])

        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON: {suggestion}")
            return self.get_or_create_uncategorized_folder(db)
        except Exception as e:
            logger.error(f"Unexpected error while suggesting folder: {str(e)}")
            return self.get_or_create_uncategorized_folder(db)


    def create_new_folder(self, db: Session, parent_id: int, folder_name: str) -> int:
        try:
            db_folder = models.Folder(name=folder_name, parent_id=parent_id)
            db.add(db_folder)
            db.commit()
            db.refresh(db_folder)
            logger.info(f"Created new folder: {db_folder.name} (ID: {db_folder.id})")
            return db_folder.id
        except Exception as e:
            logger.error(f"Error creating new folder: {str(e)}")
            db.rollback()
            return self.get_or_create_uncategorized_folder(db)

    def get_or_create_uncategorized_folder(self, db: Session) -> int:
        try:
            uncategorized = (
                db.query(models.Folder)
                .filter(models.Folder.name == "Uncategorized")
                .first()
            )
            if not uncategorized:
                uncategorized = models.Folder(name="Uncategorized", parent_id=None)
                db.add(uncategorized)
                db.commit()
                db.refresh(uncategorized)
                logger.info(f"Created Uncategorized folder (ID: {uncategorized.id})")
            return uncategorized.id
        except Exception as e:
            logger.error(f"Error getting or creating Uncategorized folder: {str(e)}")
            db.rollback()
            # If all else fails, return None or a default folder ID
            return None  # or return a default folder ID if you have one


# Initialize services
favorite_service = FavoriteService()
folder_service = FolderService()
tag_service = TagService()
nlp_service = NLPService()
