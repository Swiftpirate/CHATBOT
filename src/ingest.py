import fitz  # PyMuPDF
import json
from pathlib import Path

BOOKS_DIR = Path("data/books")
OUT_DIR = Path("data/extracted")
GROUP_ID = "G000"  # change this when you get your group ID

OUT_DIR.mkdir(parents=True, exist_ok=True)

pdfs = sorted(BOOKS_DIR.glob("*.pdf"))
print(f"Found {len(pdfs)} books")

for i, pdf_path in enumerate(pdfs, start=1):
    book_id = f"{GROUP_ID}_BOOK_{i:03d}"
    doc = fitz.open(pdf_path)
    out_file = OUT_DIR / f"{book_id}.jsonl"
    empty_pages = 0

    with open(out_file, "w", encoding="utf-8") as f:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            if len(text.strip()) < 50:
                empty_pages += 1
            record = {
                "book_id": book_id,
                "source_file": pdf_path.name,
                "page": page_num,
                "text": text,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"{book_id}: {pdf_path.name} - {len(doc)} pages, {empty_pages} nearly empty")
    doc.close()