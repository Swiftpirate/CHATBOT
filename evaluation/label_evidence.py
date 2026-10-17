"""Mark which retrieved passages actually contain the answer to each question.

Run from the project folder:  python evaluation\label_evidence.py
Your choices are saved into data/evaluation_questions.json after every question,
so you can stop with 'q' and continue later.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")
from retrieve import retrieve  # noqa: E402

EVAL_FILE = Path("data/evaluation_questions.json")

with open(EVAL_FILE, encoding="utf-8") as f:
    data = json.load(f)


def save():
    with open(EVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


todo = [
    q for q in data["questions"]
    if q["expected_behavior"] == "answer"
    and not q["expected_evidence"]
    and not q.get("no_relevant_in_top10")
]
print(f"{len(todo)} questions still need evidence labels.")

for q in todo:
    print("\n" + "=" * 90)
    print(f"{q['id']}  [{q['category']}]  {q['question']}")
    print(f"Reference answer: {q['reference_answer']}")

    results = retrieve(q["question"], top_k=10)
    for i, r in enumerate(results, start=1):
        snippet = r["text"][:400].replace("\n", " ")
        print(f"\n({i}) {r['title']} - PDF page {r['page']}   [score {r['score']:.3f}]")
        print(f"    {snippet}...")

    print("\nType the numbers of passages that contain the answer (e.g. 1 3)")
    picks = input("  'n' = none of them do, 's' = skip for now, 'q' = quit: ").strip().lower()

    if picks == "q":
        break
    if picks == "s" or picks == "":
        continue
    if picks == "n":
        q["no_relevant_in_top10"] = True
        q["review_status"] = "evidence_labelled"
        save()
        print(f"Recorded: no relevant passage found in top 10 for {q['id']}.")
        continue

    chosen = [
        results[int(p) - 1] for p in picks.split()
        if p.isdigit() and 1 <= int(p) <= len(results)
    ]
    q["expected_evidence"] = [{"source_file": r["title"], "page": r["page"]} for r in chosen]
    q["review_status"] = "evidence_labelled"
    save()
    print(f"Saved {len(chosen)} evidence passage(s) for {q['id']}.")

print("\nDone. Run it again any time to label the remaining questions.")
