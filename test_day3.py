"""
test_day3.py

Day 3 checkpoint script. Ingests:
  1. Past year question papers (PDFs) from sample_data/past_qps/,
     tagging each with a "year" pulled from the filename.
  2. Lecture videos/audio from sample_data/lecture_videos/, transcribed
     locally via faster-whisper.

Both get chunked and stored in the SAME ChromaDB collection as Day 2,
tagged with source_type so the Pattern Agent (Day 4) can filter by it.

Setup:
    sample_data/
        past_qps/
            2022.pdf
            2023.pdf
            2024.pdf
        lecture_videos/
            lecture1.mp4   (or .mp3/.wav)

    Name your past QP files so a 4-digit year appears somewhere in the
    filename (e.g. "2023.pdf", "dbms_2023_endsem.pdf") — the script
    extracts it automatically. If no year is found, it'll ask you.

Run with:
    python test_day3.py
"""

import os
import re
import sys

from ingestion.pdf_loader import load_pdf_pages
from ingestion.video_loader import transcribe_video, save_transcript
from ingestion.chunker import chunk_pages
from embeddings.embed_store import store_chunks, query, collection_count

PAST_QP_DIR = os.path.join("sample_data", "past_qps")
VIDEO_DIR = os.path.join("sample_data", "lecture_videos")
VIDEO_EXTENSIONS = (".mp4", ".mp3", ".wav", ".m4a")


def extract_year(filename: str) -> int:
    """Pulls a 4-digit year out of a filename, or asks the user."""
    match = re.search(r"(19|20)\d{2}", filename)
    if match:
        return int(match.group(0))

    user_input = input(f"  Couldn't detect year in '{filename}'. Enter it manually: ").strip()
    return int(user_input) if user_input.isdigit() else 0


def ingest_past_qp(filename: str):
    path = os.path.join(PAST_QP_DIR, filename)
    year = extract_year(filename)
    print(f"\nLoading past QP: {filename} (year={year})")

    pages = load_pdf_pages(path)
    print(f"  Extracted {len(pages)} pages of text.")

    chunks = chunk_pages(
        pages,
        source_type="past_qp",
        filename=filename,
        extra_metadata={"year": year},
    )
    print(f"  Split into {len(chunks)} chunks.")

    print("  Embedding + storing in ChromaDB...")
    stored = store_chunks(chunks)
    print(f"  Stored {stored} chunks.")


def ingest_video(filename: str):
    path = os.path.join(VIDEO_DIR, filename)
    print(f"\nTranscribing lecture video: {filename}")

    segments = transcribe_video(path)
    print(f"  Produced {len(segments)} transcript segments.")

    # Save a plain-text transcript alongside the video for reference
    transcript_path = os.path.join(VIDEO_DIR, f"{filename}.transcript.txt")
    save_transcript(segments, transcript_path)
    print(f"  Saved transcript to {transcript_path}")

    chunks = chunk_pages(
        segments,
        source_type="lecture_video",
        filename=filename,
    )
    print(f"  Split into {len(chunks)} chunks.")

    print("  Embedding + storing in ChromaDB...")
    stored = store_chunks(chunks)
    print(f"  Stored {stored} chunks.")


if __name__ == "__main__":
    print("=" * 50)
    print("Day 3 Checkpoint: Past QPs + Lecture Video Ingestion")
    print("=" * 50)

    found_anything = False

    if os.path.isdir(PAST_QP_DIR):
        qp_files = [f for f in os.listdir(PAST_QP_DIR) if f.lower().endswith(".pdf")]
        if qp_files:
            found_anything = True
            for f in qp_files:
                ingest_past_qp(f)
    else:
        print(f"\nNo folder found at ./{PAST_QP_DIR}/ — skipping past QPs.")

    if os.path.isdir(VIDEO_DIR):
        video_files = [f for f in os.listdir(VIDEO_DIR) if f.lower().endswith(VIDEO_EXTENSIONS)]
        if video_files:
            found_anything = True
            for f in video_files:
                ingest_video(f)
    else:
        print(f"\nNo folder found at ./{VIDEO_DIR}/ — skipping videos.")

    if not found_anything:
        print("\nNothing to ingest. Create sample_data/past_qps/ and/or")
        print("sample_data/lecture_videos/ with at least one file, then rerun.")
        sys.exit(1)

    print(f"\nTotal chunks now in ChromaDB: {collection_count()}")

    # Quick test: filter by source_type to prove tagging worked
    print("\n--- Testing metadata filter (past_qp only) ---")
    test_question = input("Enter a question to test against past QPs only (or Enter to skip): ").strip()

    if test_question:
        results = query(test_question, n_results=3, where={"source_type": "past_qp"})
        docs = results["documents"][0]
        metadatas = results["metadatas"][0]

        if not docs:
            print("No past_qp matches found.")
        for i, (doc, meta) in enumerate(zip(docs, metadatas), start=1):
            preview = doc[:150].replace("\n", " ")
            print(f"\n[{i}] year={meta.get('year')} source={meta['filename']}")
            print(f"    {preview}...")

    print("\n" + "=" * 50)
    print("Day 3 checkpoint complete.")
    print("=" * 50)
