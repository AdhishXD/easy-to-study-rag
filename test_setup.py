"""
test_setup.py

Day 1 checkpoint script. Run this after installing everything to confirm:
  1. Ollama's LLM responds
  2. Ollama's embedding model responds
  3. ChromaDB can store and retrieve a vector

Run with:
    python test_setup.py

Prerequisites:
    - Ollama installed and running (`ollama serve`, usually starts automatically)
    - `ollama pull qwen2.5:7b` (or your chosen model)
    - `ollama pull nomic-embed-text`
    - pip install -r requirements.txt
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def test_ollama_chat():
    print(f"\n[1/3] Testing Ollama chat model: {LLM_MODEL}")
    try:
        import ollama

        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        content = response["message"]["content"].strip()
        print(f"      Model replied: {content}")
        print("      PASSED")
        return True
    except Exception as e:
        print(f"      FAILED: {e}")
        print(f"      -> Is Ollama running? Try: ollama run {LLM_MODEL}")
        return False


def test_ollama_embeddings():
    print(f"\n[2/3] Testing Ollama embedding model: {EMBED_MODEL}")
    try:
        import ollama

        response = ollama.embeddings(
            model=EMBED_MODEL,
            prompt="This is a test sentence for embedding.",
        )
        vector = response["embedding"]
        print(f"      Got embedding vector of length: {len(vector)}")
        print("      PASSED")
        return True, len(vector)
    except Exception as e:
        print(f"      FAILED: {e}")
        print(f"      -> Try: ollama pull {EMBED_MODEL}")
        return False, 0


def test_chromadb(embedding_dim):
    print("\n[3/3] Testing ChromaDB store + retrieve")
    try:
        import chromadb

        client = chromadb.Client()  # in-memory, just for this test
        collection = client.get_or_create_collection(name="setup_test")

        # Fake embedding matching the real dimension so this test is meaningful
        fake_vector = [0.01] * embedding_dim if embedding_dim else [0.01] * 384

        collection.add(
            ids=["test_1"],
            embeddings=[fake_vector],
            documents=["This is a test document."],
            metadatas=[{"source_type": "test"}],
        )

        result = collection.query(query_embeddings=[fake_vector], n_results=1)
        retrieved_doc = result["documents"][0][0]
        print(f"      Retrieved: {retrieved_doc}")
        print("      PASSED")
        return True
    except Exception as e:
        print(f"      FAILED: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Day 1 Environment Checkpoint")
    print("=" * 50)

    chat_ok = test_ollama_chat()
    embed_ok, embed_dim = test_ollama_embeddings()
    chroma_ok = test_chromadb(embed_dim)

    print("\n" + "=" * 50)
    if chat_ok and embed_ok and chroma_ok:
        print("ALL CHECKS PASSED. You're ready for Day 2.")
    else:
        print("SOME CHECKS FAILED. Fix the issues above before moving on.")
        sys.exit(1)
    print("=" * 50)
