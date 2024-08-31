import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import os
from tqdm import tqdm

class VectorStore:
    def __init__(self):
        # Use a persistent directory for the database
        persist_directory = "chroma_db"
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)

        self.client = chromadb.PersistentClient(path=persist_directory)

        self.collection = self.client.get_or_create_collection(
            name="favorites_embeddings",
            embedding_function=embedding_functions.DefaultEmbeddingFunction()
        )

    def add_favorite(self, id, url, title, summary):
        # Check if the document already exists
        existing_docs = self.collection.get(ids=[str(id)])
        if existing_docs['ids']:
            # Update the existing document
            self.collection.update(
                ids=[str(id)],
                documents=[summary],
                metadatas=[{"url": url, "title": title}]
            )
        else:
            # Add a new document
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
                "summary": document
            }
            for id, metadata, document in zip(results['ids'][0], results['metadatas'][0], results['documents'][0])
        ]

    def populate_from_database(self, favorites):
        total_favorites = len(favorites)
        for favorite in tqdm(favorites, total=total_favorites, desc="Populating vector store", unit="favorite"):
            # Check if the document already exists
            existing_docs = self.collection.get(ids=[str(favorite.id)])
            if existing_docs['ids']:
                # Update the existing document
                self.update_favorite(favorite.id, favorite.url, favorite.title, favorite.summary)
            else:
                # Add a new document
                self.add_favorite(favorite.id, favorite.url, favorite.title, favorite.summary)

vector_store = VectorStore()