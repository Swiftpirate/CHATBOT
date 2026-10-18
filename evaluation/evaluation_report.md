# Evaluation Report — DataSage (Group G000, Data Science)

> **Status: final (group-reviewed).** Answer correctness and citation support were marked against the reference answers. Marks were first suggested by an AI assistant, then reviewed and confirmed by the group in `answer_review_suggested.csv`. Instructor review is still pending. All other figures are measured.

## 1. Summary

| Measure | Target | Validation (final) | **Test (held-out)** |
|---|---|---|---|
| Retrieval Recall@5 | ≥ 80% | 85.7% (6/7) | **75.0% (12/16)** |
| Citation traceability | 100% | 100% | **100%** |
| Cited page matches labelled evidence | — | 83.3% (5/6) | **78.6% (11/14)** |
| Abstention on no-answer questions | report | 100% (3/3) | **75% (3/4)** |
| False refusals on answerable questions | — | 0% | **0%** |
| Uncited answers | — | 0% | **0%** |
| Answer correctness *(group-reviewed)* | ≥ 80% | 57.1% strict / 71.4% lenient | **31.3% strict / 56.3% lenient** |
| Response time (mean / median / max) | report | 8.6 / 10.4 / 21.8 s | **19.7 / 20.1 / 45.7 s** |

*Strict* counts only fully correct answers. *Lenient* counts "partly correct" as half.

The system meets the citation-traceability target and never refuses an answerable question. It falls short on held-out Recall@5 (75%) and, by a wide margin, on answer correctness. Most wrong answers come from the 3B model's arithmetic and reasoning rather than from retrieval.

## 2. Test conditions

- **Hardware:** Acer TravelMate P215-54, Intel Core i7-1255U, 12 GB RAM, no discrete GPU (CPU inference), Windows 11.
- **Software:** Python 3.14.7; PyMuPDF; sentence-transformers; FAISS; Ollama.
- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- **Generation model:** `llama3.2:3b` via Ollama, offline, `temperature 0`, `num_predict 300`, `num_ctx 2048`.
- **Chunking:** 180 words with 40-word overlap, chunks kept within one page.
- **Retrieval:** FAISS `IndexFlatIP` (cosine), top 2 passages; 2 per book when a question names books; minimum score 0.35.
- **Answer review:** each answer was marked yes / partly / no against the reference answer; marks were suggested by an AI assistant and confirmed by the group.
- **Benchmark:** 30 questions (10 validation, 20 held-out test) across six categories: direct facts, reasoning, numerical, cross-book comparison, no-answer, and citation traps. Questions and reference answers were drafted with an AI assistant, then reviewed and corrected by the group. Expected evidence pages were labelled by the group, assisted by AI-suggested labels that the group reviewed.
- **Recall@5 note:** measured with plain retrieval, without book filtering. The chatbot filters by named books, so its cross-book retrieval is better than this figure shows.
- **Runs:** final validation run 2026-10-17 10:36; test run 2026-10-17 10:47, run once after tuning finished.

## 3. Document processing

| Item | Result |
|---|---|
| Books in manifest | **14** (the standard requires 15; coordinator approval needed) |
| Books processed / failed | 14 / 0 |
| Total PDF pages | 7,928 |
| Nearly empty pages (< 50 characters) | 131: covers, blank pages and figures |
| Pages needing OCR | 0 (all PDFs are text-based) |
| Chunks indexed | 23,369 |
| Metadata completeness | Title, author, edition, publisher, year, source URL and permission status for all 14 books; ISBNs missing |

**Extraction issues found:**
- **Plot pages turned into junk text.** ISLR PDF pages 146, 282, 284 and 290 are plots whose tick marks were extracted as long runs of `| | |`. They produced **211 junk chunks**, 141 of them from page 146.
- **Flattened equations.** Formulas in maths-heavy books (Bishop, MML, Convex Optimization, UML) lose their structure in plain text.
- **PDF page numbers.** Citations use PDF page numbers, not the numbers printed in the books.

## 4. Validation tuning history

Tuning used only the 10 validation questions. The test set was run once, afterwards.

| Run | Change | Abstention | Recall@5 | Mean / max time |
|---|---|---|---|---|
| 1 | Baseline | 33.3% | 85.7% | 16.1 / 35.6 s |
| 2 | Stricter refusal rule; search by topic with book names removed; drop weak passages from named books | 66.7% | 85.7% | 15.2 / 36.1 s |
| 3 | Rule-based refusal of time-sensitive questions ("latest", "current", "today") before generation | **100%** | 85.7% | 8.6 / 21.8 s |

