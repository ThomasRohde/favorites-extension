import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorStore, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        self.client = chromadb.Client(Settings(is_persistent=False))
        self.collection = self.client.create_collection("favorites")
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

    def add_favorite(self, id, url, title, summary):
        self.collection.add(
            ids=[str(id)],
            documents=[summary],
            metadatas=[{"url": url, "title": title}]
        )

    def update_favorite(self, id, url, title, summary):
        self.collection.update(
            ids=[str(id)],
            documents=[summary],
            metadatas=[{"url": url, "title": title}]
        )

    def delete_favorite(self, id):
        self.collection.delete(ids=[str(id)])

    def search_favorites(self, query, limit=10):
        results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        return [
            {
                "id": int(id),
                "url": metadata["url"],
                "title": metadata["title"],
                "distance": distance
            }
            for id, metadata, distance in zip(results["ids"][0], results["metadatas"][0], results["distances"][0])
        ]

    def populate_from_database(self, favorites):
        total_favorites = len(favorites)
        logger.info(f"Initializing vector store with {total_favorites} favorites")
        
        for favorite in tqdm(favorites, total=total_favorites, desc="Adding favorites to vector store"):
            self.add_favorite(favorite.id, favorite.url, favorite.title, favorite.summary)
        
        logger.info(f"Vector store initialization complete")

vector_store = VectorStore()