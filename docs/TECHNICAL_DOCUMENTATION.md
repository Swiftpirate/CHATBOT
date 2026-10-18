# Technical Documentation — DataSage (Group G000, Data Science)

This document records the models, versions, configuration, prompts, retrieval settings, dependencies and limitations of the chatbot, so that the system can be rebuilt and its results reproduced. It covers item 4 (environment/config) and item 8 (index build instructions) of the required submission package.

The settings here match `config/config.json` and the source code; `tests/test_config.py` checks that they stay in sync.

## 1. System overview

| Stage | Script | Input | Output |
|---|---|---|---|
| 1. Ingestion | `src/ingest.py` | `data/books/*.pdf` | `data/extracted/<book_id>.jsonl` (one record per PDF page) |
| 2. Chunking | `src/chunk.py` | extracted pages | `data/chunks.jsonl` (23,369 passages) |
| 3. Indexing | `src/build_index.py` | passages | `data/index/faiss.index` and `data/index/chunks_meta.jsonl` |
| 4. Retrieval | `src/retrieve.py` | question | top-k passages with book, page and chunk ID |
| 5. Generation | `src/generate.py` | question + passages | answer, sources, insufficient-evidence flag |
| 6. Interface | `src/app.py` | user questions | Streamlit chat app |

## 2. Models and versions

### Embedding model

| Property | Value |
|---|---|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Revision (Hugging Face commit) | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| Library | sentence-transformers 6.1.0 |
| Embedding size | 384 dimensions |
| Maximum input | 256 word pieces; longer text is cut off, which is why passages are limited to 180 words |
| Normalisation | Embeddings are L2-normalised, so the inner product equals cosine similarity |
| Download size | About 90.9 MB |
| License | Apache 2.0 |
| Status | **Placeholder** until the project coordinator confirms the approved embedding model |

### Generation model

| Property | Value |
|---|---|
| Model | `llama3.2:3b` (Meta Llama 3.2, 3 billion parameters, instruction-tuned, 4-bit quantized) |
| Runtime | Ollama 0.40.5, running locally |
| Model blob digest | `dde5aa3fc5ff` (as shown by `ollama pull`) |
| Download size | About 2.0 GB |
| Python client | `ollama` 0.6.3 |
| License | Llama 3.2 Community License |
| Hardware | CPU only; no GPU used |

To record the exact model digest on your machine, run `ollama list`.

## 3. Configuration

### Ingestion (`src/ingest.py`)

| Setting | Value |
|---|---|
| PDF library | PyMuPDF 1.28.2 (`page.get_text()`) |
| Book order | PDFs sorted by filename; book IDs assigned in that order (`G000_BOOK_001` to `G000_BOOK_014`) |
| Page numbers | PDF page numbers, starting at 1 (not printed page numbers) |
| Nearly empty page | Fewer than 50 characters; counted and reported, not removed |
| OCR | Not used; all 14 PDFs are text-based |

### Chunking (`src/chunk.py`)

| Setting | Value |
|---|---|
| Passage size | 180 words |
| Overlap | 40 words (each passage starts 140 words after the previous one) |
| Page boundary | Passages never cross pages, so every passage has exactly one page number |
| Skipped pages | Pages with fewer than 20 words |
| Passage ID format | `<book_id>_P<page>_C<chunk number>`, e.g. `G000_BOOK_009_P51_C02` |
| Passage fields | `group_id`, `subject`, `book_id`, `title` (source filename), `page`, `chunk_id`, `text` |

### Index (`src/build_index.py`)

| Setting | Value |
|---|---|
| Index type | FAISS `IndexFlatIP` (exact search, no approximation) |
| Similarity | Cosine (inner product of normalised vectors) |
| Vectors | 23,369 × 384 |
| Encoding batch size | 64 |
| Files | `data/index/faiss.index` (35.9 MB), `data/index/chunks_meta.jsonl` (25.1 MB) |
| Build time | About 16 minutes on an Intel Core i7-1255U CPU |

## 4. Retrieval settings

| Setting | Value | Where |
|---|---|---|
| Passages per normal question | 2 (`TOP_K`) | `generate.py` |
| Passages per named book | 2 (`PER_BOOK`) | `generate.py` |
| Minimum relevance score | 0.35 (`MIN_SCORE`); below this the chatbot refuses | `generate.py` |
| Default for `retrieve()` | `top_k=5` (used for Recall@5 and labelling) | `retrieve.py` |

**Book filtering.** If a question names a book, the book names are removed from the question, the remaining topic is searched, and only passages from the named books are kept. Each named book contributes up to 2 passages, and only those scoring at least 0.35. Recognised names:

