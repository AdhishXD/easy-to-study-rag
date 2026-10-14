"""Free inference with bounded output, timing and reusable analysis."""

import json
import hashlib
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from dotenv import load_dotenv
from agents import cache as response_cache
from agents.runtime import check_cancelled, current_run

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


def provider_settings() -> tuple[str, str]:
    provider = os.getenv("LLM_PROVIDER", "auto").lower()
    if provider == "auto":
        provider = "groq" if os.getenv("GROQ_API_KEY") else "ollama"
    if provider not in {"groq", "ollama"}:
        raise ValueError("LLM_PROVIDER must be auto, groq or ollama")
    model = (os.getenv("GROQ_MODEL", "openai/gpt-oss-20b") if provider == "groq"
             else os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b"))
    return provider, model


def chat(prompt: str, *, cache: bool = True, max_tokens: int = 1800) -> str:
    check_cancelled()
    provider, model = provider_settings()
    settings = {"version": 2, "provider": provider, "model": model, "prompt": prompt,
                "temperature": 0.2, "max_tokens": max_tokens,
                "think": os.getenv("OLLAMA_THINK", "false"),
                "context": os.getenv("OLLAMA_NUM_CTX", "8192")}
    key = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    context = current_run.get()
    if cache:
        saved = response_cache.get("chat", key)
        if saved is not None:
            if context:
                context.cache_hits += 1
            logger.info("provider=%s model=%s cache=hit prompt_chars=%d", provider, model, len(prompt))
            return saved
    start = time.monotonic()
    metrics = {}
    try:
        if provider == "ollama":
            import ollama
            client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"), timeout=180)
            kwargs = {}
            if model.startswith(("qwen3", "gemma4")):
                kwargs["think"] = os.getenv("OLLAMA_THINK", "false").lower() == "true"
            response = client.chat(
                model=model, messages=[{"role": "user", "content": prompt}],
                format={"type": "array", "items": {}},
                options={"temperature": 0.2, "num_predict": max_tokens,
                         "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192"))},
                keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "10m"), **kwargs)
            output = response["message"]["content"].strip()
            metrics = {name: response.get(name) for name in
                       ("load_duration", "prompt_eval_duration", "eval_duration", "prompt_eval_count", "eval_count")}
        else:
            key_value = os.getenv("GROQ_API_KEY")
            if not key_value:
                raise RuntimeError("Add GROQ_API_KEY to .env, then restart the backend")
            payload = {
                "model": model, "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2, "max_completion_tokens": max_tokens,
            }
            if "gpt-oss" in model:
                payload["reasoning_effort"] = "low"
            request = Request(
                "https://api.groq.com/openai/v1/chat/completions", data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {key_value}", "Content-Type": "application/json"},
            )
            for attempt in range(3):
                check_cancelled()
                try:
                    with urlopen(request, timeout=90) as response:
                        data = json.load(response)
                    break
                except HTTPError as exc:
                    if exc.code != 429 or attempt == 2:
                        raise RuntimeError(f"Groq returned HTTP {exc.code}; check your free quota/model in Diagnostics") from None
                    try:
                        delay = min(30, max(1, float(exc.headers.get("retry-after", "5"))))
                    except ValueError:
                        delay = 5
                    if context:
                        context.cancelled.wait(delay)
                    else:
                        time.sleep(delay)
            output = data["choices"][0]["message"]["content"].strip()
            metrics = data.get("usage", {})
        check_cancelled()
        duration = time.monotonic() - start
        if context:
            context.calls += 1
            context.model_seconds += duration
        logger.info("provider=%s model=%s cache=miss prompt_chars=%d response_chars=%d duration_s=%.2f metrics=%s",
                    provider, model, len(prompt), len(output), duration, json.dumps(metrics))
        if cache:
            cleaned = output
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            try:
                if isinstance(json.loads(cleaned), list):
                    response_cache.put("chat", key, output)
            except json.JSONDecodeError:
                pass
        if provider == "ollama" and os.getenv("LOG_LLM_CONTENT") == "1":
            TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with TRACE_PATH.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"model": model, "prompt": prompt, "response": output},
                                        ensure_ascii=False) + "\n")
        return output
    except Exception as exc:
        logger.error("provider=%s model=%s prompt_chars=%d duration_s=%.2f error=%s",
                     provider, model, len(prompt), time.monotonic() - start, type(exc).__name__)
        raise
