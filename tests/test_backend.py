"""Behavior checks using isolated data stores. No API keys or real model calls."""

from contextlib import ExitStack
import json
import os
from pathlib import Path
from threading import Event
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.main import app
from ingestion import source_store
from agents.analysis import analyze_subject, save_analysis, _extract_paper_questions, _find_repeats
from agents.llm import chat
from backend.practice import save_quiz, answer_question, progress, latest_quiz


class IsolatedTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.directory.name)
        self.stack = ExitStack()
        self.stack.enter_context(patch.dict(os.environ, {"CACHE_DB_PATH": str(self.root / "runtime.sqlite3"),
                                                       "LLM_PROVIDER": "ollama", "OLLAMA_LLM_MODEL": "qwen2.5:7b",
                                                       "APP_ACCESS_TOKEN": "", "LOG_LLM_CONTENT": "0"}))
        self.stack.enter_context(patch("ingestion.source_store.DB_PATH", self.root / "pages.sqlite3"))
        self.stack.enter_context(patch("agents.analysis.DB_PATH", self.root / "pages.sqlite3"))
        self.stack.enter_context(patch("backend.main.DEMO", False))
        self.stack.enter_context(patch("embeddings.embed_store.EMBED_PROVIDER", "ollama"))

    def tearDown(self):
        self.stack.close()
        self.directory.cleanup()

    def test_chat_cache_avoids_inference_and_separates_models(self):
        with patch("ollama.Client") as client:
            client.return_value.chat.return_value = {"message": {"content": '["normalization"]'}}
            self.assertEqual(chat("same context"), chat("same context"))
            self.assertEqual(client.return_value.chat.call_count, 1)
            with patch.dict(os.environ, {"OLLAMA_LLM_MODEL": "qwen3:4b"}):
                chat("same context")
            self.assertEqual(client.return_value.chat.call_count, 2)

    def test_invalid_json_is_not_cached(self):
        with patch("ollama.Client") as client:
            client.return_value.chat.return_value = {"message": {"content": "not JSON"}}
            chat("bad context"); chat("bad context")
            self.assertEqual(client.return_value.chat.call_count, 2)

    def test_unchanged_upload_skips_parsing_and_vectors(self):
        from ingestion.pipeline import ingest_file
        file = self.root / "notes.txt"
        file.write_text("Normalization reduces redundancy and update anomalies.")
        with patch("ingestion.pipeline.load_document", return_value=[(1, file.read_text())]) as parse, \
             patch("ingestion.pipeline.store_chunks", return_value=1) as store, \
             patch("ingestion.pipeline.delete_source_vectors"):
            self.assertEqual(ingest_file(file, "lecture_note", subject="DBMS"), 1)
            save_analysis({"subject": "DBMS", "topics": ["keep"]})
            self.assertEqual(ingest_file(file, "lecture_note", subject="DBMS"), 1)
            self.assertEqual(parse.call_count, 1)
            self.assertEqual(store.call_count, 1)
            from agents.analysis import get_analysis
            self.assertEqual(get_analysis("DBMS")["topics"], ["keep"])

    def test_embedding_batch_and_cache(self):
        from embeddings.embed_store import embed_many
        with patch("ollama.Client") as client:
            client.return_value.embed.return_value = {"embeddings": [[1.0, 0.0], [0.0, 1.0]]}
            first = embed_many(["alpha", "beta"])
            second = embed_many(["alpha", "beta"])
            self.assertEqual(first, second)
            self.assertEqual(client.return_value.embed.call_count, 1)
            self.assertEqual(client.return_value.embed.call_args.kwargs["input"], ["alpha", "beta"])

    def test_embedding_failure_does_not_replace_existing_vectors(self):
        from embeddings.embed_store import store_chunks
        with patch("embeddings.embed_store.get_collection") as collection, \
             patch("embeddings.embed_store.embed_many", side_effect=[[[1.0, 0.0]], RuntimeError("offline")]), \
             patch.dict(os.environ, {"EMBED_BATCH_SIZE": "1"}):
            with self.assertRaises(RuntimeError):
                store_chunks([{"id": "one", "text": "first", "metadata": {}},
                              {"id": "two", "text": "second", "metadata": {}}])
            collection.return_value.upsert.assert_not_called()

    def test_cpu_embeddings_do_not_require_ollama(self):
        from embeddings.embed_store import embed_many
        with patch("embeddings.embed_store.EMBED_PROVIDER", "fastembed"), \
             patch("embeddings.embed_store.cpu_model") as model, patch("ollama.Client") as ollama:
            from unittest.mock import Mock
            vector = Mock()
            vector.tolist.return_value = [0.1, 0.2, 0.3]
            model.return_value.embed.return_value = [vector]
            self.assertEqual(embed_many(["CPU embedding"]), [[0.1, 0.2, 0.3]])
            self.assertEqual(embed_many(["CPU embedding"]), [[0.1, 0.2, 0.3]])
            model.return_value.embed.assert_called_once()
            ollama.assert_not_called()

    def test_notes_only_subject_can_analyze_and_generate_practice(self):
        source_store.replace_pages("DBMS", "lecture_note", "notes.txt", [(1, "Normalization reduces redundancy")])
        topic = {"name": "Normalization", "summary": "Normalization reduces redundancy", "sources": [{"filename": "notes.txt", "page": 1}]}
        with patch("agents.analysis._extract_teaching_topics", return_value=[topic]):
            analysis = analyze_subject("DBMS")
        self.assertEqual(analysis["topics"][0]["num_years"], 0)
        self.assertEqual(analysis["questions"], [])
        question = {"question": "What is reduced?", "options": ["Redundancy", "Security", "Accuracy", "Integrity"],
                    "correct_answer": "Redundancy", "explanation": "Normalization reduces redundancy", "sources": ["notes.txt"], "question_type": "mcq"}
        with patch("backend.main.generate_questions_for_topic", return_value=[question]), TestClient(app) as client:
            response = client.post("/api/quizzes", json={"subject": "DBMS", "topic": "Normalization", "count": 1})
            self.assertEqual(response.status_code, 202)
            for _ in range(100):
                job = client.get(f"/api/jobs/{response.json()['id']}").json()
                if job["status"] not in {"queued", "running"}: break
                time.sleep(.01)
            self.assertEqual(job["status"], "completed")
            self.assertEqual(client.get("/api/quizzes/latest", params={"subject": "DBMS"}).json()["quiz_id"], job["result"]["quiz_id"])

    def test_resume_practice_preserves_first_answer_and_subject(self):
        question = {"question": "Q?", "options": ["A", "B", "C", "D"], "correct_answer": "B",
                    "explanation": "B is correct", "sources": ["notes.txt"], "question_type": "mcq"}
        quiz = save_quiz("DBMS", "Normalization", [question])
        save_quiz("Electrical", "Circuits", [question])
        answer_question(quiz["quiz_id"], 0, "A")
        retry = answer_question(quiz["quiz_id"], 0, "B")
        self.assertFalse(retry["correct"])
        self.assertEqual(retry["selected_answer"], "A")
        restored = latest_quiz("DBMS")
        self.assertEqual(restored["quiz_id"], quiz["quiz_id"])
        self.assertEqual(restored["attempts"], [{"question_index": 0, "correct": False, "answer": "A"}])
        self.assertIsNone(latest_quiz("No course"))

    def test_saved_pages_rebuild_new_index_once(self):
        from ingestion.pipeline import ensure_subject_index
        source_store.replace_pages("DBMS", "lecture_note", "notes.txt", [(1, "Normalization reduces redundancy")])
        with patch("ingestion.pipeline.get_collection") as collection, \
             patch("ingestion.pipeline.store_chunks") as store, patch("ingestion.pipeline.delete_source_vectors"):
            collection.return_value.get.return_value = {"ids": ["one"]}
            ensure_subject_index("DBMS")
            ensure_subject_index("DBMS")
            store.assert_called_once()
            source_store.replace_pages("DBMS", "lecture_note", "notes.txt", [(1, "Normalization reduces update anomalies")])
            ensure_subject_index("DBMS")
            self.assertEqual(store.call_count, 2)

    def test_filename_year_takes_priority_over_fallback(self):
        from ingestion.pipeline import ingest_file
        file = self.root / "paper_2024.txt"
        file.write_text("Explain normalization and update anomalies.")
        with patch("ingestion.pipeline.store_chunks", return_value=1), patch("ingestion.pipeline.delete_source_vectors"):
            ingest_file(file, "past_qp", subject="DBMS", year=2025)
        self.assertEqual(source_store.get_pages("DBMS")[0]["year"], 2024)

    def test_changing_exam_year_invalidates_analysis(self):
        source_store.replace_pages("DBMS", "past_qp", "paper.pdf", [(1, "Explain normalization")], 2025)
        save_analysis({"subject": "DBMS", "topics": []})
        with patch("backend.main.get_collection") as collection:
            collection.return_value.get.return_value = {"ids": ["existing"], "metadatas": [{"year": 2025}]}
            with TestClient(app) as client:
                response = client.patch("/api/library/year", json={"subject": "DBMS", "filename": "paper.pdf", "year": 2024})
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(client.get("/api/analysis", params={"subject": "DBMS"}).json())
        self.assertEqual(source_store.get_pages("DBMS")[0]["year"], 2024)
        collection.return_value.update.assert_called_once_with(ids=["existing"], metadatas=[{"year": 2024}])

    def test_subject_isolation(self):
        source_store.replace_pages("DBMS", "lecture_note", "module.pdf", [(1, "Database normal forms")])
        source_store.replace_pages("Electrical", "lecture_note", "module.pdf", [(1, "Electrical circuits")])
        with TestClient(app) as client:
            response = client.get("/api/pages", params={"subject": "DBMS", "filename": "module.pdf", "source_type": "lecture_note"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()[0]["text"], "Database normal forms")
            self.assertEqual(len(response.json()), 1)

    def test_question_batches_preserve_source_metadata(self):
        pages = [{"text": "Explain database normalization and redundancy.", "year": 2023, "filename": "db_2023.pdf", "page": 2},
                 {"text": "Describe ACID properties of database transactions.", "year": 2023, "filename": "db_2023.pdf", "page": 3}]
        with patch("agents.analysis._json_array", return_value=[
            {"source": 0, "question": "Explain database normalization and redundancy."},
            {"source": 1, "question": "Describe ACID properties of database transactions."},
            {"source": 5, "question": "Invented question that should be ignored."},
        ]) as model:
            output = _extract_paper_questions(pages)
        self.assertEqual(model.call_count, 1)
        self.assertEqual([(q["year"], q["page"]) for q in output], [(2023, 2), (2023, 3)])

    def test_analysis_reuse_skips_all_model_stages(self):
        source_store.replace_pages("DBMS", "lecture_note", "notes.pdf", [(1, "Normal forms reduce redundant data")])
        source_store.replace_pages("DBMS", "past_qp", "2023.pdf", [(1, "Explain normalization and its uses")], 2023)
        teaching = source_store.get_pages("DBMS", ("textbook", "lecture_note", "lecture_slide", "lecture_video"))
        papers = source_store.get_pages("DBMS", ("past_qp",))
        saved = {"subject": "DBMS", "fingerprint": source_store.corpus_fingerprint(teaching + papers),
                 "provider": "ollama", "model": "qwen2.5:7b", "analysis_version": 2, "topics": []}
        save_analysis(saved)
        with patch("agents.analysis._extract_teaching_topics") as extraction:
            self.assertEqual(analyze_subject("DBMS"), saved)
            extraction.assert_not_called()

    def test_repeat_groups_reject_unknown_ids_and_cross_topic_pairs(self):
        questions = [{"id": "a", "year": 2023, "topic": "Normalization"},
                     {"id": "b", "year": 2024, "topic": "Normalization"},
                     {"id": "c", "year": 2024, "topic": "Transactions"}]
        topics = [{"name": "Normalization", "summary": "Normal forms"}, {"name": "Transactions", "summary": "ACID"}]
        with patch("agents.analysis._json_array", return_value=[
            {"topic": "Normalization", "ids": ["a", "b", {}, "missing"], "reason": "Same task"},
            {"topic": "Normalization", "ids": ["a", "c"], "reason": "Incorrect group"},
        ]):
            groups = _find_repeats(questions, topics)
        self.assertEqual(len(groups), 1)
        self.assertEqual([q["id"] for q in groups[0]["questions"]], ["a", "b"])

    def test_upload_job_keeps_health_responsive(self):
        source_store.create_subject("DBMS")
        started, release = Event(), Event()
        def ingest(*args, **kwargs):
            started.set(); release.wait(3); return 2
        with patch("backend.main.ingest_file", side_effect=ingest):
            with TestClient(app) as client:
                response = client.post("/api/uploads", data={"subject": "DBMS", "source_type": "lecture_note"}, files=[("files", ("notes.txt", b"Normalize tables", "text/plain"))])
                self.assertEqual(response.status_code, 202)
                self.assertTrue(started.wait(2))
                self.assertEqual(client.get("/api/health").status_code, 200)
                id_ = response.json()["id"]
                release.set()
                for _ in range(100):
                    job = client.get(f"/api/jobs/{id_}").json()
                    if job["status"] == "completed": break
                    time.sleep(.01)
                self.assertEqual(job["result"]["files"][0]["chunks"], 2)

    def test_upload_validation_and_public_demo(self):
        source_store.create_subject("DBMS")
        with TestClient(app) as client:
            response = client.post("/api/uploads", data={"subject": "DBMS", "source_type": "past_qp"}, files=[("files", ("paper.pdf", b"pdf", "application/pdf"))])
            self.assertEqual(response.status_code, 422)
            with patch("backend.main.DEMO", True):
                self.assertEqual(client.post("/api/subjects", json={"name": "private"}).status_code, 403)

    def test_answers_are_checked_server_side_and_count_once(self):
        quiz = save_quiz("DBMS", "Normalization", [{"question": "Q?", "options": ["A", "B", "C", "D"],
            "correct_answer": "B", "explanation": "B is correct", "sources": ["notes.pdf"], "question_type": "mcq"}])
        result = answer_question(quiz["quiz_id"], 0, "A", True)
        self.assertFalse(result["correct"])
        answer_question(quiz["quiz_id"], 0, "B")
        self.assertEqual(progress("DBMS"), [{"topic": "Normalization", "answered": 1, "correct": 0}])


if __name__ == "__main__":
    unittest.main()
