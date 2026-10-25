"""Store practice sessions and derive correctness on the server."""

from contextlib import closing
import json
import sqlite3
import time
from uuid import uuid4
from agents.cache import connect


def _db():
    db = connect()
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS quizzes (id TEXT PRIMARY KEY, subject TEXT, topic TEXT, payload TEXT)")
    db.execute("""CREATE TABLE IF NOT EXISTS attempts (
        quiz_id TEXT, question_index INTEGER, subject TEXT, topic TEXT, correct INTEGER, created REAL,
        answer TEXT NOT NULL DEFAULT '',
        PRIMARY KEY(quiz_id,question_index))""")
    if "answer" not in {row[1] for row in db.execute("PRAGMA table_info(attempts)")}:
        with db:
            db.execute("BEGIN IMMEDIATE")
            if "answer" not in {row[1] for row in db.execute("PRAGMA table_info(attempts)")}:
                db.execute("ALTER TABLE attempts ADD COLUMN answer TEXT NOT NULL DEFAULT ''")
    return db


def save_quiz(subject, topic, questions):
    id_ = uuid4().hex
    with closing(_db()) as db, db:
        db.execute("INSERT INTO quizzes VALUES(?,?,?,?)", (id_, subject, topic, json.dumps(questions)))
    return {"quiz_id": id_, "questions": questions}


def latest_quiz(subject):
    with closing(_db()) as db:
        quiz = db.execute("SELECT * FROM quizzes WHERE subject=? ORDER BY rowid DESC LIMIT 1", (subject,)).fetchone()
        if not quiz:
            return None
        attempts = db.execute("SELECT question_index, correct, answer FROM attempts WHERE quiz_id=?", (quiz["id"],)).fetchall()
    return {"quiz_id": quiz["id"], "questions": json.loads(quiz["payload"]),
            "attempts": [{**dict(row), "correct": bool(row["correct"])} for row in attempts]}


def answer_question(quiz_id, index, answer, self_correct=None):
    with closing(_db()) as db, db:
        quiz = db.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
        if not quiz:
            raise ValueError("Practice session not found")
        questions = json.loads(quiz["payload"])
        if not 0 <= index < len(questions):
            raise ValueError("Question not found")
        question = questions[index]
        if question["question_type"] == "mcq":
            if answer not in question["options"]:
                raise ValueError("Choose one of the supplied options")
            correct = answer == question["correct_answer"]
        else:
            if self_correct is None:
                raise ValueError("Self-assess your answer after reviewing the model answer")
            correct = self_correct
        db.execute("INSERT OR IGNORE INTO attempts(quiz_id,question_index,subject,topic,correct,created,answer) VALUES(?,?,?,?,?,?,?)",
                   (quiz_id, index, quiz["subject"], quiz["topic"], int(correct), time.time(), answer))
        row = db.execute("SELECT correct, answer FROM attempts WHERE quiz_id=? AND question_index=?", (quiz_id, index)).fetchone()
    return {"correct": bool(row[0]), "selected_answer": row[1], "correct_answer": question["correct_answer"],
            "explanation": question["explanation"], "sources": question["sources"]}


def progress(subject):
    with closing(_db()) as db:
        rows = db.execute("SELECT topic, COUNT(*) AS answered, SUM(correct) AS correct FROM attempts WHERE subject=? GROUP BY topic ORDER BY topic", (subject,)).fetchall()
    return [dict(row) for row in rows]
