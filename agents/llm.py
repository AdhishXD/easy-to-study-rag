"""Small chat adapter for local Ollama and a hosted Groq demo."""

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()

LOG_PATH = Path(os.getenv("APP_LOG_PATH", "./db/llm_calls.log"))
TRACE_PATH = Path(os.getenv("LLM_TRACE_PATH", "./db/llm_trace.jsonl"))
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("exam_prep.llm")
if not logger.handlers:
    handler = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def chat(prompt: str) -> str:
    mode = os.getenv("MODE", "local").lower()
    model = (os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b") if mode == "local"
             else os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"))
    start = time.monotonic()
    try:
        if mode == "local":
            import ollama
            response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
            output = response["message"]["content"].strip()
        elif mode == "demo":
            key = os.getenv("GROQ_API_KEY")
            if not key:
                raise RuntimeError("GROQ_API_KEY is required in demo mode")
            payload = json.dumps({
                "model": model, "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            }).encode("utf-8")
            request = Request(
                "https://api.groq.com/openai/v1/chat/completions", data=payload,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
            with urlopen(request, timeout=90) as response:
                data = json.load(response)
            output = data["choices"][0]["message"]["content"].strip()
        else:
            raise ValueError("MODE must be local or demo")
        logger.info("provider=%s model=%s prompt_chars=%d response_chars=%d duration_s=%.2f",
                    mode, model, len(prompt), len(output), time.monotonic() - start)
        if mode == "local" and os.getenv("LOG_LLM_CONTENT") == "1":
            TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with TRACE_PATH.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"model": model, "prompt": prompt, "response": output},
                                        ensure_ascii=False) + "\n")
        return output
    except Exception as exc:
        logger.error("provider=%s model=%s prompt_chars=%d duration_s=%.2f error=%s",
                     mode, model, len(prompt), time.monotonic() - start, type(exc).__name__)
        raise
