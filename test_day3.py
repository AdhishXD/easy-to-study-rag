"""Manual checkpoint: python test_day3.py <subject> <past-PDF/video> [more files]."""

import sys
from pathlib import Path

from ingestion.pipeline import VIDEO_EXTENSIONS, ingest_file


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    subject = sys.argv[1]
    for name in sys.argv[2:]:
        path = Path(name)
        source_type = "lecture_video" if path.suffix.lower() in VIDEO_EXTENSIONS else "past_qp"
        print(f"{path.name}: {ingest_file(path, source_type, subject=subject)} chunks")