| Book file | Names recognised in a question |
|---|---|
| `978-3-031-41026-0.pdf` | linear algebra done right, axler |
| `Bishop-Pattern-Recognition-and-Machine-Learning-2006.pdf` | bishop, prml, pattern recognition and machine learning |
| `book.pdf` | mining of massive datasets, mmds, leskovec, ullman |
| `book2016June9.pdf` | foundations of data science, hopcroft, kannan |
| `bv_cvxbook.pdf` | convex optimization |
| `d2l-en.pdf` | dive into deep learning, d2l |
| `ed3book_aug26.pdf` | speech and language processing, jurafsky |
| `irbookprint.pdf` | introduction to information retrieval, ir book, manning |
| `ISLR+Seventh+Printing.pdf` | islr, isl, introduction to statistical learning |
| `mml-book.pdf` | mathematics for machine learning, mml, deisenroth |
| `os.pdf` | openintro |
| `prob.pdf` | grinstead, snell |
| `understanding-machine-learning-theory-algorithms.pdf` | understanding machine learning, shalev-shwartz, ben-david |
| `vmls.pdf` | applied linear algebra, vmls |

## 4a. Embedding and retrieval pipeline

### Building the index (offline, once)

1. **Load passages.** `build_index.py` reads all 23,369 passages from `data/chunks.jsonl`.
2. **Embed.** Each passage's text is encoded by `all-MiniLM-L6-v2` into a 384-number vector that represents its meaning. Passages are processed in batches of 64. Text beyond 256 word pieces is cut off by the model.
3. **Normalise.** Every vector is scaled to length 1 (`normalize_embeddings=True`), so the inner product of two vectors equals their cosine similarity.
4. **Index.** The vectors are added, in passage order, to a FAISS `IndexFlatIP`. Vector number *i* in the index corresponds to line *i* of `chunks_meta.jsonl`.
5. **Save.** `faiss.index` stores the vectors; `chunks_meta.jsonl` stores each passage's text, book ID, source file, page and chunk ID.

### Answering a question (online, every question)

1. **Time-sensitive check.** If the question contains a word such as "latest" or "today", the chatbot refuses immediately (see section 7).
2. **Book detection.** The question is checked against the book-name list (section 4). If books are named, their names are removed from the question so the search matches the topic, not the title.
3. **Embed the question.** The question (or the topic, if books were named) is encoded with the same model and normalised, giving one 384-number vector.
4. **Search.** FAISS compares the question vector with all 23,369 passage vectors and ranks them by cosine similarity, from 1 (identical meaning) down. The search is exact, not approximate.
   - **Normal question:** the top 2 passages are kept.
   - **Named books:** the whole ranking is scanned and the top 2 passages *from each named book* are kept, dropping any below 0.35.
5. **Relevance check.** If the best remaining passage scores below 0.35, the chatbot refuses.
6. **Look up sources.** Each kept vector's position is used to fetch its passage text, book ID, page and chunk ID from `chunks_meta.jsonl`.
7. **Build the prompt.** The passages are numbered [1], [2]… and labelled with the book title (from the manifest) and PDF page, then inserted into the prompt (section 6).
8. **Generate and check.** The model writes the answer; citations are then checked and cleaned (section 7).

### `retrieve()` interface

```python
retrieve(question: str, top_k: int = 5, books: set | None = None) -> list[dict]
```
Returns up to `top_k` passages, highest score first:
```json
{"text": "...", "score": 0.61, "book_id": "G000_BOOK_003", "title": "book.pdf", "page": 183, "chunk_id": "G000_BOOK_003_P183_C03"}
```
`title` holds the source filename; the readable book title comes from `data/book_manifest.json`. If `books` is given, only passages from those source files are returned.

### Typical scores

| Situation | Best score |
|---|---|
| Clear textbook topic (for example "What is PageRank?") | About 0.70–0.75 |
| Related but indirect topic | About 0.45–0.60 |
| Off-topic question (sport, cooking, politics) | Below 0.35, so the chatbot refuses |

## 5. Generation settings

| Setting | Value | Effect |
|---|---|---|
| `temperature` | 0 | Same question gives the same answer every time |
| `num_predict` | 300 | Maximum answer length in tokens |
| `num_ctx` | 2048 | Context window (prompt + passages + answer) |
| `keep_alive` | 30 minutes | Model stays loaded between questions |
| `stream` | true | Answer appears word by word |

## 6. Prompt

Each retrieved passage is labelled with a number, the book title and the PDF page:

```
[1] (Mining of Massive Datasets, PDF page 183)
<passage text>
```

The full prompt sent to the model:

```
You answer questions using ONLY the numbered book passages below.

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
Answer:
```

Short numbers like `[1]` are used instead of full passage IDs because the 3B model copied long IDs unreliably during development.

## 7. Safeguards (applied in code, after or before the model)

