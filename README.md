# DataSage: a book-grounded data science chatbot

**Group ID:** G000 *(placeholder until the coordinator assigns one)*
**Subject:** Data Science
**Project:** Collaborative Transformer Chatbot, Group contribution

DataSage answers questions about data science using only 14 textbooks. Every answer cites the book, PDF page and passage it came from. When the books don't cover a question, DataSage says so instead of guessing. It runs fully offline on a laptop CPU.

## How it works

```
Question
  -> search 23,369 book passages (sentence embeddings + FAISS)
  -> keep the best passages (filtered by book if the question names one)
  -> Llama 3.2 3B writes an answer from those passages only, citing [1], [2]
  -> citations are checked against the retrieved passages
  -> answer + sources (book, author, edition, PDF page, passage ID)
```

## Features

- **Grounded answers.** The model may only use the retrieved book passages.
- **Checked citations.** Citation numbers that don't match a retrieved passage are removed, and answers with no valid citation are flagged as unverified.
- **Refusals.** The chatbot refuses when no passage is relevant enough (score below 0.35), and always refuses time-sensitive questions such as "latest", "current" or "today".
- **Book filtering.** If a question names a book ("Bishop", "ISLR", "Convex Optimization"), only that book's passages are searched. Comparison questions get passages from each named book.
- **Streaming.** Answers appear word by word as they are written.
- **Chat interface.** Streamlit app with conversation history, example questions, source cards and a library view.
- **Offline and CPU-only.** No API keys and no GPU needed.

## Repository structure

```
chatbot-project/
├── README.md
├── requirements.txt
├── .streamlit/config.toml        Streamlit theme
├── config/config.json            models, chunking, retrieval and generation settings
├── data/
│   ├── book_manifest.json        metadata for all 14 books
│   ├── evaluation_questions.json 30 benchmark questions with reference answers and evidence
│   ├── books/                    the PDFs (not in git, copyrighted)
│   ├── extracted/                page text per book (not in git, generated)
│   ├── chunks.jsonl              passages (not in git, generated)
│   └── index/                    FAISS index + passage metadata (not in git, generated)
├── src/
│   ├── ingest.py                 PDF -> page text, with book ID and page number
│   ├── chunk.py                  page text -> 180-word passages
│   ├── build_index.py            passages -> embeddings -> FAISS index
│   ├── retrieve.py               retrieve(question, top_k) -> passages with sources
│   ├── generate.py               answer(question) -> answer, sources, insufficient_evidence
│   └── app.py                    Streamlit chat interface
├── tests/                        automated tests (pytest)
├── evaluation/                   evaluation scripts, results and report
└── artifacts/
```

## Setup

Tested on Windows 11 with Python 3.14.7, an Intel Core i7-1255U and 12 GB RAM.

**1. Clone the repository and create a virtual environment**
```
git clone https://github.com/Swiftpirate/CHATBOT.git
cd CHATBOT
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**2. Install Ollama and the language model**

Download Ollama from https://ollama.com, then run:
```
ollama pull llama3.2:3b
```

**3. Add the books**

The PDFs aren't in the repository because of copyright. Download each book from the `source_url` in `data/book_manifest.json` and save it in `data\books\` under the **exact filename** in `source_file`. Book IDs are assigned in filename order, so a missing or renamed file changes every ID.

**4. Build the search index** (one time, about 20 minutes on a CPU)
```
python src\ingest.py
python src\chunk.py
python src\build_index.py
```
The first run downloads the embedding model (about 90 MB), so it needs internet. After that, everything works offline.

## Running the chatbot

**Chat interface**
```
streamlit run src\app.py
```
It opens at http://localhost:8501.

**Terminal version** (prints the response time)
```
python src\generate.py
```

**Offline tip:** to skip the Hugging Face update check when you have no internet, run `set HF_HUB_OFFLINE=1` first.

## Using it from Python

```python
from retrieve import retrieve
from generate import answer

retrieve("What is overfitting?", top_k=5)
# [{"text", "score", "book_id", "title", "page", "chunk_id"}, ...]

answer("What is overfitting?")
# {"answer": "...", "sources": [{"book_id", "page", "chunk_id", ...}], "insufficient_evidence": False}
```

Run from the project folder with `src` on the Python path.

## Configuration

All settings are recorded in `config/config.json`, and `tests/test_config.py` checks that they match the code.

| Setting | Value |
|---|---|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` *(placeholder until the coordinator approves a model)* |
| Chunks | 180 words, 40-word overlap, kept within one page |
| Index | FAISS `IndexFlatIP` (cosine similarity) |
| Retrieval | top 2 passages; 2 per book when books are named; minimum score 0.35 |
| Generation | `llama3.2:3b` via Ollama, temperature 0, up to 300 tokens, 2048-token context |

Changing the embedding model or the chunk settings means rerunning `chunk.py` and `build_index.py`, and then the evaluation.

## Tests

