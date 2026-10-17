"""Run the evaluation benchmark through the chatbot and save the results.

Run from the project folder:
    python evaluation\run_eval.py            (validation questions - use while tuning)
    python evaluation\run_eval.py test       (test questions - only for the final evaluation)
    python evaluation\run_eval.py all        (every question)

Outputs:
    evaluation/report_<split>.json             metrics + per-question results
    evaluation/answers_for_review_<split>.csv  answers for you to mark correct/incorrect
"""
import csv
import json
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "src")
from retrieve import retrieve, chunks, MODEL_NAME  # noqa: E402
from generate import answer, MODEL, TOP_K, PER_BOOK, MIN_SCORE, OPTIONS  # noqa: E402

EVAL_FILE = Path("data/evaluation_questions.json")
MANIFEST = Path("data/book_manifest.json")
OUT_DIR = Path("evaluation")
SPLIT = sys.argv[1] if len(sys.argv) > 1 else "validation"

with open(EVAL_FILE, encoding="utf-8") as f:
    questions = [q for q in json.load(f)["questions"] if SPLIT == "all" or q["split"] == SPLIT]
with open(MANIFEST, encoding="utf-8") as f:
    id_to_file = {b["book_id"]: b["source_file"] for b in json.load(f)["books"]}
all_chunk_ids = {c["chunk_id"] for c in chunks}

print(f"Running {len(questions)} '{SPLIT}' questions...\n")
rows = []

for q in questions:
    start = time.time()
    result = answer(q["question"])
    elapsed = time.time() - start

    expected = {(e["source_file"], e["page"]) for e in q["expected_evidence"]}
    should_answer = q["expected_behavior"] == "answer"
    abstained = result["insufficient_evidence"]

    # Retrieval Recall@5: did any of the top 5 passages contain the answer?
    recall = None
    if should_answer:
        if expected:
            top5 = retrieve(q["question"], top_k=5)
            recall = int(any((r["title"], r["page"]) in expected for r in top5))
        elif q.get("no_relevant_in_top10"):
            recall = 0

    # Citations: do they resolve to real passages, and do they hit the expected pages?
    cited = result["sources"]
    resolves = all(s["chunk_id"] in all_chunk_ids for s in cited)
    hits_expected = None
    if expected and cited:
        hits_expected = int(any((id_to_file.get(s["book_id"]), s["page"]) in expected for s in cited))

    behaviour_ok = abstained if not should_answer else not abstained

    rows.append({
        "id": q["id"],
        "category": q["category"],
        "question": q["question"],
        "expected_behavior": q["expected_behavior"],
        "abstained": abstained,
        "behaviour_ok": behaviour_ok,
        "recall_at_5": recall,
        "num_citations": len(cited),
        "citations_resolve": resolves,
        "citation_hits_expected_page": hits_expected,
        "uncited_answer": (not abstained) and len(cited) == 0,
        "seconds": round(elapsed, 1),
        "answer": result["answer"],
        "sources": [
            f"[{s['n']}] {s['title']}, PDF page {s['page']} ({s['chunk_id']})" for s in cited
        ],
        "reference_answer": q["reference_answer"],
    })
    status = "OK " if behaviour_ok else "BAD"
    print(f"{q['id']}  {status}  {elapsed:5.1f}s  recall@5={recall}  citations={len(cited)}")


def rate(values):
    values = [v for v in values if v is not None]
    return {"rate": round(sum(values) / len(values), 3) if values else None, "n": len(values)}


answer_rows = [r for r in rows if r["expected_behavior"] == "answer"]
abstain_rows = [r for r in rows if r["expected_behavior"] == "abstain"]
answered_rows = [r for r in rows if not r["abstained"]]
times = [r["seconds"] for r in rows]

metrics = {
    "retrieval_recall_at_5": rate([r["recall_at_5"] for r in answer_rows]),
    "abstention_accuracy_on_no_answer_questions": rate([int(r["abstained"]) for r in abstain_rows]),
    "false_refusal_rate_on_answerable_questions": rate([int(r["abstained"]) for r in answer_rows]),
    "citation_traceability_all_citations_resolve": rate([int(r["citations_resolve"]) for r in answered_rows]),
    "citation_hits_expected_page": rate([r["citation_hits_expected_page"] for r in answered_rows]),
    "uncited_answer_rate": rate([int(r["uncited_answer"]) for r in answered_rows]),
    "response_time_seconds": {
        "mean": round(statistics.mean(times), 1) if times else None,
        "median": round(statistics.median(times), 1) if times else None,
        "max": round(max(times), 1) if times else None,
    },
    "answer_correctness": "Mark the CSV by hand, then calculate the percentage marked correct.",
}

report = {
    "split": SPLIT,
    "date": datetime.now().isoformat(timespec="seconds"),
    "conditions": {
        "embedding_model": MODEL_NAME,
        "generation_model": MODEL,
        "top_k": TOP_K,
        "per_book_when_named": PER_BOOK,
        "min_score": MIN_SCORE,
        "generation_options": OPTIONS,
        "machine": platform.platform(),
        "processor": platform.processor(),
        "note": "CPU only. Record peak RAM from Task Manager while the evaluation runs.",
    },
    "metrics": metrics,
    "results": rows,
}

OUT_DIR.mkdir(exist_ok=True)
with open(OUT_DIR / f"report_{SPLIT}.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

with open(OUT_DIR / f"answers_for_review_{SPLIT}.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "category", "question", "reference_answer", "chatbot_answer",
                     "sources", "correct (yes/partly/no)", "citation supports claim (yes/no)", "notes"])
    for r in rows:
        writer.writerow([r["id"], r["category"], r["question"], r["reference_answer"],
                         r["answer"], " | ".join(r["sources"]), "", "", ""])

print("\n=== Summary ===")
for name, value in metrics.items():
    print(f"{name}: {value}")
print(f"\nSaved evaluation/report_{SPLIT}.json and evaluation/answers_for_review_{SPLIT}.csv")
