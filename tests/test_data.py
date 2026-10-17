"""Tests for the book manifest, extraction (ingest.py), chunking (chunk.py) and the index."""
import json
import re
from pathlib import Path

import faiss
import pytest

MANIFEST = json.loads(Path("data/book_manifest.json").read_text(encoding="utf-8"))
BOOKS = MANIFEST["books"]
CONFIG = json.loads(Path("config/config.json").read_text(encoding="utf-8"))
CHUNK_FIELDS = {"group_id", "subject", "book_id", "title", "page", "chunk_id", "text"}
CHUNK_ID = re.compile(r"^G\d{3}_BOOK_\d{3}_P\d+_C\d{2,}$")


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


# ---------- manifest ----------
def test_manifest_books_have_required_fields():
    required = {"book_id", "source_file", "title", "author", "edition", "permission_status", "processing_status"}
    for b in BOOKS:
        assert required <= set(b), f"{b.get('book_id')} is missing fields"


def test_manifest_book_ids_are_unique():
    ids = [b["book_id"] for b in BOOKS]
    assert len(ids) == len(set(ids))


@pytest.mark.xfail(reason="The PDF requires 15 books; the group has 14 pending coordinator approval.")
def test_manifest_meets_minimum_of_15_books():
    assert len(BOOKS) >= 15


# ---------- extraction ----------
def test_one_extracted_file_per_book():
    extracted = sorted(p.stem for p in Path("data/extracted").glob("*.jsonl"))
    assert extracted == sorted(b["book_id"] for b in BOOKS)


def test_extracted_pages_keep_book_and_page_metadata():
    for b in BOOKS:
        records = load_jsonl(Path("data/extracted") / f"{b['book_id']}.jsonl")
        assert records, f"{b['book_id']} has no pages"
        assert records[0]["page"] == 1
        for r in records[:5]:
            assert {"book_id", "source_file", "page", "text"} <= set(r)
            assert r["book_id"] == b["book_id"]
            assert r["source_file"] == b["source_file"]


# ---------- chunking ----------
CHUNKS = load_jsonl("data/chunks.jsonl")


def test_chunks_follow_the_passage_schema():
    for c in CHUNKS:
        assert CHUNK_FIELDS <= set(c)
        assert CHUNK_ID.match(c["chunk_id"]), c["chunk_id"]
        assert c["chunk_id"].startswith(f"{c['book_id']}_P{c['page']}_")


def test_chunk_ids_are_unique():
    ids = [c["chunk_id"] for c in CHUNKS]
    assert len(ids) == len(set(ids))


def test_chunks_respect_the_size_limit():
    limit = CONFIG["chunking"]["chunk_words"]
    assert all(len(c["text"].split()) <= limit for c in CHUNKS)


def test_every_chunk_comes_from_a_manifest_book():
    files = {b["source_file"] for b in BOOKS}
    assert all(c["title"] in files for c in CHUNKS)


# ---------- index ----------
def test_index_has_one_vector_per_chunk():
    index = faiss.read_index("data/index/faiss.index")
    meta = load_jsonl("data/index/chunks_meta.jsonl")
    assert index.ntotal == len(meta) == len(CHUNKS)
