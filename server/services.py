# services.py
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
import models, schemas
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import logging
import re
from typing import Union
from task_queue import task_queue
from database import SessionLocal, engine
import asyncio
import ollama

logger = logging.getLogger(__name__)

class FavoriteService:
    async def create_favorite_task(self, task_id: str, favorite_data: dict):
        db = SessionLocal()
        try:
            favorite = schemas.FavoriteCreate(**favorite_data)
            
            task_queue._update_task(task_id, "processing", 10, None)
            # Generate summary if not provided
            if not favorite.summary:
                favorite.summary = await nlp_service.summarize_content(str(favorite.url))
            
            task_queue._update_task(task_id, "processing", 40, None)
            # Suggest tags if not provided
            if not favorite.tags:
                favorite.tags = await nlp_service.suggest_tags(favorite.summary)
            
            task_queue._update_task(task_id, "processing", 70, None)
            # Suggest folder if not provided
            if not favorite.folder_id:
                favorite.folder_id = await nlp_service.suggest_folder(db, favorite.summary)
            
            db_favorite = models.Favorite(
                url=str(favorite.url),
                title=favorite.title,
                summary=favorite.summary,
                folder_id=favorite.folder_id
            )
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
            return db_favorite.id
        except Exception as e:
            logger.error(f"Error creating favorite: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()

    def create_favorite(self, favorite: schemas.FavoriteCreate, task_name: str):
        task_id = task_queue.add_task(
            self.create_favorite_task,
            task_name,
            favorite.dict()
        )
        return {"task_id": task_id}

    def get_favorite(self, db: Session, favorite_id: int) -> Optional[models.Favorite]:
        return db.query(models.Favorite).filter(models.Favorite.id == favorite_id).first()

    def get_favorites(self, db: Session, skip: int = 0, limit: int = 100) -> List[models.Favorite]:
        return db.query(models.Favorite).offset(skip).limit(limit).all()

    def update_favorite(self, db: Session, favorite_id: int, favorite: schemas.FavoriteUpdate) -> Optional[models.Favorite]:
        db_favorite = db.query(models.Favorite).filter(models.Favorite.id == favorite_id).first()
        if db_favorite:
            update_data = favorite.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_favorite, key, value)
            db.commit()
            db.refresh(db_favorite)
        return db_favorite

    def delete_favorite(self, db: Session, favorite_id: int) -> Optional[models.Favorite]:
        db_favorite = db.query(models.Favorite).filter(models.Favorite.id == favorite_id).first()
        if db_favorite:
            db.delete(db_favorite)
            db.commit()
        return db_favorite

# Folder Service
class FolderService:
    def create_folder(self, db: Session, folder: schemas.FolderCreate) -> models.Folder:
        db_folder = models.Folder(**folder.dict())
        db.add(db_folder)
        db.commit()
        db.refresh(db_folder)
        return db_folder

    def get_folder(self, db: Session, folder_id: int) -> Optional[models.Folder]:
        return db.query(models.Folder).filter(models.Folder.id == folder_id).first()

    def get_folders(self, db: Session, skip: int = 0, limit: int = 100) -> List[models.Folder]:
        return db.query(models.Folder).filter(models.Folder.parent_id == None).options(joinedload(models.Folder.children)).offset(skip).limit(limit).all()

    def update_folder(self, db: Session, folder_id: int, folder: schemas.FolderCreate) -> Optional[models.Folder]:
        db_folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
        if db_folder:
            for key, value in folder.dict().items():
                setattr(db_folder, key, value)
            db.commit()
            db.refresh(db_folder)
        return db_folder

    def delete_folder(self, db: Session, folder_id: int, move_to_parent: bool = False) -> Optional[models.Folder]:
        db_folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
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
                "children": [build_structure(child) for child in folder.children if isinstance(child, models.Folder)]
            }

        root_folders = db.query(models.Folder).filter(models.Folder.parent_id == None).options(joinedload(models.Folder.children)).all()
        return [build_structure(folder) for folder in root_folders]

    
    def get_folder_favorites(self, db: Session, folder_id: int, skip: int = 0, limit: int = 100):
        folder = db.query(models.Folder).filter(models.Folder.id == folder_id).first()
        if folder:
            return db.query(models.Favorite).filter(models.Favorite.folder_id == folder_id).offset(skip).limit(limit).all()
        return None

