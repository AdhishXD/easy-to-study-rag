"""Small clearly synthetic public corpus; replace with licensed course material."""

from embeddings.embed_store import collection_count, store_chunks
from ingestion.chunker import chunk_pages
from ingestion.source_store import get_pages, replace_pages

SUBJECT = "DBMS (synthetic demo)"

TEACHING = [
    ("dbms_notes.pdf", "textbook", "A functional dependency X -> Y means that any two rows agreeing on X must agree on Y. A candidate key is a minimal set of attributes that functionally determines every attribute in the relation. Normalization reduces redundancy and update anomalies. First normal form requires atomic attribute values. Second normal form removes partial dependencies on part of a composite key. Third normal form removes transitive dependencies of non-key attributes on a key. BCNF requires every determinant of a nontrivial functional dependency to be a superkey."),
    ("dbms_slides.pptx", "lecture_slide", "Transactions group database operations into a unit. ACID means atomicity, consistency, isolation, and durability. Atomicity means all operations commit or none do. Isolation prevents concurrent transactions from interfering as though they ran serially. Durability means committed changes survive failures. Serializability asks whether a concurrent schedule is equivalent to a serial schedule. Two-phase locking has a growing phase that acquires locks and a shrinking phase that releases locks."),
    ("dbms_lecture.txt", "lecture_video", "An index speeds up lookup by maintaining a search structure. A B+ tree keeps keys sorted and stores data pointers in leaf nodes; linked leaves support efficient range scans. An index adds storage and makes writes more expensive. Query optimization compares alternative execution plans and tries to choose a low-cost plan, based on estimates such as row counts and selectivity."),
]

PAPERS = {
    2022: "1. Explain functional dependency and candidate key. 2. Normalize a relation to third normal form. 3. Describe ACID properties of a transaction. 4. Explain B+ tree indexing.",
    2023: "1. Discuss normalization and third normal form with a functional dependency example. 2. Explain serializability and two-phase locking. 3. Compare B+ tree indexing and a table scan.",
    2024: "1. Identify candidate keys from functional dependencies and explain normalization. 2. Describe ACID properties and isolation in transactions. 3. Discuss B+ tree range scans and query optimization.",
}


def seed_demo() -> int:
    if not get_pages(SUBJECT):
        for filename, kind, text in TEACHING:
            replace_pages(SUBJECT, kind, filename, [(1, text)])
        for year, text in PAPERS.items():
            replace_pages(SUBJECT, "past_qp", f"dbms_{year}.pdf", [(1, text)], year)
    if collection_count():
        return 0
    records = []
    for filename, kind, text in TEACHING:
        records.extend(chunk_pages([(1, text)], kind, filename,
                                   extra_metadata={"subject": SUBJECT}))
    for year, text in PAPERS.items():
        records.extend(chunk_pages([(1, text)], "past_qp", f"dbms_{year}.pdf",
                                   extra_metadata={"subject": SUBJECT, "year": year}))
    return store_chunks(records)
