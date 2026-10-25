"""Inspect work sizes and measure read endpoints without running any inference."""

import argparse
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.main import app
from agents.analysis import _batches, _teaching_batches, _paper_batches
from ingestion.source_store import list_subjects, get_pages


def audit():
    courses = []
    for subject in list_subjects():
        name = subject["name"]
        teaching = get_pages(name, ("lecture_note", "lecture_slide", "textbook", "lecture_video"))
        papers = get_pages(name, ("past_qp",))
        courses.append({"subject": name, "teaching_pages": len(teaching), "paper_pages": len(papers),
                        "old_teaching_requests": len(list(_teaching_batches(teaching, 5500))),
                        "new_teaching_requests": len(list(_teaching_batches(teaching))),
                        "old_paper_requests": len(list(_batches(papers))),
                        "new_paper_requests": len(_paper_batches(papers))})
    client = TestClient(app)
    latencies = {}
    for endpoint in ["/api/health", "/api/subjects"] + ([f"/api/analysis?subject={courses[0]['subject']}"] if courses else []):
        samples = []
        for _ in range(10):
            started = time.perf_counter()
            response = client.get(endpoint)
            response.raise_for_status()
            samples.append((time.perf_counter() - started) * 1000)
        latencies[endpoint] = round(statistics.median(samples), 2)
    return {"inference_performed": False, "courses": courses, "api_median_ms": latencies}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    result = audit()
    print(json.dumps(result, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
