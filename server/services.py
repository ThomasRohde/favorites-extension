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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry  # Updated import statement
import random
from urllib.parse import urlparse
from llm import llm_service
from rich import print as rprint
import builtins
import json

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
                "parent_id": folder.parent_id,
                "description": folder.description, 
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
    def __init__(self):
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def get_random_user_agent(self):
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
        ]
        return random.choice(user_agents)

    async def fetch_with_retries(self, url, max_retries=3):
        for attempt in range(max_retries):
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
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
                    logger.warning(f"403 Forbidden encountered on attempt {attempt + 1}. Retrying...")
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries reached for URL {url}. Unable to fetch content.")
                        raise
                else:
                    raise
            except requests.RequestException as e:
                logger.error(f"Error fetching URL {url} on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise

    def generate_fallback_description(self, url: str) -> str:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path

        prompt = f"""Generate a brief, general description for a webpage based only on its URL. The URL is:

{url}

Your description should:
1. Identify the likely type of website (e.g., company website, blog, news site, etc.) based on the domain name.
2. Suggest possible content or purpose of the specific page based on the URL path.
3. Use neutral language and avoid making definitive claims about the content.

Limit your response to 2-3 sentences."""

        return llm_service.generate(prompt)

    async def summarize_content(self, url: str) -> str:
        try:
            response = await self.fetch_with_retries(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract meta information
            meta_info = {}
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                if 'name' in tag.attrs and tag.attrs['name'].lower() in ['description', 'keywords']:
                    meta_info[tag.attrs['name'].lower()] = tag.attrs.get('content', '')
                elif 'property' in tag.attrs and tag.attrs['property'].lower() in ['og:title', 'og:description']:
                    meta_info[tag.attrs['property'].lower()] = tag.attrs.get('content', '')

            # Combine meta information
            meta_text = "\n".join([f"{key.capitalize()}: {value}" for key, value in meta_info.items() if value])

            # If meta information is insufficient, scrape content
            if len(meta_text.strip()) < 100:
                # Extract text from specific tags
                content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                content = ' '.join([tag.get_text(strip=True) for tag in content_tags])
                content = ' '.join(content.split())  # Remove extra whitespace
                content = content[:3000]  # Limit content to first 3000 characters
            else:
                content = ""

            prompt = f"""You will be given information about a webpage. Your task is to create a brief summary describing the webpage and what it is about. Here is the information:

<webpage_info>
{meta_text}
{content}
</webpage_info>

Please create a summary of 2-3 sentences that describes the webpage and its main topic or purpose. Your summary should:

1. Identify the type of webpage (e.g., article, product page, blog post, etc.)
2. Explain the main subject or theme of the content
3. Highlight any key features or important information presented on the page
4. If the webpage is news or current events related, summarize the general kinds of topics covered, not any specific story
5. Be assertive about the contents of the web page, do not use language like 'appears to be', or 'is likely'.

Focus on providing a concise yet informative overview that would give someone a clear idea of what they would find if they visited this webpage. Use the meta information when available, and fall back to the content when necessary. DO NOT write anything but the summary."""

            return llm_service.generate(prompt)

        except requests.RequestException as e:
            logger.error(f"Error fetching URL {url}: {str(e)}")
            return self.generate_fallback_description(url)

    
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

        response = llm_service.generate(prompt)
        # Clean up the response: remove everything after the first newline and split by comma
        cleaned_response = response.split('\n')[0]
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
    - If no existing folder seems appropriate, suggest a new folder name that would best categorize this webpage.

    4. Based on your analysis, provide your suggestion in a JSON structure with the following format:
    {{
        "name": "Parent Folder Name",
        "id": parent_folder_id,
        "children": [
        {{
            "name": "Suggested Folder Name",
            "id": suggested_folder_id  // Optional, include only if suggesting an existing folder
        }}
        ]
    }}

    Examples:
    1. Suggesting an existing folder:
    {{
        "name": "Development",
        "id": 2,
        "children": [
        {{
            "name": "Python",
            "id": 5
        }}
        ]
    }}

    2. Suggesting a new folder:
    {{
        "name": "Technology",
        "id": 3,
        "children": [
        {{
            "name": "Artificial Intelligence"
        }}
        ]
    }}

    5. IMPORTANT: Your response must contain ONLY the JSON structure. Do not include any explanations, justifications, or additional text."""

        try:
            suggestion = llm_service.generate(prompt)
            suggestion_json = json.loads(suggestion)
            print(suggestion_json)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON: {suggestion}")
            return self.get_or_create_uncategorized_folder(db)
        except Exception as e:
            logger.error(f"Error generating folder suggestion: {str(e)}")
            return self.get_or_create_uncategorized_folder(db)

        try:
            parent_folder_id = suggestion_json.get('id')
            suggested_folder = suggestion_json['children'][0]

            # Check if parent folder exists
            parent_folder = folder_service.get_folder(db, parent_folder_id)
            if not parent_folder:
                logger.warning(f"Suggested parent folder ID {parent_folder_id} does not exist. Using root folder.")
                parent_folder_id = folder_structure['id']  # Use root folder id

            if 'id' in suggested_folder:
                # Check if the suggested folder exists
                existing_folder = folder_service.get_folder(db, suggested_folder['id'])
                if existing_folder:
                    return existing_folder.id
                else:
                    logger.warning(f"Suggested folder ID {suggested_folder['id']} does not exist. Creating a new folder.")

            # Create a new folder
            return self.create_new_folder(db, parent_folder_id, suggested_folder['name'])

        except KeyError as e:
            logger.error(f"Invalid JSON structure in LLM response: {str(e)}")
            return self.get_or_create_uncategorized_folder(db)
        except Exception as e:
            logger.error(f"Error processing folder suggestion: {str(e)}")
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
            uncategorized = db.query(models.Folder).filter(models.Folder.name == "Uncategorized").first()
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