```
python -m pytest tests -v
```
There are 33 tests covering the manifest, extraction, chunking, the index, retrieval, citation checking, the answer format, refusals and config consistency. Current result: **32 passed, 1 expected failure**. The expected failure is the 15-book minimum; see Known limitations. The tests don't call the language model, so Ollama doesn't need to be running.

## Evaluation

The benchmark has 30 questions: 10 for validation (used while tuning) and 20 held out for testing (run once, after tuning). They cover direct facts, reasoning, calculations, cross-book comparisons, questions the books can't answer, and citation traps.

```
python evaluation\label_evidence.py      label which pages contain each answer
python evaluation\run_eval.py            validation set
python evaluation\run_eval.py test       held-out test set (final evaluation only)
```

**Test set results:**

| Measure | Target | Result |
|---|---|---|
| Retrieval Recall@5 | ≥ 80% | 75.0% (12/16) |
| Citation traceability | 100% | 100% |
| Answer correctness (group-reviewed) | ≥ 80% | 31.3% fully correct, 56.3% counting partly correct as half |
| Refusal on no-answer questions | report | 75% (3/4) |
| False refusals | — | 0% |
| Response time | report | mean 19.7 s, max 45.7 s |

The full report, including test conditions, error analysis and limitations, is in `evaluation/evaluation_report.md` and `evaluation/report.json`.

## Known limitations

- **14 books instead of 15.** The standard requires at least 15 unless the coordinator approves an exception; approval is pending.
- **Placeholders.** The group ID (`G000`) and embedding model are placeholders until the coordinator confirms them.
- **A small CPU model.** Llama 3.2 3B makes arithmetic mistakes and gives weak explanations for "why" and comparison questions. Answer correctness is well below target.
- **Slow comparisons.** Cross-book answers take 35–46 seconds on a CPU.
- **Keyword refusals.** Time-sensitive questions are refused by a keyword rule, not learned behaviour.
- **PDF page numbers.** Citations use PDF page numbers, not the numbers printed in the books.
- **Junk passages.** Four ISLR plot pages produced 211 passages of junk text (tick marks); they are still in the index.
- **Word ambiguity.** Matches like "transformers" and "transformations" can produce answers from the wrong concept.
- **Memory.** RAM use is high on a 12 GB laptop (about 93% for the whole system during evaluation), so close other apps before running.
- **No saved history.** Chat history is lost when the page is refreshed.

## Books

| ID | Title | Author(s) | Edition | Permission |
|---|---|---|---|---|
| G000_BOOK_001 | Linear Algebra Done Right | Sheldon Axler | 4th | Open access (Creative Commons) |
| G000_BOOK_002 | Pattern Recognition and Machine Learning | Christopher M. Bishop | 1st | Free PDF released by the author via Microsoft Research |
| G000_BOOK_003 | Mining of Massive Datasets | Leskovec, Rajaraman, Ullman | 2nd | Free download by agreement with the publisher |
| G000_BOOK_004 | Foundations of Data Science | Blum, Hopcroft, Kannan | June 2016 draft | Free draft posted by the authors |
| G000_BOOK_005 | Convex Optimization | Boyd, Vandenberghe | 1st | Free online with publisher permission |
| G000_BOOK_006 | Dive into Deep Learning | Zhang, Lipton, Li, Smola | Online | Open-source book, free online |
| G000_BOOK_007 | Speech and Language Processing | Jurafsky, Martin | 3rd draft (Aug 2026) | Free draft posted by the authors |
| G000_BOOK_008 | Introduction to Information Retrieval | Manning, Raghavan, Schütze | 1st | Free online from the authors' site |
| G000_BOOK_009 | An Introduction to Statistical Learning with Applications in R | James, Witten, Hastie, Tibshirani | 1st (7th printing) | Free PDF from the authors |
| G000_BOOK_010 | Mathematics for Machine Learning | Deisenroth, Faisal, Ong | 1st | Free for personal use |
| G000_BOOK_011 | OpenIntro Statistics | Diez, Çetinkaya-Rundel, Barr | 4th | Creative Commons license |
| G000_BOOK_012 | Grinstead and Snell's Introduction to Probability | Grinstead, Snell | 2nd | GNU Free Documentation License |
| G000_BOOK_013 | Understanding Machine Learning: From Theory to Algorithms | Shalev-Shwartz, Ben-David | 1st | Free download from the authors |
| G000_BOOK_014 | Introduction to Applied Linear Algebra | Boyd, Vandenberghe | 1st | Free online with publisher permission |

Full metadata, including source URLs, is in `data/book_manifest.json`.

## Team roles

| Member | Role |
|---|---|
| YANDE SICHULA | BACKEND DEVELOPER |
| FILL IN: partner's name | FILL IN |

## Copyright and data

The book PDFs, extracted text, passages and index aren't committed (see `.gitignore`), because they contain copyrighted text. They're rebuilt locally from the official sources listed in the manifest. The repository is private.
