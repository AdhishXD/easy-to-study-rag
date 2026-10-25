"""
embeddings/embed_store.py

Embeds text with a small CPU model (or optional Ollama) and stores/query
vectors in a persistent, provider-specific ChromaDB collection.
"""

import os
import hashlib
from functools import lru_cache
from agents import cache
from agents.runtime import report, check_cancelled
from typing import List, Dict, Any, Optional

import chromadb
from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./db/chroma_store")
MODE = os.getenv("MODE", "local").lower()
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "fastembed").lower()
FASTEMBED_MODEL = os.getenv("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
if EMBED_PROVIDER not in {"fastembed", "ollama"}:
    raise ValueError("EMBED_PROVIDER must be fastembed or ollama")


def embedding_identity() -> str:
    return f"{EMBED_PROVIDER}:{FASTEMBED_MODEL if EMBED_PROVIDER == 'fastembed' else EMBED_MODEL}"


COLLECTION_NAME = "exam_prep_demo" if MODE == "demo" else "exam_prep"
if EMBED_PROVIDER == "fastembed":
    COLLECTION_NAME += "_" + hashlib.sha256(embedding_identity().encode()).hexdigest()[:10]

@lru_cache(maxsize=1)
def _client():
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_collection():
    """Returns (creating if needed) the shared Chroma collection."""
    collection = _client().get_or_create_collection(name=COLLECTION_NAME)
    expected = embedding_identity()
    stored = (collection.metadata or {}).get("embedding_model")
    accepted = {expected, EMBED_MODEL} if EMBED_PROVIDER == "ollama" else {expected}
    if stored and stored not in accepted:
        raise ValueError("Embedding model changed. Use a new CHROMA_DB_PATH and re-index your files.")
    if not stored:
        # Existing indices were created using nomic locally / MiniLM in demo mode.
        legacy = "all-MiniLM-L6-v2" if MODE == "demo" else "nomic-embed-text"
        if collection.count() and (EMBED_PROVIDER != "ollama" or EMBED_MODEL != legacy):
            raise ValueError("Existing vectors use a different embedding model; choose a new CHROMA_DB_PATH.")
        collection.modify(metadata={**(collection.metadata or {}), "embedding_model": expected})
    # The old index tagged its model without a provider prefix.
    return collection


@lru_cache(maxsize=1)
def cpu_model():
    report("Loading the free CPU embedding model", 0.2)
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=FASTEMBED_MODEL, cache_dir=os.getenv("MODEL_CACHE_PATH", "./db/model_cache"),
                         threads=min(4, max(1, (os.cpu_count() or 2) // 2)))


def embed_many(texts: list[str]) -> list[list[float]]:
    """Cache by text/model and send missing vectors as one batch request."""
    if not texts:
        return []
    check_cancelled()
    namespace = "embedding:" + embedding_identity()
    keys = [hashlib.sha256(text.encode()).hexdigest() for text in texts]
    saved = cache.get_many(namespace, keys)
    vectors = [saved.get(key) for key in keys]
    missing = list(dict.fromkeys(key for key in keys if key not in saved))
    if not missing:
        return vectors
    by_key = dict(zip(keys, texts))
    inputs = [by_key[key] for key in missing]
    if EMBED_PROVIDER == "fastembed":
        generated = [vector.tolist() for vector in cpu_model().embed(inputs, batch_size=32)]
    else:
        import ollama
        client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"), timeout=180)
        generated = client.embed(model=EMBED_MODEL, input=inputs, keep_alive="10m")["embeddings"]
    if len(generated) != len(missing):
        raise ValueError("Embedding model returned an incomplete batch")
    new = dict(zip(missing, generated))
    cache.put_many(namespace, new)
    return [(saved | new)[key] for key in keys]


def embed_text(text: str) -> List[float]:
    return embed_many([text])[0]


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

    batch_size = min(256, max(1, int(os.getenv("EMBED_BATCH_SIZE", "32"))))
    for start in range(0, len(chunk_records), batch_size):
        batch = chunk_records[start:start + batch_size]
        report(f"Embedding passages {start + 1}–{min(start + batch_size, len(chunk_records))} of {len(chunk_records)}", 0.2 + 0.7 * start / len(chunk_records))
        ids.extend(record["id"] for record in batch)
        documents.extend(record["text"] for record in batch)
        embeddings.extend(embed_many([record["text"] for record in batch]))
        metadatas.extend(record["metadata"] for record in batch)
    # Stage all embeddings before touching a source's index. Cancellation or
    # an inference failure must not leave half of an existing file overwritten.
    check_cancelled()
    write_batch = min(1000, _client().get_max_batch_size())
    for start in range(0, len(ids), write_batch):
        collection.upsert(
            ids=ids[start:start + write_batch],
            documents=documents[start:start + write_batch],
            embeddings=embeddings[start:start + write_batch],
            metadatas=metadatas[start:start + write_batch],
        )

    return len(chunk_records)


def delete_source_vectors(subject: str, source_type: str, filename: str, keep_ids: list[str] | None = None) -> None:
    collection = get_collection()
    where = {"$and": [{"subject": subject}, {"source_type": source_type}, {"filename": filename}]}
    if keep_ids is None:
        collection.delete(where=where)
    else:
        existing = collection.get(where=where, include=[])["ids"]
        keep = set(keep_ids)
        stale = [id_ for id_ in existing if id_ not in keep]
        if stale:
            collection.delete(ids=stale)


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
