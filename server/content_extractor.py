from urllib.parse import urlparse
from bs4 import BeautifulSoup

class ContentExtractor:
    def __init__(self, fetch_function):
        self.fetch = fetch_function

    async def extract_content(self, url):
        parsed_url = urlparse(url)
        
        # Special handling for YouTube channels
        if self.is_youtube_channel(parsed_url):
            return self.extract_youtube_channel_info(parsed_url)
        
        # For all other URLs, including YouTube videos and playlists
        response = await self.fetch(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        meta_info = self.extract_meta_information(soup)
        
        if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
            url_type = self.classify_youtube_url(parsed_url)
            return self.format_youtube_content(url_type, meta_info)
        else:
            return self.format_generic_content(meta_info)

    def is_youtube_channel(self, parsed_url):
        return ('youtube.com' in parsed_url.netloc and 
                (parsed_url.path.startswith('/@') or '/channel/' in parsed_url.path or '/c/' in parsed_url.path))

    def extract_youtube_channel_info(self, parsed_url):
        channel_name = parsed_url.path.split('/')[-1]
        if channel_name.startswith('@'):
            channel_name = channel_name[1:]  # Remove the '@' symbol
        
        meta_text = f"Type: YouTube Channel\n"
        meta_text += f"Channel Name: {channel_name}\n"
        meta_text += f"URL: {parsed_url.geturl()}\n"
        
        content = f"YouTube channel for {channel_name}"
        
        return meta_text, content

    def classify_youtube_url(self, parsed_url):
        if 'watch' in parsed_url.path:
            return 'video'
        elif 'playlist' in parsed_url.path:
            return 'playlist'
        else:
            return 'unknown'

    def extract_meta_information(self, soup):
        meta_info = {}

        # Extracting title
        if soup.title:
            meta_info['title'] = soup.title.string

        # Extracting meta tags
        for meta in soup.find_all('meta'):
            if 'name' in meta.attrs:
                name = meta.attrs['name'].lower()
                if name in ['description', 'keywords']:
                    meta_info[name] = meta.attrs['content']
            elif 'property' in meta.attrs:
                property_name = meta.attrs['property'].lower()
                if property_name in ['og:title', 'og:description', 'og:image', 'og:url', 'og:type']:
                    meta_info[property_name] = meta.attrs['content']

        # Extracting tags (keywords)
        if 'keywords' in meta_info:
            meta_info['tags'] = [tag.strip() for tag in meta_info['keywords'].split(',')]

        return meta_info

    def format_youtube_content(self, url_type, meta_info):
        meta_text = f"Type: YouTube {url_type.capitalize()}\n"
        meta_text += f"Title: {meta_info.get('og:title', meta_info.get('title', 'Unknown'))}\n"
        meta_text += f"Description: {meta_info.get('og:description', meta_info.get('description', 'No description found'))}\n"
        meta_text += f"URL: {meta_info.get('og:url', 'Unknown URL')}\n"
        
        if 'og:image' in meta_info:
            meta_text += f"Thumbnail: {meta_info['og:image']}\n"
        
        if 'tags' in meta_info:
            meta_text += f"Tags: {', '.join(meta_info['tags'])}\n"

        content = meta_info.get('og:description', meta_info.get('description', 'No content found'))

        return meta_text, content

    def format_generic_content(self, meta_info):
        meta_text = f"Title: {meta_info.get('og:title', meta_info.get('title', 'Unknown'))}\n"
        meta_text += f"Description: {meta_info.get('og:description', meta_info.get('description', 'No description found'))}\n"
        
        if 'og:url' in meta_info:
            meta_text += f"URL: {meta_info['og:url']}\n"
        
        if 'og:image' in meta_info:
            meta_text += f"Image: {meta_info['og:image']}\n"
        
        if 'og:type' in meta_info:
            meta_text += f"Type: {meta_info['og:type']}\n"
        
        if 'tags' in meta_info:
            meta_text += f"Tags: {', '.join(meta_info['tags'])}\n"

        content = meta_info.get('og:description', meta_info.get('description', 'No content found'))

        return meta_text, content