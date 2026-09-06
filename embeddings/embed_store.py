"""
embeddings/embed_store.py

Handles turning chunk text into vectors (via Ollama's local embedding
model) and storing/querying them in a persistent ChromaDB collection.
"""

import os
from typing import List, Dict, Any, Optional

import chromadb
import ollama
from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./db/chroma_store")
COLLECTION_NAME = "exam_prep"

_chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_collection():
    """Returns (creating if needed) the shared Chroma collection."""
    return _chroma_client.get_or_create_collection(name=COLLECTION_NAME)


def embed_text(text: str) -> List[float]:
    """Calls Ollama's local embedding model for a single piece of text."""
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


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
        collection.add(
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
    query_vector = embed_text(query_text)

    return collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        where=where,
    )


def collection_count() -> int:
    """Returns how many chunks are currently stored."""
    return get_collection().count()


if __name__ == "__main__":
    print(f"Chunks currently stored: {collection_count()}")
