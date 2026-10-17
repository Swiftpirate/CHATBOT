"""Tests for citations, the answer format and insufficient-evidence behaviour (generate.py).

These tests do not call the language model, so they run without waiting for Ollama.
"""
import pytest

from generate import books_named_in, finalize, prepare, strip_book_names
from retrieve import chunks

# two fake retrieved passages, as retrieve() would return them
RESULTS = [
    {"title": "os.pdf", "book_id": "G000_BOOK_011", "page": 195,
     "chunk_id": "G000_BOOK_011_P195_C01", "text": "...", "score": 0.75},
    {"title": "prob.pdf", "book_id": "G000_BOOK_012", "page": 28,
     "chunk_id": "G000_BOOK_012_P28_C01", "text": "...", "score": 0.60},
]


# ---------- answer format ----------
def test_answer_format_matches_the_project_spec():
    result = finalize("A p-value is a probability [1].", RESULTS)
    assert set(result) == {"answer", "sources", "insufficient_evidence"}
    for s in result["sources"]:
        assert {"book_id", "page", "chunk_id"} <= set(s)


# ---------- citations ----------
def test_valid_citation_is_kept():
    result = finalize("A p-value is a probability [1].", RESULTS)
    assert result["insufficient_evidence"] is False
    assert [s["chunk_id"] for s in result["sources"]] == ["G000_BOOK_011_P195_C01"]


def test_invented_citation_is_removed():
    result = finalize("Fact one [1]. Fact two [7].", RESULTS)
    assert "[7]" not in result["answer"]
    assert [s["n"] for s in result["sources"]] == [1]


def test_combined_citations_are_split():
    result = finalize("Both books say this [1, 2].", RESULTS)
    assert {s["n"] for s in result["sources"]} == {1, 2}


def test_answer_without_citation_is_flagged():
    result = finalize("This sentence has no citation.", RESULTS)
    assert result["sources"] == []
    assert "not verified" in result["answer"]


def test_every_displayed_citation_resolves_to_a_stored_passage():
    stored = {c["chunk_id"] for c in chunks}
    results, _ = prepare("What is a p-value?")
    assert results is not None
    result = finalize("An answer citing both passages [1][2].", results)
    assert result["sources"]
    assert all(s["chunk_id"] in stored for s in result["sources"])


# ---------- insufficient evidence ----------
def test_model_refusal_becomes_insufficient_evidence():
    result = finalize("INSUFFICIENT EVIDENCE", RESULTS)
    assert result["insufficient_evidence"] is True
    assert result["sources"] == []


@pytest.mark.parametrize("question", [
    "What is the latest version of PyTorch?",
    "What is the price of copper today?",
])
def test_time_sensitive_questions_abstain(question):
    assert prepare(question) == (None, None)


@pytest.mark.parametrize("question", [
    "How do I cook nshima?",
    "Who won the 2010 FIFA World Cup?",
])
def test_off_topic_questions_abstain(question):
    assert prepare(question) == (None, None)


def test_named_book_that_does_not_cover_the_topic_abstains():
    assert prepare("What does Convex Optimization say about PageRank?") == (None, None)


# ---------- book filtering helpers ----------
def test_book_names_are_detected():
    named = books_named_in("Do Bishop and ISLR define the bias-variance tradeoff the same way?")
    assert set(named) == {
        "Bishop-Pattern-Recognition-and-Machine-Learning-2006.pdf",
        "ISLR+Seventh+Printing.pdf",
    }


def test_book_names_are_removed_before_searching():
    topic = strip_book_names("What does Convex Optimization say about PageRank?")
    assert "convex optimization" not in topic.lower()
    assert "PageRank" in topic
