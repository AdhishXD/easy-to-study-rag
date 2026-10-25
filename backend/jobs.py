"""One bounded worker avoids overlapping requests thrashing a local GPU/CPU."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from threading import Lock
import time
from uuid import uuid4

from agents.cache import connect
from agents.runtime import RunContext, JobCancelled, current_run


class JobManager:
    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="study-worker")
        self.lock = Lock()
        self.contexts = {}
        with closing(connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, subject TEXT, kind TEXT, status TEXT,
                progress REAL, message TEXT, result TEXT, error TEXT,
                created REAL, updated REAL, elapsed REAL, metrics TEXT)""")
            db.execute("UPDATE jobs SET status='failed', error='Server restarted; please retry' WHERE status IN ('queued','running')")

    def get(self, id_: str):
        with closing(connect()) as db:
            db.row_factory = __import__('sqlite3').Row
            row = db.execute("SELECT * FROM jobs WHERE id=?", (id_,)).fetchone()
        if not row:
            return None
        job = dict(row)
        job["result"] = json.loads(job["result"]) if job["result"] else None
        job["metrics"] = json.loads(job["metrics"]) if job["metrics"] else {}
        return job

    def list(self, subject: str | None = None):
        with closing(connect()) as db:
            db.row_factory = __import__('sqlite3').Row
            query = "SELECT id,subject,kind,status,progress,message,error,created,updated,elapsed,metrics FROM jobs" + (" WHERE subject=?" if subject else "") + " ORDER BY created DESC LIMIT 20"
            rows = db.execute(query, (subject,) if subject else ()).fetchall()
        jobs = [dict(row) for row in rows]
        for job in jobs:
            job["metrics"] = json.loads(job["metrics"]) if job["metrics"] else {}
        return jobs

    def update(self, id_: str, **fields):
        fields["updated"] = time.time()
        with closing(connect()) as db, db:
            db.execute(f"UPDATE jobs SET {','.join(k+'=?' for k in fields)} WHERE id=?", (*fields.values(), id_))

    def submit(self, subject: str, kind: str, task, cleanup=None):
        with self.lock:
            active = [j for j in self.list() if j["status"] in {"queued", "running"}]
            if len(active) >= 8:
                raise ValueError("The processing queue is full. Wait for a job to finish.")
            if any(j["subject"] == subject and j["kind"] == kind for j in active):
                raise ValueError(f"{kind.capitalize()} is already queued for this subject")
            id_ = uuid4().hex
            now = time.time()
            with closing(connect()) as db, db:
                db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                           (id_, subject, kind, "queued", 0, "Waiting for the current task", None, None, now, now, 0, "{}"))
            context = RunContext(notify=lambda message, progress: self.update(id_, message=message, progress=progress))
            self.contexts[id_] = context
            # Return a stable queued snapshot even when a cache hit finishes
            # before the HTTP response is sent. Clients can then collect results.
            submitted = self.get(id_)
            self.pool.submit(self._run, id_, task, context, cleanup)
        return submitted

    def _run(self, id_, task, context, cleanup):
        start = time.monotonic()
        token = current_run.set(context)
        try:
            if context.cancelled.is_set():
                raise JobCancelled()
            self.update(id_, status="running", message="Starting…")
            result = task()
            if context.cancelled.is_set():
                raise JobCancelled()
            self.update(id_, status="completed", progress=1, message="Ready", result=json.dumps(result, ensure_ascii=False))
        except JobCancelled:
            self.update(id_, status="cancelled", message="Cancelled")
        except Exception as exc:
            from agents.llm import logger
            logger.exception("job_failed id=%s", id_)
            self.update(id_, status="failed", message="Could not finish", error=str(exc)[:500])
        finally:
            self.update(id_, elapsed=round(time.monotonic() - start, 2), metrics=json.dumps({
                "llm_calls": context.calls, "cache_hits": context.cache_hits, "model_seconds": round(context.model_seconds, 2)}))
            current_run.reset(token)
            if cleanup:
                cleanup()
            with self.lock:
                self.contexts.pop(id_, None)

    def cancel(self, id_):
        with self.lock:
            context = self.contexts.get(id_)
            if context:
                context.cancelled.set()
                self.update(id_, message="Cancelling after the current model request…")
        return self.get(id_)

    def close(self):
        for context in list(self.contexts.values()):
            context.cancelled.set()
        self.pool.shutdown(wait=False, cancel_futures=False)
