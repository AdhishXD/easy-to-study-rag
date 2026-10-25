"""Retain one PDF per content hash, with subject/source references in SQLite."""

from contextlib import closing
import hashlib
import os
from pathlib import Path
import re
import tempfile
from threading import RLock

from ingestion.source_store import _connect

_lock = RLock()


def _root() -> Path:
    return Path(os.getenv("ORIGINALS_PATH", "./db/originals")).resolve()


def _path(digest: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Invalid original document identifier")
    root = _root()
    path = (root / f"{digest}.pdf").resolve()
    if path.parent != root:
        raise ValueError("Original document path escapes storage")
    return path


def _db():
    db = _connect()
    db.execute("""CREATE TABLE IF NOT EXISTS originals (
        subject TEXT, source_type TEXT, filename TEXT, digest TEXT NOT NULL, size INTEGER NOT NULL,
        PRIMARY KEY(subject, source_type, filename))""")
    return db


def _discard_unreferenced(db, digest: str | None):
    if digest and not db.execute("SELECT 1 FROM originals WHERE digest=? LIMIT 1", (digest,)).fetchone():
        _path(digest).unlink(missing_ok=True)


def save_original(path: Path, subject: str, kind: str) -> None:
    """Call after successful ingestion, including the unchanged-file fast path."""
    if path.suffix.lower() != ".pdf":
        return
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    key = digest.hexdigest()
    target = _path(key)
    with _lock, closing(_db()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute("SELECT digest FROM originals WHERE subject=? AND source_type=? AND filename=?",
                              (subject, kind, path.name)).fetchone()
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".tmp", delete=False) as output, path.open("rb") as source:
                    temporary = Path(output.name)
                    for data in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(data)
                temporary.replace(target)
            finally:
                if temporary:
                    temporary.unlink(missing_ok=True)
        db.execute("INSERT OR REPLACE INTO originals VALUES(?,?,?,?,?)",
                   (subject, kind, path.name, key, target.stat().st_size))
        if previous and previous[0] != key:
            _discard_unreferenced(db, previous[0])


def get_original(subject: str, kind: str, filename: str) -> dict | None:
    with closing(_db()) as db:
        row = db.execute("SELECT digest,size FROM originals WHERE subject=? AND source_type=? AND filename=?",
                         (subject, kind, filename)).fetchone()
    if not row:
        return None
    path = _path(row["digest"])
    if not path.is_file():
        return None
    return {"path": path, "digest": row["digest"], "size": row["size"]}


def remove_original(subject: str, kind: str, filename: str) -> None:
    with _lock, closing(_db()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute("SELECT digest FROM originals WHERE subject=? AND source_type=? AND filename=?",
                              (subject, kind, filename)).fetchone()
        db.execute("DELETE FROM originals WHERE subject=? AND source_type=? AND filename=?", (subject, kind, filename))
        if previous:
            _discard_unreferenced(db, previous[0])
