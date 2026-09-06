"""
ingestion/pdf_loader.py

Extracts text from a PDF, page by page, so each chunk can later be
tagged with the page it came from (useful for citing sources in
generated quiz questions).
"""

from typing import List, Tuple

import pdfplumber


def load_pdf_pages(file_path: str) -> List[Tuple[int, str]]:
    """
    Extracts text from a PDF, one entry per page.

    Returns:
        A list of (page_number, page_text) tuples, 1-indexed.
        Blank/unreadable pages are skipped.
    """
    pages = []

    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                pages.append((i, text.strip()))

    return pages


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_loader.py <path_to_pdf>")
        sys.exit(1)

    result = load_pdf_pages(sys.argv[1])
    print(f"Extracted {len(result)} pages with text.")
    if result:
        first_page_num, first_page_text = result[0]
        preview = first_page_text[:200].replace("\n", " ")
        print(f"Page {first_page_num} preview: {preview}...")