| Safeguard | When | Behaviour |
|---|---|---|
| Time-sensitive refusal | Before retrieval | Questions containing *latest, newest, most recent, current version, right now, today, this year, nowadays* are refused without calling the model |
| Low-relevance refusal | After retrieval | If no passage scores at least 0.35, the chatbot refuses |
| Model refusal | After generation | If the answer starts with `INSUFFICIENT EVIDENCE`, the standard refusal is returned |
| Citation splitting | After generation | `[1, 2]` is rewritten as `[1][2]` |
| Invented citation removal | After generation | Citation numbers that don't match a retrieved passage are deleted |
| Unverified answer flag | After generation | Answers with no valid citation get a warning |

**Refusal text:** "The provided books do not contain enough evidence to answer this question."

**Answer format** (returned by `answer()`):
```json
{
  "answer": "text with [1] style citations",
  "sources": [{"n": 1, "book_id": "...", "title": "...", "author": "...", "edition": "...", "page": 183, "chunk_id": "..."}],
  "insufficient_evidence": false
}
```

## 8. Dependencies

### Runtime environment

| Component | Version |
|---|---|
| Operating system | Windows 11 (build 26200) |
| Python | 3.14.7 |
| Ollama | 0.40.5 |
| Git | Used for version control |

### Main Python packages (pinned in `requirements.txt`)

| Package | Version | Used for |
|---|---|---|
| pymupdf | 1.28.2 | PDF text extraction |
| sentence-transformers | 6.1.0 | Embedding model |
| transformers | 5.20.0 | Model loading (used by sentence-transformers) |
| torch | 2.14.1 | Neural network runtime, CPU |
| huggingface_hub | 1.33.0 | Model download |
| faiss-cpu | 1.15.1 | Vector index and search |
| numpy | 2.5.4 | Arrays |
| ollama | 0.6.3 | Talking to the local language model |
| streamlit | 1.66.0 | Chat interface |
| pytest | 9.1.1 | Automated tests |
| pytesseract | 0.3.13 | Installed for OCR; not used (no scanned books) |

All other packages in `requirements.txt` are dependencies of these. Install them with:
```
pip install -r requirements.txt
```

## 9. Rebuilding the index (reproducible instructions)

1. Create the environment: `python -m venv venv`, `venv\Scripts\activate`, `pip install -r requirements.txt`.
2. Install Ollama and run `ollama pull llama3.2:3b`.
3. Download each book from the `source_url` in `data/book_manifest.json` into `data/books/`, using the exact `source_file` name. Book IDs depend on filename order, so every file must be present and correctly named.
4. Run, in order:
   ```
   python src\ingest.py
   python src\chunk.py
   python src\build_index.py
   ```
5. Expected results: 14 books, 7,928 pages, 23,369 passages, an index of 23,369 vectors.
6. Verify with `python -m pytest tests -v` (expected: 32 passed, 1 expected failure for the 15-book minimum).

If the embedding model or chunk settings change, steps 4–6 must be repeated, and the evaluation must be rerun.

## 10. Hardware and performance

| Item | Value |
|---|---|
| Laptop | Acer TravelMate P215-54 |
| CPU | Intel Core i7-1255U (10 cores) |
| RAM | 12 GB |
| GPU | Integrated graphics only; not used |
| Answer time (test set) | Mean 19.7 s, median 20.1 s, max 45.7 s |
| Peak system RAM during evaluation | About 93% of 12 GB |

## 11. Limitations

- **Placeholders.** The group ID (`G000`) and the embedding model await coordinator confirmation. Changing either requires rebuilding the index.
- **14 books.** The standard requires 15 unless the coordinator approves an exception.
- **Model quality.** Llama 3.2 3B makes arithmetic errors and gives weak explanations for "why" and comparison questions; answer correctness on the test set was 31.3% (fully correct).
- **Retrieval.** Recall@5 on the test set was 75%, below the 80% target. Simple calculation and "why" questions often retrieve examples instead of explanations.
- **Word ambiguity.** Similar words can retrieve the wrong concept (for example "transformers" and "transformations").
- **Keyword rules.** Time-sensitive refusals and book-name detection use fixed word lists, not learned behaviour; unlisted names or phrasings aren't recognised.
- **Page numbers.** Citations use PDF page numbers, not printed page numbers.
- **Extraction quality.** Four ISLR plot pages produced 211 junk passages; equations in maths-heavy books are flattened into plain text.
- **Truncation.** Passages longer than the embedding model's input limit are cut off; long answers are cut off at 300 tokens.
- **Speed and memory.** Cross-book answers take 35–46 seconds on a CPU, and RAM use is high on a 12 GB laptop.
- **Dependency on Ollama.** The chatbot fails with a connection error if Ollama isn't running.
- **Chat history.** Conversations are lost when the page is refreshed.
