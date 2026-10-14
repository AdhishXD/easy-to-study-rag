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
    connection.execute("""CREATE TABLE IF NOT EXISTS source_pages (
        subject TEXT NOT NULL, source_type TEXT NOT NULL, filename TEXT NOT NULL,
        page INTEGER NOT NULL, year INTEGER, text TEXT NOT NULL,
        PRIMARY KEY (subject, source_type, filename, page)
    )""")
    return connection


def replace_pages(subject: str, source_type: str, filename: str,
                  pages: list[tuple[int, str]], year: int | None = None) -> None:
    with closing(_connect()) as db, db:
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
