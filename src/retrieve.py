import json
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

INDEX_DIR = Path("data/index")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # must match build_index.py

model = SentenceTransformer(MODEL_NAME)
index = faiss.read_index(str(INDEX_DIR / "faiss.index"))
with open(INDEX_DIR / "chunks_meta.jsonl", encoding="utf-8") as f:
    chunks = [json.loads(line) for line in f]


def retrieve(question: str, top_k: int = 5, books=None) -> list:
    """Return passages with text, score, book_id, title, page, and chunk_id.

    books: optional set of source file names. If given, only passages
    from those books are returned.
    """
    query_vec = model.encode([question], normalize_embeddings=True).astype("float32")

    # when filtering by book, search everything and keep only that book's passages
    k = index.ntotal if books else top_k
    scores, ids = index.search(query_vec, k)

    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx == -1:
            continue
        c = chunks[idx]
        if books and c["title"] not in books:
            continue
        results.append({
            "text": c["text"],
            "score": float(score),
            "book_id": c["book_id"],
            "title": c["title"],
            "page": c["page"],
            "chunk_id": c["chunk_id"],
        })
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    while True:
        q = input("\nAsk a question (or type 'quit'): ")
        if q.lower() == "quit":
            break
        for r in retrieve(q):
            print(f"\n[{r['score']:.3f}] {r['title']} - page {r['page']} ({r['chunk_id']})")
            print(r["text"][:300] + "...")
