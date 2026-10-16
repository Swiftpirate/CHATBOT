import json
from pathlib import Path

EXTRACTED_DIR = Path("data/extracted")
OUT_FILE = Path("data/chunks.jsonl")
GROUP_ID = "G000"          # change when you get your group ID
SUBJECT = "Data Science"   # change if your subject is different
CHUNK_WORDS = 180
OVERLAP = 40

count = 0
with open(OUT_FILE, "w", encoding="utf-8") as out:
    for book_file in sorted(EXTRACTED_DIR.glob("*.jsonl")):
        with open(book_file, encoding="utf-8") as f:
            for line in f:
                page = json.loads(line)
                words = page["text"].split()
                if len(words) < 20:
                    continue  # skip blank or nearly empty pages

                start = 0
                chunk_num = 1
                while True:
                    chunk_text = " ".join(words[start:start + CHUNK_WORDS])
                    record = {
                        "group_id": GROUP_ID,
                        "subject": SUBJECT,
                        "book_id": page["book_id"],
                        "title": page["source_file"],
                        "page": page["page"],
                        "chunk_id": f"{page['book_id']}_P{page['page']}_C{chunk_num:02d}",
                        "text": chunk_text,
                    }
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    count += 1
                    chunk_num += 1
                    if start + CHUNK_WORDS >= len(words):
                        break
                    start += CHUNK_WORDS - OVERLAP

print(f"Created {count} chunks in {OUT_FILE}")