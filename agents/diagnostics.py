"""Non-secret local model status and application trace helpers."""

import json
import os
from pathlib import Path
from urllib.request import urlopen

from agents.llm import LOG_PATH, TRACE_PATH
from agents.llm import provider_settings


def model_status() -> dict:
    provider, model = provider_settings()
    if provider == "groq":
        return {"provider": "Groq", "model": model, "key_configured": bool(os.getenv("GROQ_API_KEY")),
                "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")}
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    result = {"provider": "Ollama", "host": host,
              "chat_model": model,
              "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")}
    try:
        with urlopen(host + "/api/tags", timeout=3) as response:
            payload = json.load(response)
        result["reachable"] = True
        result["installed_models"] = [m.get("name") for m in payload.get("models", [])]
        try:
            with urlopen(host + "/api/ps", timeout=3) as response:
                result["loaded_models"] = json.load(response).get("models", [])
        except Exception:
            result["loaded_models"] = []
    except Exception as exc:
        result["reachable"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def recent_calls(limit: int = 30) -> str:
    path = Path(LOG_PATH)
    if not path.exists():
        return "No application LLM calls recorded yet."
    with path.open(encoding="utf-8", errors="replace") as stream:
        lines = stream.readlines()
    return "".join(lines[-limit:])


def latest_trace() -> dict | None:
    if not TRACE_PATH.exists():
        return None
    with TRACE_PATH.open(encoding="utf-8", errors="replace") as stream:
        last = None
        for line in stream:
            last = line
    return json.loads(last) if last else None
