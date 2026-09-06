

from embeddings.embed_store import query, collection_count

if __name__ == "__main__":
    total = collection_count()
    print(f"\nTotal chunks currently in ChromaDB: {total}")

    if total == 0:
        print(
            "\nNo chunks found. This usually means either:\n"
            "  1. You haven't run test_day2.py yet to ingest a file, or\n"
            "  2. You're running this script from a different folder than\n"
            "     where you ran test_day2.py, so it's pointing at a\n"
            "     different (empty) ./db/chroma_store path.\n"
        )

    while True:
        test_question = input(
            "\nEnter a test question (or just hit Enter to quit): "
        ).strip()

        if not test_question:
            print("Exiting.")
            break

        results = query(test_question, n_results=3)

        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        print("Results: ", results) 

        if not docs:
            print("No matches found.")
            continue

        for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances), start=1):
            preview = doc[:150].replace("\n", " ")
            print(f"\n[{i}] (distance={dist:.4f}) source={meta['filename']} page={meta['page']}")
            print(f"    {preview}...")