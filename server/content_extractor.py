import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class ContentExtractor:
    def __init__(self, fetch_with_retries):
        self.fetch_with_retries = fetch_with_retries

    async def extract_content(self, url: str) -> tuple[str, str]:
        try:
            response = await self.fetch_with_retries(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            meta_text = self.extract_meta_information(soup)
            content = self.extract_main_content(soup) if len(meta_text.strip()) < 100 else ""

            return meta_text, content
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return "", ""

    def extract_meta_information(self, soup: BeautifulSoup) -> str:
        meta_info = {}
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            if 'name' in tag.attrs and tag.attrs['name'].lower() in ['description', 'keywords']:
                meta_info[tag.attrs['name'].lower()] = tag.attrs.get('content', '')
            elif 'property' in tag.attrs and tag.attrs['property'].lower() in ['og:title', 'og:description']:
                meta_info[tag.attrs['property'].lower()] = tag.attrs.get('content', '')

        return "\n".join([f"{key.capitalize()}: {value}" for key, value in meta_info.items() if value])

    def extract_main_content(self, soup: BeautifulSoup) -> str:
        content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        content = ' '.join([tag.get_text(strip=True) for tag in content_tags])
        content = ' '.join(content.split())  # Remove extra whitespace
        return content[:3000]  # Limit content to first 3000 characters

    @staticmethod
    def get_domain(url: str) -> str:
        return urlparse(url).netloc

    # You can add more methods here for domain-specific extraction
    # For example:
    # def extract_content_from_wikipedia(self, soup: BeautifulSoup) -> str:
    #     ...
    
    # def extract_content_from_news_site(self, soup: BeautifulSoup) -> str:
    #     ...