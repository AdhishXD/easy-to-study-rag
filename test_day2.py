"""Manual checkpoint: python test_day2.py <subject> <lecture_note|textbook> <files...>."""

import sys
from ingestion.pipeline import ingest_file


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    subject = sys.argv[1]
    source_type = sys.argv[2]
    if source_type not in {"lecture_note", "textbook"}:
        raise SystemExit(__doc__)
    for path in sys.argv[3:]:
        print(f"{path}: {ingest_file(path, source_type, subject=subject)} chunks")
