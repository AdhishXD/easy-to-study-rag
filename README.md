# Exam Prep Synthesizer

Index a course's lecture notes, slides, textbooks, recordings, and past papers. The app keeps full extracted pages for LLM topic and question analysis, and overlapping chunks for retrieval-grounded quizzes. It supports MCQs and 2, 3, and 5 mark answers.

## Local setup

Use Python 3.12 in a fresh virtual environment. Install `requirements-local.txt`, copy `.env.example` to `.env`, and pull the Ollama models:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-local.txt
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
streamlit run app.py
```

Choose a subject/course name when indexing. The Add material tab accepts lecture notes and textbooks as PDF, PPTX (speaker notes included), legacy PPT, DOCX, TXT, or MD, plus common video/audio formats. Legacy PPT conversion needs LibreOffice installed locally. Past papers currently accept PDF and need a four-digit year in the filename, a `-ese-25`/`-makeup-25` suffix, or an explicit fallback year in the UI. Scanned PDFs need OCR before ingestion. Local video transcription uses faster-whisper on CPU.

After indexing, inspect the extracted page text in the Study tab, then click **Analyze teaching material and past papers**. Re-index files that were uploaded before full-page storage was added. Analysis can take several minutes with a local model.

The Diagnostics tab checks whether Ollama responds and whether the configured chat and embedding models are installed. On Windows, Ollama's own server events are in `%LOCALAPPDATA%\Ollama\server.log`. Application call timing and errors are in `db/llm_calls.log`. Set `LOG_LLM_CONTENT=1` in `.env` to save local prompts and responses in the ignored `db/llm_trace.jsonl`; it contains your study text. Hidden model reasoning is not exposed by these logs.

The repo's old `venv/` was created against a Python install that is no longer present; create a fresh environment. Stored vectors live in `db/chroma_store/` and are ignored by Git.

## Free public demo

The current hosted target is [Streamlit Community Cloud](https://streamlit.io/cloud), using a fixed **synthetic DBMS dataset**. In the Cloud deployment settings, choose Python 3.12, set the entry point to `app.py`, and add root-level secrets:

```toml
MODE = "demo"
GROQ_API_KEY = "your-free-tier-Groq-key"
GROQ_MODEL = "openai/gpt-oss-20b"
```

The demo uses a small CPU sentence-transformer embedding model and Groq for generation. Its sample Chroma index is recreated when the app starts; the local mode uses Ollama for both embeddings and generation. Public uploads are disabled so visitors cannot mix private course material into a shared ephemeral index. To replace the synthetic material, update `demo_seed.py` with material you have permission to publish.

## Design notes and limits

- Chunks preserve source type, filename, page/slide/segment, subject, and exam year where applicable. Chunking uses overlapping, boundary-aware windows and deterministic IDs. Full extracted pages live in `db/source_pages.sqlite3`.
- The LLM extracts topics from every teaching page, extracts complete questions from past-paper pages, maps questions to taught topics, and groups possible repeats across years. Years and source locations come from ingestion metadata, not model claims. These groups are candidates, not verified duplicates.
- The app rejects malformed JSON and weakly source-matched extracted text. Bad PDF extraction still requires OCR or manual source cleanup; inspect the saved text before trusting analysis.
- The model only sees retrieved teaching passages. The app validates its JSON and attaches source labels from retrieval. Citation labels show which passages were supplied; they do not independently prove every sentence of a generated answer.
- Quiz quality on real course material still needs evaluation. Image-only pages, handwritten notes, and tables can parse poorly without additional extraction/OCR.
- CrewAI orchestration and SQLite performance tracking are planned. The present app calls the ingestion, analysis, and quiz modules directly.

## Main modules

- `ingestion/pipeline.py`: file routing and ingestion
- `embeddings/embed_store.py`: local/demo embeddings and Chroma queries
- `agents/analysis.py`: full-page topic and question analysis
- `agents/diagnostics.py`: model status and call trace
- `agents/quiz_agent.py`: grounded question generation and validation
- `app.py`: Streamlit interface

The `test_day2.py` through `test_day5.py` scripts are optional subject-aware checkpoints.

Local study files belong in the ignored sample_data/ folder, with lecture_videos/ and past_qps/ subfolders as needed.
