"""Run with: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"""

from contextlib import asynccontextmanager
import os
from pathlib import Path
import tempfile
from typing import Literal

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from agents.analysis import analyze_subject, get_analysis
from agents.diagnostics import model_status, recent_calls, latest_trace
from agents.llm import provider_settings
from agents.quiz_agent import generate_questions_for_topic
from agents.runtime import report, JobCancelled, current_run
from backend.jobs import JobManager
from backend.practice import save_quiz, answer_question, progress, latest_quiz
from ingestion.pipeline import ingest_file, SOURCE_TYPES, extract_year
from ingestion.document_loader import DOCUMENT_EXTENSIONS
from ingestion.source_store import list_subjects, create_subject, list_files, get_pages, delete_source_pages
from ingestion.source_store import get_source_pages, page_numbers, set_source_year
from embeddings.embed_store import delete_source_vectors, get_collection, embedding_identity, EMBED_PROVIDER

DEMO = os.getenv("MODE", "local").lower() == "demo"
security = HTTPBearer(auto_error=False)


def access(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    token = os.getenv("APP_ACCESS_TOKEN")
    if token:
        import secrets
        if not credentials or not secrets.compare_digest(credentials.credentials, token):
            raise HTTPException(401, "Enter your workspace access token")


@asynccontextmanager
async def lifespan(app):
    app.state.jobs = JobManager()
    if DEMO:
        from demo_seed import seed_demo
        seed_demo()
    yield
    app.state.jobs.close()


app = FastAPI(title="Easy to Study", version="0.2.0", lifespan=lifespan,
              dependencies=[Depends(access)])
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
                   allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type", "Authorization"])
app.add_middleware(GZipMiddleware, minimum_size=1024)


def writable():
    if DEMO:
        raise HTTPException(403, "The public demo uses a fixed sample course. Run locally to upload your materials.")


def subject_exists(name):
    if name not in {s["name"] for s in list_subjects()}:
        raise HTTPException(404, "Subject not found")


class SubjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class AnalysisInput(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    force: bool = False


class QuizInput(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    topic: str = Field(min_length=1, max_length=100)
    question_type: Literal["mcq", "2_mark", "3_mark", "5_mark"] = "mcq"
    count: int = Field(default=3, ge=1, le=5)


class AnswerInput(BaseModel):
    quiz_id: str
    question_index: int = Field(ge=0)
    answer: str = ""
    self_correct: bool | None = None


class YearInput(BaseModel):
    subject: str
    filename: str
    year: int = Field(ge=1900, le=2100)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    provider, model = provider_settings()
    return {"demo": DEMO, "provider": provider, "model": model, "uploads_enabled": not DEMO,
            "embedding_provider": EMBED_PROVIDER, "embedding_model": embedding_identity(),
            "max_upload_mb": int(os.getenv("MAX_UPLOAD_MB", "100"))}


@app.get("/api/subjects")
def subjects():
    return list_subjects()


@app.post("/api/subjects", status_code=201)
def add_subject(body: SubjectInput):
    writable()
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Enter a subject name")
    create_subject(name)
    return {"name": name}


@app.get("/api/library")
def library(subject: str):
    subject_exists(subject)
    return list_files(subject)


@app.get("/api/pages")
def pages(subject: str, filename: str, source_type: str, page: int | None = None):
    subject_exists(subject)
    return get_source_pages(subject, source_type, filename, page)


@app.get("/api/page-numbers")
def source_numbers(subject: str, filename: str, source_type: str):
    subject_exists(subject)
    return page_numbers(subject, source_type, filename)


@app.delete("/api/library")
def delete_file(subject: str, filename: str, source_type: str):
    writable()
    subject_exists(subject)
    if any(j["status"] in {"running", "queued"} and j["subject"] == subject for j in app.state.jobs.list()):
        raise HTTPException(409, "Cancel or finish this subject's processing before removing files")
    delete_source_vectors(subject, source_type, filename)
    delete_source_pages(subject, source_type, filename)
    return {"removed": filename}


@app.get("/api/analysis")
def analysis(subject: str):
    subject_exists(subject)
    return get_analysis(subject)


@app.patch("/api/library/year")
def update_year(body: YearInput):
    writable()
    subject_exists(body.subject)
    if any(j["status"] in {"running", "queued"} and j["subject"] == body.subject for j in app.state.jobs.list()):
        raise HTTPException(409, "Finish or cancel processing before changing the exam year")
    if not any(m["filename"] == body.filename and m["source_type"] == "past_qp" for m in list_files(body.subject)):
        raise HTTPException(404, "Past paper not found")
    collection = get_collection()
    records = collection.get(where={"$and": [{"subject": body.subject}, {"source_type": "past_qp"}, {"filename": body.filename}]}, include=["metadatas"])
    if records["ids"]:
        collection.update(ids=records["ids"], metadatas=[{**m, "year": body.year} for m in records["metadatas"]])
    set_source_year(body.subject, body.filename, body.year)
    return {"year": body.year}


@app.post("/api/analysis", status_code=202)
def start_analysis(body: AnalysisInput):
    subject_exists(body.subject)
    try:
        return app.state.jobs.submit(body.subject, "analysis", lambda: analyze_subject(body.subject, force=body.force))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@app.post("/api/uploads", status_code=202)
def upload_files(subject: str = Form(...), source_type: str = Form(...), year: int = Form(0),
                 files: list[UploadFile] = File(...)):
    writable()
    subject_exists(subject)
    if source_type not in SOURCE_TYPES or not files or len(files) > 20:
        raise HTTPException(422, "Choose a material type and between 1 and 20 files")
    directory = tempfile.TemporaryDirectory(prefix="exam-upload-")
    entries = []
    try:
        total = 0
        max_bytes = int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024
        names = set()
        for file in files:
            name = Path((file.filename or "upload").replace("\\", "/")).name
            if not name or name in {".", ".."} or name in names:
                raise HTTPException(422, "Each uploaded file needs a unique filename")
            names.add(name)
            extension = Path(name).suffix.lower()
            allowed = {".mp4", ".mp3", ".wav", ".m4a", ".webm"} if source_type == "lecture_video" else DOCUMENT_EXTENSIONS
            if extension not in allowed:
                raise HTTPException(422, f"Unsupported format: {extension}")
            if source_type == "past_qp" and not (extract_year(name) or 1900 <= year <= 2100):
                raise HTTPException(422, f"Set an exam year for {name}")
            path = Path(directory.name) / name
            with path.open("wb") as stream:
                while data := file.file.read(1024 * 1024):
                    total += len(data)
                    if total > max_bytes:
                        raise HTTPException(413, f"This upload exceeds {max_bytes // 1024 // 1024} MB. Use a smaller batch.")
                    stream.write(data)
            entries.append(path)
        def process():
            results = []
            for index, path in enumerate(entries):
                context = current_run.get()
                notify = context.notify if context else None
                if context:
                    context.notify = lambda message, value, i=index: notify(f"File {i + 1}/{len(entries)} · {message}", (i + value) / len(entries))
                try:
                    report(path.name, 0)
                    count = ingest_file(path, source_type, subject=subject, year=year or None)
                    results.append({"filename": path.name, "chunks": count, "status": "indexed"})
                except JobCancelled:
                    raise
                except Exception as exc:
                    results.append({"filename": path.name, "status": "failed", "error": str(exc)[:500]})
                finally:
                    if context:
                        context.notify = notify
            return {"files": results}
        try:
            return app.state.jobs.submit(subject, "upload", process, cleanup=directory.cleanup)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
    except Exception:
        directory.cleanup()
        raise
    finally:
        for file in files:
            file.file.close()


@app.get("/api/quizzes/latest")
def resume_quiz(subject: str):
    subject_exists(subject)
    return latest_quiz(subject)


@app.post("/api/quizzes", status_code=202)
def quiz(body: QuizInput):
    subject_exists(body.subject)
    analysis = get_analysis(body.subject)
    if not analysis or body.topic not in {t["name"] for t in analysis["topics"]}:
        raise HTTPException(422, "Choose a topic from your course analysis")
    def generate():
        report("Finding relevant teaching passages", 0.1)
        questions = generate_questions_for_topic(body.topic, body.count, body.question_type, body.subject)
        if not questions:
            raise ValueError("The model returned no valid grounded questions. Try a topic with more teaching context.")
        return save_quiz(body.subject, body.topic, questions)
    try:
        return app.state.jobs.submit(body.subject, "quiz", generate)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@app.post("/api/attempts")
def answer(body: AnswerInput):
    try:
        return answer_question(body.quiz_id, body.question_index, body.answer, body.self_correct)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.get("/api/progress")
def performance(subject: str):
    subject_exists(subject)
    return progress(subject)


@app.get("/api/jobs")
def jobs(subject: str | None = None):
    return app.state.jobs.list(subject)


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    value = app.state.jobs.get(job_id)
    if not value:
        raise HTTPException(404, "Job not found")
    return value


@app.post("/api/jobs/{job_id}/cancel")
def cancel(job_id: str):
    value = app.state.jobs.cancel(job_id)
    if not value:
        raise HTTPException(404, "Job not found")
    return value


@app.get("/api/diagnostics")
def diagnostics():
    value = {"model": model_status(), "recent_calls": recent_calls()}
    if not DEMO:
        value["trace"] = latest_trace()
    return value


# A production build can be served with the API from a single free web service.
frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
