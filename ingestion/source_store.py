"""Full extracted source pages for analysis that must not read overlap fragments."""

import os
from contextlib import closing
from pathlib import Path
import sqlite3

from dotenv import load_dotenv

load_dotenv()


DB_PATH = Path(os.getenv("SOURCE_DB_PATH", "./db/source_pages.sqlite3"))


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("""CREATE TABLE IF NOT EXISTS source_pages (
        subject TEXT NOT NULL, source_type TEXT NOT NULL, filename TEXT NOT NULL,
        page INTEGER NOT NULL, year INTEGER, text TEXT NOT NULL,
        PRIMARY KEY (subject, source_type, filename, page)
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS source_files (
        subject TEXT, source_type TEXT, filename TEXT, fingerprint TEXT,
        chunks INTEGER, year INTEGER,
        PRIMARY KEY(subject, source_type, filename))""")
    connection.execute("CREATE TABLE IF NOT EXISTS subjects (name TEXT PRIMARY KEY)")
    return connection


def replace_pages(subject: str, source_type: str, filename: str,
                  pages: list[tuple[int, str]], year: int | None = None) -> None:
    with closing(_connect()) as db, db:
        db.execute("INSERT OR IGNORE INTO subjects VALUES(?)", (subject,))
        db.execute("CREATE TABLE IF NOT EXISTS analyses (subject TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        db.execute("DELETE FROM analyses WHERE subject=?", (subject,))
        db.execute("DELETE FROM source_pages WHERE subject=? AND source_type=? AND filename=?",
                   (subject, source_type, filename))
        db.executemany(
            "INSERT INTO source_pages(subject,source_type,filename,page,year,text) VALUES(?,?,?,?,?,?)",
            [(subject, source_type, filename, number, year, text) for number, text in pages],
        )


def get_pages(subject: str, source_types: tuple[str, ...] | None = None) -> list[dict]:
    with closing(_connect()) as db, db:
        if source_types:
            placeholders = ",".join("?" for _ in source_types)
            rows = db.execute(
                f"SELECT * FROM source_pages WHERE subject=? AND source_type IN ({placeholders}) "
                "ORDER BY source_type,filename,page", (subject, *source_types)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM source_pages WHERE subject=? ORDER BY source_type,filename,page",
                              (subject,)).fetchall()
    return [dict(row) for row in rows]


def list_subjects() -> list[dict]:
    with closing(_connect()) as db:
        rows = db.execute("""SELECT name, COUNT(DISTINCT source_type || ':' || filename) AS files,
            COUNT(page) AS pages, COUNT(DISTINCT CASE WHEN source_type='past_qp' THEN year END) AS years
            FROM (SELECT name FROM subjects UNION SELECT subject FROM source_pages) s
            LEFT JOIN source_pages p ON p.subject=s.name GROUP BY name ORDER BY name COLLATE NOCASE""").fetchall()
    return [dict(row) for row in rows]


def create_subject(name: str) -> None:
    with closing(_connect()) as db, db:
        db.execute("INSERT OR IGNORE INTO subjects VALUES(?)", (name,))


def list_files(subject: str) -> list[dict]:
    with closing(_connect()) as db:
        rows = db.execute("""SELECT p.source_type, p.filename, MAX(p.year) AS year,
            COUNT(*) AS pages, SUM(LENGTH(p.text)) AS characters, MAX(f.chunks) AS chunks
            FROM source_pages p LEFT JOIN source_files f ON p.subject=f.subject AND
            p.source_type=f.source_type AND p.filename=f.filename WHERE p.subject=?
            GROUP BY p.source_type,p.filename ORDER BY p.filename COLLATE NOCASE""", (subject,)).fetchall()
    return [dict(row) for row in rows]


def source_fingerprint(subject: str, kind: str, filename: str) -> tuple | None:
    with closing(_connect()) as db:
        row = db.execute("SELECT fingerprint,chunks,year FROM source_files WHERE subject=? AND source_type=? AND filename=?",
                         (subject, kind, filename)).fetchone()
    return tuple(row) if row else None


def register_source(subject: str, kind: str, filename: str, fingerprint: str, chunks: int, year) -> None:
    with closing(_connect()) as db, db:
        db.execute("INSERT OR REPLACE INTO source_files VALUES(?,?,?,?,?,?)",
                   (subject, kind, filename, fingerprint, chunks, year))


def delete_source_pages(subject: str, kind: str, filename: str) -> None:
    from ingestion.original_store import remove_original
    with closing(_connect()) as db, db:
        db.execute("DELETE FROM source_pages WHERE subject=? AND source_type=? AND filename=?", (subject, kind, filename))
        db.execute("DELETE FROM source_files WHERE subject=? AND source_type=? AND filename=?", (subject, kind, filename))
        db.execute("CREATE TABLE IF NOT EXISTS analyses (subject TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        db.execute("DELETE FROM analyses WHERE subject=?", (subject,))
    remove_original(subject, kind, filename)


def corpus_fingerprint(pages: list[dict]) -> str:
    import hashlib
    import json
    return hashlib.sha256(json.dumps(pages, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def get_source_pages(subject: str, kind: str, filename: str, page: int | None = None) -> list[dict]:
    with closing(_connect()) as db:
        sql = "SELECT * FROM source_pages WHERE subject=? AND source_type=? AND filename=?"
        values = [subject, kind, filename]
        if page is not None and page > 0:
            sql += " AND page=?"
            values.append(page)
        sql += " ORDER BY page" + (" LIMIT 1" if page == 0 else "")
        rows = db.execute(sql, values).fetchall()
    return [dict(row) for row in rows]


def page_numbers(subject: str, kind: str, filename: str) -> list[int]:
    with closing(_connect()) as db:
        rows = db.execute("SELECT page FROM source_pages WHERE subject=? AND source_type=? AND filename=? ORDER BY page",
                          (subject, kind, filename)).fetchall()
    return [row[0] for row in rows]


def set_source_year(subject: str, filename: str, year: int) -> None:
    with closing(_connect()) as db, db:
        db.execute("UPDATE source_pages SET year=? WHERE subject=? AND source_type='past_qp' AND filename=?", (year, subject, filename))
        db.execute("UPDATE source_files SET year=? WHERE subject=? AND source_type='past_qp' AND filename=?", (year, subject, filename))
        db.execute("CREATE TABLE IF NOT EXISTS analyses (subject TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        db.execute("DELETE FROM analyses WHERE subject=?", (subject,))
