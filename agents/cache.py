"""Persistent content-addressed caches. Private material never enters Git."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import time


def connect():
    path = Path(os.getenv("CACHE_DB_PATH", "./db/runtime.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS cache (
        namespace TEXT, key TEXT, payload TEXT NOT NULL, created REAL NOT NULL,
        PRIMARY KEY(namespace,key))""")
    return db


def get(namespace: str, key: str):
    with closing(connect()) as db:
        row = db.execute("SELECT payload FROM cache WHERE namespace=? AND key=?", (namespace, key)).fetchone()
    return json.loads(row[0]) if row else None


def put(namespace: str, key: str, value) -> None:
    with closing(connect()) as db, db:
        db.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?,?)",
                   (namespace, key, json.dumps(value, ensure_ascii=False), time.time()))


def get_many(namespace: str, keys: list[str]) -> dict:
    if not keys:
        return {}
    with closing(connect()) as db:
        placeholders = ",".join("?" for _ in keys)
        rows = db.execute(f"SELECT key,payload FROM cache WHERE namespace=? AND key IN ({placeholders})", (namespace, *keys)).fetchall()
    return {key: json.loads(payload) for key, payload in rows}


def put_many(namespace: str, values: dict) -> None:
    with closing(connect()) as db, db:
        db.executemany("INSERT OR REPLACE INTO cache VALUES(?,?,?,?)",
                       [(namespace, key, json.dumps(value), time.time()) for key, value in values.items()])
