"""One entry point for parsing, chunking and indexing study material."""

from pathlib import Path
import re

from ingestion.chunker import chunk_pages
from ingestion.document_loader import DOCUMENT_EXTENSIONS, load_document
from ingestion.source_store import replace_pages
from embeddings.embed_store import store_chunks

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
        year = year or extract_year(path.name)
        if year is None or not 1900 <= year <= 2100:
            raise ValueError(f"A valid exam year is required for {path.name}")
        metadata["year"] = year
    chunks = chunk_pages(pages, source_type, path.name, extra_metadata=metadata)
    if not chunks:
        raise ValueError(f"No extractable text in {path.name}; scanned PDFs need OCR")
    count = store_chunks(chunks)
    replace_pages(subject.strip(), source_type, path.name, pages, year)
    return count


