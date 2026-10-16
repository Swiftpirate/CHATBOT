import re
import json
import time
import ollama
from pathlib import Path
from retrieve import retrieve

MODEL = "llama3.2:3b"
TOP_K = 2
MIN_SCORE = 0.35  # if the best match scores lower, treat it as no evidence

# speed settings - to test threads, add e.g. "num_thread": 8
OPTIONS = {"num_predict": 150, "num_ctx": 2048}

# load real book details from the manifest
with open(Path("data/book_manifest.json"), encoding="utf-8") as f:
    BOOKS = {b["source_file"]: b for b in json.load(f)["books"]}


def book_info(source_file):
    return BOOKS.get(source_file, {"title": source_file, "author": "", "edition": ""})


PROMPT = """You answer questions using ONLY the numbered book passages below.

Rules:
- Use only information from the passages.
- After each sentence, cite the passage number in square brackets, like [1] or [2].
- Every sentence must have a citation.
- If the passages do not contain the answer, reply exactly: INSUFFICIENT EVIDENCE
- Keep the answer under 150 words.
- Do not add notes or comments about the passages.

Passages:
{passages}

Question: {question}
Answer:"""


def no_evidence():
    return {
        "answer": "The provided books do not contain enough evidence to answer this question.",
        "sources": [],
        "insufficient_evidence": True,
    }


def prepare(question):
    """Find passages and build the prompt. Returns (None, None) if there is no evidence."""
    results = retrieve(question, top_k=TOP_K)
    if not results or results[0]["score"] < MIN_SCORE:
        return None, None
    passages = "\n\n".join(
        f"[{i}] ({book_info(r['title'])['title']}, PDF page {r['page']})\n{r['text']}"
        for i, r in enumerate(results, start=1)
    )
    return results, PROMPT.format(passages=passages, question=question)


def stream_tokens(prompt):
    """Yield the answer piece by piece as the model writes it."""
    for part in ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options=OPTIONS,
        keep_alive="30m",
        stream=True,
    ):
        yield part["message"]["content"]


def finalize(text, results):
    """Clean the citations and build the final answer in the project format."""
    text = text.strip()
    if "INSUFFICIENT EVIDENCE" in text.upper():
        return no_evidence()

    # split combined citations like [1, 2] into [1][2]
    text = re.sub(
        r"\[(\d+(?:\s*,\s*\d+)+)\]",
        lambda m: "".join(f"[{x.strip()}]" for x in m.group(1).split(",")),
        text,
    )

    # keep only citation numbers that match a retrieved passage
    found = re.findall(r"\[(\d+)\]", text)
    valid = []
    for n in dict.fromkeys(found):
        if 1 <= int(n) <= len(results):
            valid.append(int(n))
        else:
            text = text.replace(f"[{n}]", "")  # remove invented numbers

    sources = []
    for n in sorted(valid):
        r = results[n - 1]
        info = book_info(r["title"])
        sources.append({
            "n": n,
            "book_id": r["book_id"],
            "title": info["title"],
            "author": info["author"],
            "edition": info["edition"],
            "page": r["page"],
            "chunk_id": r["chunk_id"],
        })

    if not sources:
        text += "\n\n(Warning: no valid citation was given, so this answer is not verified.)"

    return {"answer": text, "sources": sources, "insufficient_evidence": False}


def answer(question: str) -> dict:
    """Full answer without streaming (used for tests and evaluation)."""
    results, prompt = prepare(question)
    if results is None:
        return no_evidence()
    text = "".join(stream_tokens(prompt))
    return finalize(text, results)


if __name__ == "__main__":
    while True:
        q = input("\nAsk a question (or type 'quit'): ")
        if q.lower() == "quit":
            break
        start = time.time()
        results, prompt = prepare(q)
        if results is None:
            result = no_evidence()
            print("\n" + result["answer"])
        else:
            print()
            text = ""
            for piece in stream_tokens(prompt):
                print(piece, end="", flush=True)
                text += piece
            print()
            result = finalize(text, results)
        print("\nSources:")
        for s in result["sources"]:
            print(f"  [{s['n']}] {s['title']} ({s['author']}, {s['edition']}), "
                  f"PDF page {s['page']} - {s['chunk_id']}")
        if result["insufficient_evidence"]:
            print("  (insufficient evidence)")
        print(f"\nTime: {time.time() - start:.1f}s")