Part of run 3's speed-up comes from no-answer questions now being refused before the model runs, which takes about 0 seconds.

## 5. Results by category (test set)

| Category | Questions | Recall@5 | Correct (yes / partly / no) |
|---|---|---|---|
| Direct facts | Q002, Q004, Q006, Q008, Q009, Q010 | 6/6 | 4 / 1 / 1 |
| Reasoning | Q012–Q015 | 3/4 | 0 / 4 / 0 |
| Numerical | Q017–Q019 | 1/3 | 0 / 1 / 2 |
| Cross-book | Q021–Q023 | 2/3 | 1 / 2 / 0 |
| No-answer | Q026–Q028 | — | 3/3 correctly refused |
| Citation trap | Q030 | — | Failed: answered instead of refusing |

Direct-fact questions work well. Numerical and reasoning questions are where the system is weakest.

## 6. Efficiency

| Item | Value |
|---|---|
| Response time, test set | Mean 19.7 s, median 20.1 s, max 45.7 s (Q021, cross-book) |
| Typical single-topic answer | About 6–25 s; refusals before generation take about 0 s |
| Peak RAM | About 93% of 12 GB (about 11.2 GB) for the whole system during the test run; per-process RAM was not recorded |
| Generation model size | 2.0 GB (`llama3.2:3b`) |
| Embedding model size | 90.9 MB |
| FAISS index plus metadata | 61.0 MB |
| Chunks / extracted text / book PDFs | 25.1 MB / 18.8 MB / 179.2 MB |
| Failures on the target laptop | None; the system runs offline with no GPU |

## 7. Failures and error analysis

1. **Arithmetic (Q016–Q019).** The model gets calculations wrong even when the correct formula is retrieved. For Q018, it cited the right F1 formula but answered 0.8 instead of 0.615. For Q016 and Q017, no retrieved passage contained the answer, and the model copied numbers from nearby examples (1/4 for 2-toss sample spaces, 1/2). Textbooks explain basics briefly and then spend many pages on harder examples, so simple calculation questions tend to retrieve complex exercises.
2. **Word ambiguity (Q030).** "Transformers" matched OpenIntro's data "transformations" (log rescaling), so the chatbot answered from the wrong concept instead of refusing.
3. **Explanations not retrieved (Q013, Q011).** "Why" questions retrieve on-topic passages that don't contain the reasoning. D2L's section comparing CNNs, RNNs and self-attention exists but wasn't found.
4. **Cross-book crowding (Q020, Q021, Q023).** Without book filtering, one book's passages crowd out the other's. For Q023, no Linear Algebra Done Right passage appeared in the plain top 10. Book filtering fixes retrieval in the chatbot, but the model still sometimes attributes a claim to the wrong book (Q022, Q023).
5. **Wrong sense of a term (Q009).** "Inverted index" retrieved a web-link table instead of the standard term-to-postings index. During labelling, "bias" also matched the intercept term in a linear model.
6. **Instruction following (Q011, Q019, Q021, Q022).** Some sentences have no citation despite the prompt rule, and long comparison answers are cut off at the 300-token limit.
7. **Flawed reasoning behind correct conclusions (Q014, Q019).** The final answer is right, but the explanation misstates the maths, so these were marked "partly".

## 8. Limitations

- A 3B model on a CPU limits arithmetic, multi-step reasoning and comparison quality; cross-book answers take 35–46 s.
- The time-sensitive refusal is a keyword rule, not learned behaviour.
- With 20 test questions, one question moves a metric by 5–25 percentage points, so results are indicative, not precise.
- Answer correctness was reviewed by the group, not yet by the instructor or a subject expert.
- Citations use PDF page numbers.
- Junk chunks from plot pages remain in the index.
- The group ID (G000) and embedding model are placeholders until the coordinator confirms them. Changing either requires rebuilding the index and rerunning this evaluation.
- The manifest has 14 books; the standard requires 15 unless the coordinator approves an exception.

## 9. Suggested improvements

- Filter out symbol-heavy chunks (such as the plot tick marks) and rebuild the index.
- Route numerical questions through a calculator step instead of the language model.
- Retrieve more passages for "why" and comparison questions, or add a reranker.
- Test a larger or maths-stronger model (for example `qwen2.5:3b`, or a 7B model on a GPU) and compare it against these results.
- Store printed page numbers alongside PDF page numbers.

## Files

- `evaluation/report.json`: machine-readable version of this report
- `evaluation/report_test.json`, `evaluation/report_validation.json`: raw per-question results
- `evaluation/answer_review_suggested.csv`: per-answer review marks (suggested and confirmed)
- `data/evaluation_questions.json`: questions, reference answers, evidence labels and splits
