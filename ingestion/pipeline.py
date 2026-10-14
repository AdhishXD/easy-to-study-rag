"""One entry point for parsing, chunking and indexing study material."""

from pathlib import Path
import hashlib
import json
import os
import re

from ingestion.chunker import chunk_pages
from ingestion.document_loader import DOCUMENT_EXTENSIONS, load_document
from ingestion.source_store import replace_pages, source_fingerprint, register_source
from embeddings.embed_store import store_chunks, delete_source_vectors, embedding_identity, COLLECTION_NAME, CHROMA_DB_PATH, get_collection
from agents.runtime import report, check_cancelled

VIDEO_EXTENSIONS = {".mp4", ".mp3", ".wav", ".m4a", ".webm"}
SOURCE_TYPES = {"textbook", "lecture_note", "lecture_slide", "lecture_video", "past_qp"}


def extract_year(filename: str) -> int | None:
    """Accept a four-digit year or the two-digit suffix used by MIT papers."""
    match = re.search(r"(?<!\d)(20\d{2})(?!\d)", filename)
    if match:
        return int(match.group(1))
    match = re.search(r"(?:^|[-_])(ese|makeup|endsem|midsem)[-_](\d{2})(?:\D|$)", filename, re.I)
    return 2000 + int(match.group(2)) if match else None


def ingest_file(path: str | Path, source_type: str, *, subject: str,
                year: int | None = None, save_video_transcript: bool = False) -> int:
    """Index one file. A subject keeps unrelated courses out of the same analysis."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"Unknown source_type: {source_type}")
    if not subject.strip():
        raise ValueError("A subject/course name is required")
    subject = subject.strip()
    if source_type == "past_qp":
        year = extract_year(path.name) or year
        if year is None or not 1900 <= year <= 2100:
            raise ValueError(f"A valid exam year is required for {path.name}")
    digest = hashlib.sha256()
    digest.update(json.dumps({"version": 2, "chunks": [700, 100],
                              "embed": embedding_identity(),
                              "mode": os.getenv("MODE", "local"),
                              "store": os.getenv("CHROMA_DB_PATH", "./db/chroma_store"),
                              "whisper": os.getenv("WHISPER_MODEL_SIZE", "base"),
                              "beam": os.getenv("WHISPER_BEAM_SIZE", "1")}, sort_keys=True).encode())
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            check_cancelled()
            digest.update(data)
    fingerprint = digest.hexdigest()
    previous = source_fingerprint(subject, source_type, path.name)
    if previous and previous[0] == fingerprint and previous[2] == year:
        report(f"{path.name} is already indexed; reused its passages", 1)
        return previous[1]
    report(f"Reading {path.name}", 0.1)
    extension = path.suffix.lower()
    if source_type == "lecture_video":
        if extension not in VIDEO_EXTENSIONS:
            raise ValueError("Unsupported audio/video format")
        from ingestion.video_loader import transcribe_video, save_transcript
        pages = transcribe_video(str(path))
        if save_video_transcript:
            save_transcript(pages, str(path) + ".transcript.txt")
    else:
        if extension not in DOCUMENT_EXTENSIONS:
            raise ValueError("Supported documents: PDF, PPTX, PPT, DOCX, TXT, MD")
        pages = load_document(path)
    metadata = {"subject": subject.strip()}
    if source_type == "past_qp":
        metadata["year"] = year
    chunks = chunk_pages(pages, source_type, path.name, extra_metadata=metadata)
    if not chunks:
        raise ValueError(f"No extractable text in {path.name}; scanned PDFs need OCR")
    count = store_chunks(chunks)
    delete_source_vectors(subject, source_type, path.name, keep_ids=[c["id"] for c in chunks])
    replace_pages(subject.strip(), source_type, path.name, pages, year)
    register_source(subject, source_type, path.name, fingerprint, count, year)
    report(f"Indexed {path.name}", 1)
    return count


def ensure_subject_index(subject: str) -> None:
    """Rebuild a provider-specific index from saved pages without re-uploading files."""
    from collections import defaultdict
    from agents import cache
    from ingestion.source_store import get_pages, corpus_fingerprint
    pages = get_pages(subject)
    if not pages:
        return
    namespace = f"subject-index:{Path(CHROMA_DB_PATH).resolve()}:{COLLECTION_NAME}"
    fingerprint = corpus_fingerprint(pages)
    indexed = get_collection().get(where={"subject": subject}, limit=1, include=[])["ids"]
    if indexed and cache.get(namespace, subject) == fingerprint:
        return
    report("Preparing the course search index with the current embedding model", 0.05)
    files = defaultdict(list)
    for page in pages:
        files[(page["source_type"], page["filename"], page["year"])].append((page["page"], page["text"]))
    for (kind, filename, year), text in files.items():
        metadata = {"subject": subject}
        if year is not None:
            metadata["year"] = year
        chunks = chunk_pages(text, kind, filename, extra_metadata=metadata)
        store_chunks(chunks)
        delete_source_vectors(subject, kind, filename, keep_ids=[c["id"] for c in chunks])
    cache.put(namespace, subject, fingerprint)
