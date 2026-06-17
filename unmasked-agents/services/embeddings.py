import os
from openai import OpenAI
from services.db import get_connection

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def get_embedding(text: str) -> list[float]:
    if not client:
        return [0.0] * 1536
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


async def search_knowledge_base(query_text: str, top_k: int = 5, threshold: float = 0.6) -> list[dict]:
    """
    DSA: Approximate nearest-neighbor search using cosine similarity.
    The <=> operator computes cosine distance in pgvector.
    IVFFlat index makes this sub-linear instead of scanning every row.
    """
    query_embedding = await get_embedding(query_text)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT source, content, metadata,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM knowledge_base
            WHERE 1 - (embedding <=> $1::vector) > $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """, embedding_str, threshold, top_k)

    return [
        {
            "source": row["source"],
            "content": row["content"],
            "metadata": row["metadata"],
            "similarity": round(float(row["similarity"]), 4),
        }
        for row in rows
    ]
