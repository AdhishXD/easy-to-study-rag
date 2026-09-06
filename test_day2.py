"""
test_day2.py

Day 2 checkpoint script. Loads a PDF and/or PPTX from a sample_data/
folder, chunks it, embeds it via Ollama, stores it in ChromaDB, then
runs a test query to confirm retrieval works end-to-end.

Setup:
    Create a folder called `sample_data/` in the project root and drop
    in ONE real PDF (a textbook chapter or lecture notes) and/or ONE
    PPTX (a lecture slide deck) you actually want to test with.

Run with:
    python test_day2.py
"""

import os
import sys

from ingestion.pdf_loader import load_pdf_pages
from ingestion.pptx_loader import load_pptx_slides
from ingestion.chunker import chunk_pages
from embeddings.embed_store import store_chunks, query, collection_count

SAMPLE_DIR = "sample_data"


def find_sample_files():
    if not os.path.isdir(SAMPLE_DIR):
        return [], []

    pdfs = [f for f in os.listdir(SAMPLE_DIR) if f.lower().endswith(".pdf")]
    pptxs = [f for f in os.listdir(SAMPLE_DIR) if f.lower().endswith(".pptx")]
    return pdfs, pptxs


def ingest_pdf(filename: str):
    path = os.path.join(SAMPLE_DIR, filename)
    print(f"\nLoading PDF: {filename}")
    pages = load_pdf_pages(path)
    print(f"  Extracted {len(pages)} pages of text.")

    chunks = chunk_pages(
        pages,
        source_type="textbook",
        filename=filename,
    )
    print(f"  Split into {len(chunks)} chunks.")

    print("  Embedding + storing in ChromaDB (this calls Ollama per chunk)...")
    stored = store_chunks(chunks)
    print(f"  Stored {stored} chunks.")


def ingest_pptx(filename: str):
    path = os.path.join(SAMPLE_DIR, filename)
    print(f"\nLoading PPTX: {filename}")
    slides = load_pptx_slides(path)
    print(f"  Extracted {len(slides)} slides of text.")

    chunks = chunk_pages(
        slides,
        source_type="lecture_slide",
        filename=filename,
    )
    print(f"  Split into {len(chunks)} chunks.")

    print("  Embedding + storing in ChromaDB (this calls Ollama per chunk)...")
    stored = store_chunks(chunks)
    print(f"  Stored {stored} chunks.")


if __name__ == "__main__":
    print("=" * 50)
    print("Day 2 Checkpoint: PDF + PPTX Ingestion")
    print("=" * 50)

    pdfs, pptxs = find_sample_files()

    if not pdfs and not pptxs:
        print(f"\nNo files found in ./{SAMPLE_DIR}/")
        print(f"Create the folder and add at least one .pdf or .pptx file, then rerun.")
        sys.exit(1)

    for pdf_file in pdfs:
        ingest_pdf(pdf_file)

    for pptx_file in pptxs:
        ingest_pptx(pptx_file)

    print(f"\nTotal chunks now in ChromaDB: {collection_count()}")

    # Test retrieval
    test_question = input(
        "\nEnter a question about your uploaded content to test retrieval: "
    ).strip()

    if test_question:
        print(f"\nQuerying for: '{test_question}'")
        results = query(test_question, n_results=3)

        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances), start=1):
            preview = doc[:150].replace("\n", " ")
            print(f"\n[{i}] (distance={dist:.4f}) source={meta['filename']} page={meta['page']}")
            print(f"    {preview}...")

    print("\n" + "=" * 50)
    print("Day 2 checkpoint complete.")
    print("=" * 50)
