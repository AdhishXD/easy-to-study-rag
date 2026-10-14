# Easy to Study

A course workspace that connects lecture notes, textbooks, recordings, and past exam papers. Find recurring exam topics, read their teaching context, and practice with MCQs or 2, 3, and 5 mark questions.

Built with **React + TypeScript + Tailwind**, **FastAPI**, local **Chroma**, and **SQLite**. Generation uses Ollama locally or a free Groq account. No paid service is required to run it.

## Run locally

Use Python 3.12 and Node.js 22 or newer. Create a fresh environment on a new machine:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-local.txt
# Copy only if you do not already have .env:
Copy-Item .env.example .env
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. API documentation is at **http://127.0.0.1:8000/docs**. Vite forwards `/api` requests to FastAPI. On Linux/macOS, activate the environment with `source .venv/bin/activate`.

For a single service, run `npm run build` in `frontend/`, then start FastAPI. It serves the production frontend at **http://127.0.0.1:8000**. Build before starting the backend. Use one Uvicorn worker: the background queue belongs to one process.

## Choose inference

`LLM_PROVIDER=auto` uses Groq if `GROQ_API_KEY` is configured; otherwise it uses Ollama. Set `LLM_PROVIDER=ollama` to keep generation local. Restart the backend after changing `.env`.

To use free Groq inference, add these to the ignored `.env` file:

```dotenv
LLM_PROVIDER=auto
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

The key stays on the backend. Retrieved teaching text and analysis passages are sent to Groq when that provider is selected. Free quotas still apply. Rate limits are retried with a bounded wait; the UI reports failures instead of inventing results. Local embeddings continue to use Ollama, independently of the chat provider.

The local default preserves the existing `qwen2.5:7b` installation. For a lighter candidate, pull `qwen3:4b`, set `OLLAMA_LLM_MODEL=qwen3:4b`, and compare question quality on the same course pages. Thinking is disabled by default for models that support that setting. A model name alone does not guarantee faster inference on your hardware.

## Study workflow

1. Create one subject per course.
2. Add notes, textbooks, recordings, and dated past papers. Documents support PDF, PPTX with speaker notes, PPT, DOCX, TXT, and MD. Recordings support MP4, MP3, WAV, M4A, and WEBM.
3. Inspect the saved page text in **Materials**. Legacy PPT needs LibreOffice; scanned or handwritten PDFs need OCR. Formats without a loader are rejected clearly.
4. Check exam years. Years in filenames take priority over the fallback year. Existing paper years can be corrected in the library.
5. Analyze the course. Jobs run in the background, show progress, and can be cancelled between processing steps. A current model request or file commit may finish before cancellation takes effect.
6. Explore topics, complete past-paper questions, and candidate repeats with original source text.
7. Generate a practice set. MCQs are checked on the backend; written answers use self-assessment. Progress shows topics that need another look.

The materials library can remove incorrectly assigned files. Removal clears that course's saved analysis. Subjects isolate course material; this is a local workspace, not a multi-user account system.

## Performance and grounding

- Stable batches cover all extracted teaching pages and past-paper text. Text is not silently sampled.
- Analysis responses are cached by provider, model, prompt, and generation settings. Completed analysis also records a corpus fingerprint and algorithm version.
- File fingerprints skip unchanged parsing, transcription, and indexing. They include processing settings so changing the index or transcription settings triggers new work.
- Embeddings use batched requests and a persistent text/model cache. All vectors for a source are prepared before replacing its stored passages; obsolete chunks are removed after replacement.
- One bounded worker prevents concurrent local model jobs from competing for memory. HTTP requests and navigation remain responsive.
- Quiz retrieval expands matched chunks with surrounding page context. Sources come from stored retrieval metadata. JSON and source references are validated; invalid output is skipped.
- Recurrence counts distinct years. It is evidence for prioritizing study, not a prediction of the next exam. Candidate repeats and generated answers still need human review.

See [the performance audit](docs/performance.md) for measured work sizes, fixes, and remaining limits, and [the UI design notes](docs/design.md) for interface decisions.

## Diagnostics and checks

**Settings & activity** shows jobs, elapsed time, cache hits, model status, and request timing. Ollama status includes loaded model sizes and VRAM usage when available. App logs are in `db/llm_calls.log`. Set `LOG_LLM_CONTENT=1` to save local prompts/responses in `db/llm_trace.jsonl`; these contain course text and are ignored by Git.

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/audit_performance.py --output db/performance-audit.json
cd frontend
npm run build
npm run format:check
```

Tests use isolated temporary stores and mocked inference. They do not send course data to a model provider. The audit inspects saved course sizes and times read endpoints without running inference.

## Hosting, next

The frontend builds to static assets and FastAPI can serve them from the same origin. Deployment has not been performed yet. A free demo should use a curated, publishable dataset and `MODE=demo`; install `requirements-demo.txt` for its small CPU embedding model. Public uploads and file changes are disabled in demo mode.

Before exposing a private workspace, set `APP_ACCESS_TOKEN` and restrict `CORS_ORIGINS`. The frontend accepts that token for the current browser session. Free hosting often has sleep, memory, and ephemeral-disk limits; persistent private uploads need storage and user isolation beyond this local version.

## Project layout

```text
frontend/          React components, Tailwind styles, typed API client
backend/           FastAPI routes, background jobs, practice history
agents/            Course analysis, grounded quizzes, inference adapter/cache
ingestion/         Loaders, chunking, fingerprints, full-page source storage
embeddings/        Batched embeddings and Chroma indexing/retrieval
tests/             Isolated backend and grounding regressions
scripts/           Performance audit
docs/              Design decisions and performance findings
db/                Private indexes, SQLite files, cache, and logs (ignored)
sample_data/       Private study files, lecture_videos/, past_qps/ (ignored)
```

The original Streamlit implementation and checkpoint scripts are preserved on GitHub at `f3c98e1`. They have been removed from the current codebase; the supported interface is the React application and automated checks live in `tests/`.
