import chromadb
from chromadb.utils import embedding_functions
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from tqdm import tqdm
from rich import print as rprint
import builtins

builtins.print = rprint

persist_directory = os.environ.get('CHROMA_DIR', './chroma_db')

class VectorStore:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.chroma_client.get_or_create_collection(
            name="favorites_embeddings",
            embedding_function=embedding_functions.DefaultEmbeddingFunction()
        )
        
        # Create SQLite engine and session
        self.engine = create_engine(f'sqlite:///{os.path.join(persist_directory, "chroma.sqlite3")}')
        self.Session = sessionmaker(bind=self.engine)
        
        # Create full-text search index if it doesn't exist
        self._create_fts_index()

    def _create_fts_index(self):
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS favorites_fts USING fts5(
                    id, url, title, summary
                );
            """))
            conn.commit()

    def populate_from_database(self, favorites):
        total_favorites = len(favorites)
        batch_size = 100  # Adjust this value based on your needs

        for i in tqdm(range(0, total_favorites, batch_size), desc="Populating vector store"):
            batch = favorites[i:i+batch_size]
            
            # Prepare data for batch insertion
            ids = [str(favorite.id) for favorite in batch]
            metadatas = [{"url": favorite.url, "title": favorite.title, "summary": favorite.summary} for favorite in batch]
            documents = [f"{favorite.title} {favorite.summary}" for favorite in batch]
            
            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                metadatas=metadatas,
                documents=documents
            )
            
            # Add to full-text search index
            with self.Session() as session:
                for favorite in batch:
                    session.execute(text("""
                        INSERT OR REPLACE INTO favorites_fts (id, url, title, summary)
                        VALUES (:id, :url, :title, :summary)
                    """), {"id": favorite.id, "url": favorite.url, "title": favorite.title, "summary": favorite.summary})
                session.commit()

    def add_favorite(self, id, url, title, summary):
        self.collection.add(
            ids=[str(id)],
            metadatas={"url": url, "title": title, "summary": summary},
            documents=[f"{title} {summary}"]
        )
        
        # Add to full-text search index
        with self.Session() as session:
            session.execute(text("""
                INSERT OR REPLACE INTO favorites_fts (id, url, title, summary)
                VALUES (:id, :url, :title, :summary)
            """), {"id": id, "url": url, "title": title, "summary": summary})
            session.commit()

    def update_favorite(self, id, url, title, summary):
        self.collection.update(
            ids=[str(id)],
            metadatas={"url": url, "title": title, "summary": summary},
            documents=[f"{title} {summary}"]
        )
        
        # Update full-text search index
        with self.Session() as session:
            session.execute(text("""
                INSERT OR REPLACE INTO favorites_fts (id, url, title, summary)
                VALUES (:id, :url, :title, :summary)
            """), {"id": id, "url": url, "title": title, "summary": summary})
            session.commit()

    def delete_favorite(self, id):
        self.collection.delete(ids=[str(id)])
        
        # Delete from full-text search index
        with self.Session() as session:
            session.execute(text("DELETE FROM favorites_fts WHERE id = :id"), {"id": id})
            session.commit()

    def search_favorites(self, query, limit=10):
        # Perform vector search
        vector_results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        # Perform full-text search
        with self.Session() as session:
            fts_results = session.execute(text("""
                SELECT id, url, title, summary, rank
                FROM favorites_fts
                WHERE favorites_fts MATCH :query
                ORDER BY rank
                LIMIT :limit
            """), {"query": query, "limit": limit}).fetchall()
        
        # Combine and deduplicate results
        combined_results = self._combine_results(vector_results, fts_results, limit)
        
        return combined_results

    def _combine_results(self, vector_results, fts_results, limit):
        combined = {}
        
        # Add vector search results
        for i, id in enumerate(vector_results['ids'][0]):
            combined[id] = {
                "id": int(id),
                "url": vector_results['metadatas'][0][i]['url'],
                "title": vector_results['metadatas'][0][i]['title'],
                "summary": vector_results['metadatas'][0][i]['summary'],
                "vector_score": vector_results['distances'][0][i],
                "fts_rank": None
            }
        
        # Add or update with full-text search results
        for result in fts_results:
            id_str = str(result.id)
            if id_str in combined:
                combined[id_str]["fts_rank"] = result.rank
            else:
                combined[id_str] = {
                    "id": result.id,
                    "url": result.url,
                    "title": result.title,
                    "summary": result.summary,
                    "vector_score": None,
                    "fts_rank": result.rank
                }
        
        # Sort results based on a combined score
        sorted_results = sorted(
            combined.values(),
            key=lambda x: (
                -(x["vector_score"] or float('inf')),  # Lower vector_score is better
                x["fts_rank"] or float('inf')  # Lower fts_rank is better
            )
        )
        return sorted_results[:limit]

vector_store = VectorStore()