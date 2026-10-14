"""Focused checks for the upload and question-extraction regressions."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.analysis import _extract_paper_questions
from ingestion.chunker import chunk_pages
from ingestion.pipeline import ingest_file


class RegressionTests(unittest.TestCase):
    @patch("ingestion.pipeline.replace_pages")
    @patch("ingestion.pipeline.store_chunks", return_value=1)
    @patch("ingestion.pipeline.load_document", return_value=[(1, "Normalization reduces redundancy.")])
    def test_pdf_is_accepted_as_lecture_note(self, load, store, save):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Module-1.pdf"
            path.write_bytes(b"placeholder")
            count = ingest_file(path, "lecture_note", subject="DBMS")
        self.assertEqual(count, 1)
        load.assert_called_once()
        store.assert_called_once()
        save.assert_called_once_with("DBMS", "lecture_note", "Module-1.pdf",
                                     [(1, "Normalization reduces redundancy.")], None)

    @patch("agents.analysis._json_array", return_value=[
        "Explain normalization and why it reduces redundancy.",
        "Explain mitochondrial quantum teleportation in zebras.",
    ])
    def test_extracted_questions_must_match_source_words(self, _):
        pages = [{"text": "Explain normalization and why it reduces redundancy.",
                  "year": 2024, "filename": "paper.pdf", "page": 1}]
        questions = _extract_paper_questions(pages)
        self.assertEqual(len(questions), 1)
        self.assertIn("normalization", questions[0]["question"])

    def test_overlap_has_no_duplicate_tail_and_ids_are_stable(self):
        arguments = ([(1, "Functional dependency. " * 100)], "lecture_note", "note.pdf")
        first = chunk_pages(*arguments, extra_metadata={"subject": "DBMS"})
        second = chunk_pages(*arguments, extra_metadata={"subject": "DBMS"})
        self.assertEqual([r["id"] for r in first], [r["id"] for r in second])
        self.assertEqual(len({r["id"] for r in first}), len(first))
        self.assertGreater(len(first), 1)


if __name__ == "__main__":
    unittest.main()
