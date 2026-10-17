import re
import json
import time
import ollama
from pathlib import Path
from retrieve import retrieve

MODEL = "llama3.2:3b"
TOP_K = 2           # passages for a normal question
PER_BOOK = 2        # passages per book when the question names books
MIN_SCORE = 0.35    # if the best match scores lower, treat it as no evidence

# speed + consistency settings (temperature 0 = same answer every time)
# to test threads, add e.g. "num_thread": 8
OPTIONS = {"num_predict": 300, "num_ctx": 2048, "temperature": 0}

# load real book details from the manifest
with open(Path("data/book_manifest.json"), encoding="utf-8") as f:
    BOOKS = {b["source_file"]: b for b in json.load(f)["books"]}

# names people may use for each book in a question
BOOK_ALIASES = {
    "978-3-031-41026-0.pdf": ["linear algebra done right", "axler"],
    "Bishop-Pattern-Recognition-and-Machine-Learning-2006.pdf": ["bishop", "prml", "pattern recognition and machine learning"],
    "book.pdf": ["mining of massive datasets", "mmds", "leskovec", "ullman"],
    "book2016June9.pdf": ["foundations of data science", "hopcroft", "kannan"],
    "bv_cvxbook.pdf": ["convex optimization"],
    "d2l-en.pdf": ["dive into deep learning", "d2l"],
    "ed3book_aug26.pdf": ["speech and language processing", "jurafsky"],
    "irbookprint.pdf": ["introduction to information retrieval", "ir book", "manning"],
    "ISLR+Seventh+Printing.pdf": ["islr", "isl", "introduction to statistical learning"],
    "mml-book.pdf": ["mathematics for machine learning", "mml", "deisenroth"],
    "os.pdf": ["openintro"],
    "prob.pdf": ["grinstead", "snell"],
    "understanding-machine-learning-theory-algorithms.pdf": ["understanding machine learning", "shalev-shwartz", "ben-david"],
    "vmls.pdf": ["applied linear algebra", "vmls"],
}


def book_info(source_file):
    return BOOKS.get(source_file, {"title": source_file, "author": "", "edition": ""})


def books_named_in(question):
    """Return the source files of any books mentioned by name in the question."""
    q = question.lower()
    named = []
    for source_file, aliases in BOOK_ALIASES.items():
        if any(re.search(rf"\b{re.escape(a)}\b", q) for a in aliases):
            named.append(source_file)
    return named


def strip_book_names(question):
    """Remove book names from the question so the search matches the topic, not the title."""
    q = question
    for aliases in BOOK_ALIASES.values():
        for a in aliases:
            q = re.sub(rf"\b{re.escape(a)}\b", " ", q, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", q).strip()


PROMPT = """You answer questions using ONLY the numbered book passages below.

Rules:
- Give the final answer in the first sentence, then explain briefly.
- Use only information from the passages.
- After each sentence, cite the passage number in square brackets, like [1] or [2].
- Every sentence must have a citation.
- When you mention a book, use the book title shown next to the passage number.
- If the question asks you to compare books, first say what each book's passages say, then state how they are similar or different.
- If the passages do not contain the information needed to answer the question, reply exactly: INSUFFICIENT EVIDENCE
- If the question asks about current or latest information (latest versions, prices, news, people in office), reply exactly: INSUFFICIENT EVIDENCE
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


TIME_SENSITIVE = re.compile(
    r"\b(latest|newest|most recent|current version|right now|today|this year|nowadays)\b",
    re.IGNORECASE,
)


def prepare(question):
    """Find passages and build the prompt. Returns (None, None) if there is no evidence."""
    # books are fixed snapshots, so they cannot answer questions about the present
    if TIME_SENSITIVE.search(question):
        return None, None

    named = books_named_in(question)

    if named:
        # search by topic only (book names removed), then keep the best
        # passages from each named book that are actually relevant
        topic = strip_book_names(question)
        results = []
        for source_file in named:
            hits = retrieve(topic, top_k=PER_BOOK, books={source_file})
            results += [h for h in hits if h["score"] >= MIN_SCORE]
    else:
        results = retrieve(question, top_k=TOP_K)

    if not results or max(r["score"] for r in results) < MIN_SCORE:
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
    # only treat it as a refusal if the reply starts with the refusal phrase
    if text.upper().startswith("INSUFFICIENT EVIDENCE"):
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