"""Tests for the common retrieval function (retrieve.py)."""
from retrieve import retrieve

FIELDS = {"text", "score", "book_id", "title", "page", "chunk_id"}


def test_returns_top_k_passages_with_required_fields():
    results = retrieve("What is overfitting?", top_k=5)
    assert len(results) == 5
    for r in results:
        assert FIELDS <= set(r)


def test_results_are_sorted_by_score():
    scores = [r["score"] for r in retrieve("What is a p-value?", top_k=5)]
    assert scores == sorted(scores, reverse=True)


def test_source_metadata_travels_with_each_passage():
    for r in retrieve("What is k-means clustering?", top_k=5):
        assert isinstance(r["page"], int) and r["page"] >= 1
        assert r["chunk_id"].startswith(f"{r['book_id']}_P{r['page']}_")


def test_book_filter_returns_only_that_book():
    results = retrieve("What is overfitting?", top_k=3, books={"ISLR+Seventh+Printing.pdf"})
    assert results
    assert all(r["title"] == "ISLR+Seventh+Printing.pdf" for r in results)


def test_known_question_finds_the_right_book():
    titles = [r["title"] for r in retrieve("What is PageRank?", top_k=5)]
    assert "book.pdf" in titles  # Mining of Massive Datasets
