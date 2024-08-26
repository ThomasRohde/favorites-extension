import requests
from bs4 import BeautifulSoup
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API endpoint
API_URL = "http://localhost:8000/api/favorites/"

# List of tech-related websites with specific paths
TECH_WEBSITES = [
    "https://www.wired.com/category/artificial-intelligence/",
    "https://techcrunch.com/category/startups/",
    "https://www.theverge.com/tech",
    "https://arstechnica.com/gadgets/",
    "https://www.engadget.com/mobile/",
    "https://www.cnet.com/tech/computing/",
    "https://www.technologyreview.com/topic/artificial-intelligence/",
    "https://www.anandtech.com/tag/cpus",
    "https://www.tomshardware.com/reviews/gpu-hierarchy,4388.html",
    "https://www.pcgamer.com/hardware/"
]

def get_webpage_title(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.title.string if soup.title else "No title found"
        return title.strip()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch title for {url}. Error: {str(e)}")
        return "Error fetching title"

def generate_favorite(url):
    title = get_webpage_title(url)
    return {"url": url, "title": title}

def create_favorite(favorite):
    try:
        response = requests.post(API_URL, json=favorite)
        response.raise_for_status()
        logging.info(f"Successfully created favorite: {favorite['title']}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to create favorite: {favorite['title']}. Error: {str(e)}")
        return None

def stress_test(num_favorites, delay):
    successful_creations = 0
    failed_creations = 0

    start_time = time.time()

    for i in range(num_favorites):
        url = TECH_WEBSITES[i % len(TECH_WEBSITES)]
        favorite = generate_favorite(url)
        result = create_favorite(favorite)
        
        if result:
            successful_creations += 1
        else:
            failed_creations += 1

        time.sleep(delay)

    end_time = time.time()
    total_time = end_time - start_time

    logging.info(f"\nStress test completed.")
    logging.info(f"Total favorites attempted: {num_favorites}")
    logging.info(f"Successful creations: {successful_creations}")
    logging.info(f"Failed creations: {failed_creations}")
    logging.info(f"Total time taken: {total_time:.2f} seconds")
    logging.info(f"Average time per request: {total_time/num_favorites:.2f} seconds")

if __name__ == "__main__":
    num_favorites = 10  # Reduced number for demonstration, adjust as needed
    delay = 1  # Increased delay to be more respectful to the websites

    logging.info(f"Starting stress test with {num_favorites} favorites and {delay} second delay between requests.")
    stress_test(num_favorites, delay)