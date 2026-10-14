"""
embeddings/embed_store.py

Handles turning chunk text into vectors (via Ollama's local embedding
model) and storing/querying them in a persistent ChromaDB collection.
"""

import os
from typing import List, Dict, Any, Optional

import chromadb
from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./db/chroma_store")
MODE = os.getenv("MODE", "local").lower()
COLLECTION_NAME = "exam_prep_demo" if MODE == "demo" else "exam_prep"

_chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_collection():
    """Returns (creating if needed) the shared Chroma collection."""
    return _chroma_client.get_or_create_collection(name=COLLECTION_NAME)


def embed_text(text: str) -> List[float]:
    """Use Ollama locally, or a small CPU embedding model in hosted demo mode."""
    if MODE == "demo":
        from sentence_transformers import SentenceTransformer
        global _demo_model
        if _demo_model is None:
            _demo_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return _demo_model.encode(text, normalize_embeddings=True).tolist()
    import ollama
    try:
        response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    except Exception:
        from agents.llm import logger
        logger.exception("embedding_failed model=%s text_chars=%d", EMBED_MODEL, len(text))
        raise
    return response["embedding"]


_demo_model = None


def store_chunks(chunk_records: List[Dict[str, Any]]) -> int:
    """
    Embeds and stores a list of chunk records (as produced by
    ingestion/chunker.py) into ChromaDB.

    Args:
        chunk_records: list of {"id": ..., "text": ..., "metadata": {...}}

    Returns:
        Number of chunks successfully stored.
    """
    collection = get_collection()

    ids, documents, embeddings, metadatas = [], [], [], []

    for record in chunk_records:
        vector = embed_text(record["text"])
        ids.append(record["id"])
        documents.append(record["text"])
        embeddings.append(vector)
        metadatas.append(record["metadata"])

    if ids:
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    return len(ids)


def query(
    query_text: str,
    n_results: int = 5,
    where: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Embeds a query and retrieves the most similar stored chunks.

    Args:
        query_text: the natural-language question or topic.
        n_results: how many matches to return.
        where: optional Chroma metadata filter, e.g. {"source_type": "past_qp"}

    Returns:
        Raw ChromaDB query result (documents, metadatas, distances).
    """
    collection = get_collection()
    if collection.count() == 0:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}
    query_vector = embed_text(query_text)

    return collection.query(
        query_embeddings=[query_vector],
        n_results=min(n_results, collection.count()),
        where=where,
    )


def collection_count() -> int:
    """Returns how many chunks are currently stored."""
    return get_collection().count()


def get_by_filter(where: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetches ALL chunks matching a metadata filter — no similarity
    search, no embedding call. Used by analysis steps (like the
    Pattern Agent) that need every matching chunk, not just the
    top-k most similar to some query.

    Args:
        where: Chroma metadata filter, e.g. {"source_type": "past_qp"}

    Returns:
        Flat dict with "documents" and "metadatas" lists (not nested
        like query() results, since there's no per-query grouping here).
    """
    collection = get_collection()
    return collection.get(where=where)


if __name__ == "__main__":
    print(f"Chunks currently stored: {collection_count()}")
