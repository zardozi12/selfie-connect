import numpy as np
from typing import List, Tuple

class InMemoryVectorStore:
    def __init__(self):
        self.vectors: List[Tuple[int, np.ndarray]] = []  # (image_id, embedding)

    def add(self, image_id: int, embedding: np.ndarray):
        self.vectors.append((image_id, embedding))

    def search(self, query: np.ndarray, top_k: int = 5) -> List[int]:
        sims = [(image_id, float(np.dot(vec, query) / ((np.linalg.norm(vec) * np.linalg.norm(query)) or 1e-9)))
                for image_id, vec in self.vectors]
        sims.sort(key=lambda x: x[1], reverse=True)
        return [image_id for image_id, _ in sims[:top_k]]

"""
pgvector service for PhotoVault
Handles vector embeddings storage and similarity search using PostgreSQL with pgvector extension
"""

from typing import List, Dict, Any
from tortoise import Tortoise


def _is_postgres() -> bool:
    """Check if we're using PostgreSQL (required for pgvector)"""
    try:
        conn = Tortoise.get_connection("default")
        return conn.capabilities.dialect == "postgres"
    except Exception:
        return False


async def upsert_image_vector(image_id: str, emb: List[float]) -> None:
    """
    Store or update image embedding in pgvector table.
    
    Args:
        image_id: UUID of the image
        emb: Embedding vector (list of floats)
    """
    if not _is_postgres():
        return
    
    try:
        await Tortoise.get_connection("default").execute_query(
            """
            INSERT INTO image_embeddings (image_id, emb)
            VALUES ($1, $2)
            ON CONFLICT (image_id)
            DO UPDATE SET emb = EXCLUDED.emb
            """,
            [image_id, emb],
        )
    except Exception as e:
        print(f"Failed to upsert vector embedding: {e}")


async def search_vectors(query_vec: List[float], top_k: int = 20) -> List[Dict[str, Any]]:
    """
    Search for similar images using pgvector cosine similarity.
    
    Args:
        query_vec: Query embedding vector
        top_k: Number of results to return
    
    Returns:
        List of results with image_id and similarity score
    """
    if not _is_postgres():
        return []
    
    try:
        rows = await Tortoise.get_connection("default").execute_query_dict(
            """
            SELECT image_id, 1 - (emb <=> $1) AS score
            FROM image_embeddings
            ORDER BY emb <=> $1
            LIMIT $2
            """,
            [query_vec, top_k],
        )
        return rows
    except Exception as e:
        print(f"Vector search failed: {e}")
        return []


async def delete_image_vector(image_id: str) -> None:
    """
    Delete image embedding from pgvector table.
    
    Args:
        image_id: UUID of the image to delete
    """
    if not _is_postgres():
        return
    
    try:
        await Tortoise.get_connection("default").execute_query(
            "DELETE FROM image_embeddings WHERE image_id = $1",
            [image_id],
        )
    except Exception as e:
        print(f"Failed to delete vector embedding: {e}")


async def get_vector_stats() -> Dict[str, Any]:
    """
    Get statistics about vector embeddings.
    
    Returns:
        Dictionary with embedding count and other stats
    """
    if not _is_postgres():
        return {"count": 0, "database": "not_postgres"}
    
    try:
        result = await Tortoise.get_connection("default").execute_query_dict(
            "SELECT COUNT(*) as count FROM image_embeddings"
        )
        return {
            "count": result[0]["count"] if result else 0,
            "database": "postgres_with_pgvector"
        }
    except Exception as e:
        print(f"Failed to get vector stats: {e}")
        return {"count": 0, "error": str(e)}
