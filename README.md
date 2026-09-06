# Exam Prep Agent

Multi-agent RAG system that ingests lecture slides, textbooks, past year
question papers, and lecture videos, analyzes exam topic frequency
patterns, and generates practice quizzes weighted toward what actually
shows up on exams.

Built entirely with free/local tools: Ollama, ChromaDB, CrewAI.

## Day 1 Setup

1. **Install Ollama** from https://ollama.com

2. **Pull the models** (choose based on your RAM):
   ```bash
   ollama pull qwen2.5:7b        # needs ~16GB RAM
   # OR
   ollama pull llama3.2:3b       # lighter, works on ~8GB RAM

   ollama pull nomic-embed-text  # embedding model, small
   ```

3. **Create a virtual environment and install dependencies**:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux

   pip install -r requirements.txt
   ```

4. **Copy the env file**:
   ```bash
   copy .env.example .env       # Windows
   # cp .env.example .env       # macOS/Linux
   ```
   Edit `.env` if your model names differ from the defaults.

5. **Run the checkpoint script**:
   ```bash
   python test_setup.py
   ```
   You should see `ALL CHECKS PASSED` at the end. If Ollama's chat test
   fails, make sure Ollama is running (`ollama serve` or just open the
   Ollama app) and that you've pulled the model named in `.env`.

## Project structure

```
exam-prep-agent/
├── ingestion/       # PDF, PPTX, past QP, video loaders + chunker
├── embeddings/      # ChromaDB storage logic
├── agents/          # Ingestor, Pattern, Quiz Master agents
├── db/              # SQLite performance tracking (later)
├── test_setup.py    # Day 1 environment checkpoint
├── requirements.txt
└── .env.example
```

## Roadmap

- [x] Day 1 — Environment setup
- [ ] Day 2 — PDF + PPTX ingestion
- [ ] Day 3 — Past QPs + lecture video ingestion
- [ ] Day 4 — Pattern Agent (topic frequency analysis)
- [ ] Day 5 — Quiz Master Agent
- [ ] Day 6 — CrewAI orchestration
- [ ] Day 7 — Dual-mode LLM wrapper + deploy to Hugging Face Spaces
