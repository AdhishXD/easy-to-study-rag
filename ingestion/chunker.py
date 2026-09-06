
# Chunking. PDFs, PPTX and past QPs are made into flat list of chunks, tagged with metadata. 

import uuid
from typing import List, Tuple, Dict, Any

CHUNK_SIZE = 700       # characters per chunk
CHUNK_OVERLAP = 100    # characters shared between consecutive chunks


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Plain sliding-window string splitter. No API call needed."""
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start += chunk_size - chunk_overlap

    return chunks


def chunk_pages(
    pages: List[Tuple[int, str]],
    source_type: str,
    filename: str,
    extra_metadata: Dict[str, Any] = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,) -> List[Dict[str, Any]]:
    """
    Converts loader output into a list of chunk records ready for embedding.

    Args:
        pages: list of (page_or_slide_number, text) tuples from a loader.
        source_type: one of "textbook", "lecture_slide", "past_qp",
                     "lecture_video" — used later by the Pattern Agent
                     to filter which chunks to analyze.
        filename: original file name, kept for traceability/citation.
        extra_metadata: any additional tags, e.g. {"year": 2023, "subject": "DBMS"}
        chunk_size / chunk_overlap: passed through to the splitter.

    Returns:
        A list of dicts: {"id": ..., "text": ..., "metadata": {...}}
    """
    extra_metadata = extra_metadata or {}
    records = []

    for page_num, page_text in pages:
        pieces = _split_text(page_text, chunk_size, chunk_overlap)
        for piece in pieces:
            metadata = {
                "source_type": source_type,
                "filename": filename,
                "page": page_num,
                **extra_metadata,
            }
            records.append(
                {
                    "id": str(uuid.uuid4()),
                    "text": piece,
                    "metadata": metadata,
                }
            )

    return records


if __name__ == "__main__":
    # Quick sanity check with fake data
    fake_pages = [(1, "A" * 1500), (2, "B" * 500)]
    result = chunk_pages(
        fake_pages,
        source_type="textbook",
        filename="sample.pdf",
        extra_metadata={"subject": "DBMS"},
    )
    print(f"Produced {len(result)} chunks from 2 fake pages.")
    for r in result:
        print(f"  page={r['metadata']['page']} len={len(r['text'])} id={r['id'][:8]}...")
