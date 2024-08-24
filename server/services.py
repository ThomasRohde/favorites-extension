# services.py
from sqlalchemy import func
from sqlalchemy.orm import Session
import models, schemas
from typing import List, Optional
import chromadb
from chromadb.config import Settings
import ollama
import requests
from bs4 import BeautifulSoup
import logging


logger = logging.getLogger(__name__)

class FavoriteService:
    def create_favorite(self, db: Session, favorite: schemas.FavoriteCreate) -> models.Favorite:
        logger.info(f"Creating favorite: {favorite}")
        db_favorite = models.Favorite(
            url=str(favorite.url),
            title=favorite.title,
            summary=favorite.summary,
            folder_id=favorite.folder_id
        )
        db.add(db_favorite)
        db.commit()
        db.refresh(db_favorite)

        # Add tags
        if favorite.tags:
            for tag_name in favorite.tags:
                try:
                    tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
                    if not tag:
                        logger.info(f"Creating new tag: {tag_name}")
                        tag = models.Tag(name=tag_name)
                        db.add(tag)
                        db.commit()
                    db_favorite.tags.append(tag)
                except Exception as e:
                    logger.error(f"Error adding tag {tag_name}: {str(e)}", exc_info=True)
            db.commit()

        logger.info(f"Favorite created successfully: {db_favorite.id}")
        return db_favorite

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

            # Update ChromaDB
            collection.update(
                documents=[db_favorite.summary or ""],
                metadatas=[{"url": db_favorite.url, "title": db_favorite.title}],
                ids=[str(db_favorite.id)]
            )

        return db_favorite

    def delete_favorite(self, db: Session, favorite_id: int) -> Optional[models.Favorite]:
        db_favorite = db.query(models.Favorite).filter(models.Favorite.id == favorite_id).first()
        if db_favorite:
            db.delete(db_favorite)
            db.commit()

            # Delete from ChromaDB
            collection.delete(ids=[str(favorite_id)])

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
        return db.query(models.Folder).offset(skip).limit(limit).all()

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

    def get_folder_structure(self, db: Session) -> models.Folder:
        return db.query(models.Folder).filter(models.Folder.parent_id == None).first()

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
        # Fetch the content
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        content = soup.get_text()

        # Use Ollama to summarize
        prompt = f"""You will be given the content of a webpage. Your task is to create a brief summary describing the webpage and what it is about. Here is the webpage content:

<webpage_content>
{content}
</webpage_content>

Please create a summary of 2-3 sentences that describes the webpage and its main topic or purpose. Your summary should:

1. Identify the type of webpage (e.g., article, product page, blog post, etc.)
2. Explain the main subject or theme of the content
3. Highlight any key features or important information presented on the page
4. If the webpage is part of an aggregation site, with many different pages, and the site has decoration around the page content, e.g., GitHub, do not include the parent content in the summary

Focus on providing a concise yet informative overview that would give someone a clear idea of what they would find if they visited this webpage. DO NOT write anything but the summary."""
        
        response = ollama.generate(model='phi3.5', prompt=prompt)
        return response['response']

    async def suggest_tags(self, url: str) -> List[str]:
        # Fetch and summarize content
        summary = await self.summarize_content(url)

        # Use Ollama to suggest tags
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

Remember to adjust the number of tags based on the content of the summary, ensuring you provide at least 3 and no more than 5 tags."""
        
        response = ollama.generate(model='phi3.5', prompt=prompt)
        tags = response['response'].split(',')
        return [tag.strip() for tag in tags]

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

    async def suggest_folder(self, db: Session, url: str) -> int:
        # Fetch and summarize content
        summary = await self.summarize_content(url)

        # Get the complete folder structure
        folder_structure = self.get_folder_structure(db)
        formatted_structure = self.format_folder_structure(folder_structure)

        # Use Ollama to suggest a folder
        prompt = f"""You are tasked with suggesting the most appropriate folder for a webpage based on its summary and the existing folder structure. Follow these steps carefully:

1. First, you will be presented with a summary of a webpage:

<summary>
{summary}
</summary>

2. Next, you will be given the existing folder structure:

<folder_structure>
{folder_structure}
</folder_structure>

3. Analyze the webpage summary and compare it to the themes or topics represented by the existing folders. Consider the following:
   - Does the content of the summary clearly match any of the existing folder themes?
   - Are there key words or concepts in the summary that align with folder names?
   - If no existing folder seems appropriate, what new folder name would best categorize this webpage?

4. Based on your analysis, provide your suggestion in one of these two formats:
   - If an existing folder is appropriate: ID: [number]
   - If a new folder is needed: NEW: [folder name]

5. IMPORTANT: Your response must contain ONLY the folder ID or NEW suggestion. Do not include any explanations, justifications, or additional text.

Remember, your goal is to provide the most accurate categorization for the webpage based on its summary and the existing folder structure. Be concise and precise in your output."""

        response = ollama.generate(model='phi3.5', prompt=prompt)
        suggestion = response['response'].strip()

        if suggestion.startswith("NEW:"):
            # Create a new folder
            new_folder_name = suggestion.split(":", 1)[1].strip()
            db_folder = models.Folder(name=new_folder_name, parent_id=folder_structure['id'])  # Set parent as root
            db.add(db_folder)
            db.commit()
            db.refresh(db_folder)
            return db_folder.id
        else:
            # Return the suggested folder ID
            try:
                return int(suggestion.split(":", 1)[1].strip())
            except ValueError:
                # If the LLM didn't return a valid ID, default to the root folder
                return folder_structure['id']

# Initialize services
favorite_service = FavoriteService()
folder_service = FolderService()
tag_service = TagService()
nlp_service = NLPService()