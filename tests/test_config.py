"""Checks that config/config.json matches the settings actually used in the code."""
import json
from pathlib import Path

import generate
import retrieve

CONFIG = json.loads(Path("config/config.json").read_text(encoding="utf-8"))


def test_embedding_model_matches_retrieval_and_index_building():
    model = CONFIG["embedding"]["model"]
    assert retrieve.MODEL_NAME == model
    assert f'MODEL_NAME = "{model}"' in Path("src/build_index.py").read_text(encoding="utf-8")


def test_chunk_settings_match_chunk_script():
    source = Path("src/chunk.py").read_text(encoding="utf-8")
    assert f"CHUNK_WORDS = {CONFIG['chunking']['chunk_words']}" in source
    assert f"OVERLAP = {CONFIG['chunking']['overlap_words']}" in source


def test_retrieval_settings_match_generate():
    r = CONFIG["retrieval"]
    assert generate.TOP_K == r["top_k"]
    assert generate.PER_BOOK == r["per_book_when_named"]
    assert generate.MIN_SCORE == r["min_score"]


def test_generation_settings_match_generate():
    g = CONFIG["generation"]
    assert generate.MODEL == g["model"]
    assert generate.OPTIONS == g["options"]
