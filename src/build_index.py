import json
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = Path("data/chunks.jsonl")
INDEX_DIR = Path("data/index")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # replace with the approved model

INDEX_DIR.mkdir(parents=True, exist_ok=True)

with open(CHUNKS_FILE, encoding="utf-8") as f:
    chunks = [json.loads(line) for line in f]
texts = [c["text"] for c in chunks]
print(f"Loaded {len(texts)} chunks")

model = SentenceTransformer(MODEL_NAME)
embeddings = model.encode(texts, batch_size=64, show_progress_bar=True,
                          normalize_embeddings=True)
embeddings = np.array(embeddings, dtype="float32")

index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings)
faiss.write_index(index, str(INDEX_DIR / "faiss.index"))

with open(INDEX_DIR / "chunks_meta.jsonl", "w", encoding="utf-8") as f:
    for c in chunks:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

print(f"Saved index with {index.ntotal} vectors to {INDEX_DIR}")