# Tag Service
class TagService:
    def create_tag(self, db: Session, tag: schemas.TagCreate) -> models.Tag:
        db_tag = models.Tag(**tag.dict())
        db.add(db_tag)
        db.commit()
        db.refresh(db_tag)
        return db_tag

    def get_tag(self, db: Session, tag_id: int) -> Optional[models.Tag]:
        return db.query(models.Tag).filter(models.Tag.id == tag_id).first()

    def get_tags(self, db: Session, skip: int = 0, limit: int = 100) -> List[models.Tag]:
        return db.query(models.Tag).offset(skip).limit(limit).all()

    def update_tag(self, db: Session, tag_id: int, tag: schemas.TagCreate) -> Optional[models.Tag]:
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

    def get_tag_favorites(self, db: Session, tag_id: int, skip: int = 0, limit: int = 100) -> Optional[List[models.Favorite]]:
        tag = self.get_tag(db, tag_id)
        if tag:
            return tag.favorites[skip:skip+limit]
        return None

    async def suggest_tags(self, content: str) -> List[str]:
        return await self.nlp_service.suggest_tags(content)

    def get_popular_tags(self, db: Session, limit: int = 10) -> List[models.Tag]:
        return db.query(models.Tag).join(models.favorite_tags).group_by(models.Tag.id).order_by(func.count(models.favorite_tags.c.favorite_id).desc()).limit(limit).all()

# NLP Service
class NLPService:
    async def summarize_content(self, url: str) -> str:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract meta information
        meta_description = soup.find('meta', attrs={'name': 'description'})
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        og_description = soup.find('meta', attrs={'property': 'og:description'})

        # Combine meta information
        meta_info = ""
        if meta_description:
            meta_info += f"Description: {meta_description['content']}\n"
        if meta_keywords:
            meta_info += f"Keywords: {meta_keywords['content']}\n"
        if og_title:
            meta_info += f"Title: {og_title['content']}\n"
        if og_description:
            meta_info += f"OG Description: {og_description['content']}\n"

        # If meta information is insufficient, scrape content
        if len(meta_info.strip()) < 100:
            content = soup.get_text()
            content = ' '.join(content.split())  # Remove extra whitespace
            content = content[:3000]  # Limit content to first 3000 characters
        else:
            content = ""

        prompt = f"""You will be given information about a webpage. Your task is to create a brief summary describing the webpage and what it is about. Here is the information:

<webpage_info>
{meta_info}
{content}
</webpage_info>

Please create a summary of 2-3 sentences that describes the webpage and its main topic or purpose. Your summary should:

1. Identify the type of webpage (e.g., article, product page, blog post, etc.)
2. Explain the main subject or theme of the content
3. Highlight any key features or important information presented on the page
4. If the webpage is news or current events related, summarize the general kinds of topics covered, not any specific story

Focus on providing a concise yet informative overview that would give someone a clear idea of what they would find if they visited this webpage. Use the meta information when available, and fall back to the content when necessary. DO NOT write anything but the summary."""

        response = ollama.generate(model='phi3.5', prompt=prompt)
        return response['response']
    
    async def suggest_tags(self, summary: str) -> List[str]:
        prompt = f"""You are tasked with suggesting 3-5 relevant tags for the following summary:

<summary>
{summary}
</summary>

Your goal is to generate tags that accurately represent the main topics, themes, or key elements discussed in the summary. Follow these guidelines when selecting tags:

1. Choose tags that are concise, typically consisting of one or two words.
2. Focus on the most prominent and important concepts in the summary.
3. Avoid overly generic tags that could apply to almost any text.
4. Ensure the tags are diverse and cover different aspects of the summary.
5. If applicable, include tags related to the subject matter, industry, or field of study.

Provide your answer as a comma-separated list of tags, without any additional text or explanation. The list should contain a minimum of 3 tags and a maximum of 5 tags.

Example output format:
tag1, tag2, tag3, tag4, tag5

Remember to adjust the number of tags based on the content of the summary, ensuring you provide at least 3 and no more than 5 tags. 
IMPORTANT! Do not provide anything else that the list of tags. Do not elaborate or explain!"""

        response = ollama.generate(model='phi3.5', prompt=prompt)
        # Clean up the response: remove everything after the first newline and split by comma
        cleaned_response = response['response'].split('\n')[0]
        tags = cleaned_response.split(',')
        
        # Strip whitespace and filter out any empty tags
        return [tag.strip() for tag in tags if tag.strip()]

    def get_folder_structure(self, db: Session):
        def build_structure(folder, level=0):
            return {
                "name": folder.name,
                "id": folder.id,
                "level": level,
                "children": [build_structure(child, level + 1) for child in folder.children]
            }

        root = db.query(models.Folder).filter(models.Folder.parent_id == None).first()
        return build_structure(root)

    def format_folder_structure(self, structure, level=0):
        result = "  " * level + f"- {structure['name']} (ID: {structure['id']})\n"
        for child in structure['children']:
            result += self.format_folder_structure(child, level + 1)
        return result

    async def suggest_folder(self, db: Session, summary: str) -> int:
        folder_structure = self.get_folder_structure(db)
        formatted_structure = self.format_folder_structure(folder_structure)

        prompt = f"""You are tasked with suggesting the most appropriate folder for a webpage based on its summary and the existing folder structure. Follow these steps carefully:

1. First, you will be presented with a summary of a webpage:

<summary>
{summary}
</summary>

2. Next, you will be given the existing folder structure:

<folder_structure>
{formatted_structure}
</folder_structure>

3. Analyze the webpage summary and compare it to the themes or topics represented by the existing folders. Consider the following:
   - Does the content of the summary clearly match any of the existing folder themes?
   - Are there key words or concepts in the summary that align with folder names?
   - If no existing folder seems appropriate, what new folder name would best categorize this webpage?

4. Based on your analysis, provide your suggestion in one of these formats:
   - If an existing folder is appropriate: [number]
   - If a new folder is needed: [folder name]

5. IMPORTANT: Your response must contain ONLY the folder ID number or new folder name suggestion. Do not include any explanations, justifications, or additional text."""

        response = ollama.generate(model='phi3.5', prompt=prompt)
        suggestion = response['response'].strip()

        logger.info(f"Raw folder suggestion: {suggestion}")

        # Try to extract a folder ID or name
        folder_id_or_name = self.parse_folder_suggestion(suggestion)

        if isinstance(folder_id_or_name, int):
            # Check if the folder ID exists
            if folder_service.get_folder(db, folder_id_or_name):
                return folder_id_or_name
            else:
                logger.warning(f"Suggested folder ID {folder_id_or_name} does not exist. Creating a new folder.")
                return self.create_new_folder(db, folder_structure['id'], suggestion)
        elif isinstance(folder_id_or_name, str):
            # Create a new folder with the suggested name
            return self.create_new_folder(db, folder_structure['id'], folder_id_or_name)
        else:
            logger.warning(f"Could not parse folder suggestion: {suggestion}. Creating a new folder.")
            return self.create_new_folder(db, folder_structure['id'], "Uncategorized")

    def parse_folder_suggestion(self, suggestion: str) -> Union[int, str, None]:
        # Try to extract a folder ID
        id_match = re.search(r'\((\d+)\)|\d+', suggestion)
        if id_match:
            return int(id_match.group(1) if id_match.group(1) else id_match.group(0))

        # If no ID is found, return the suggestion as a new folder name
        return suggestion.strip()

    def create_new_folder(self, db: Session, parent_id: int, folder_name: str) -> int:
        db_folder = models.Folder(name=folder_name, parent_id=parent_id)
        db.add(db_folder)
        db.commit()
        db.refresh(db_folder)
        logger.info(f"Created new folder: {db_folder.name} (ID: {db_folder.id})")
        return db_folder.id
        
# Initialize services
favorite_service = FavoriteService()
folder_service = FolderService()
tag_service = TagService()
nlp_service = NLPService()