# Memory Lane RAG v1.1: Fixes, Datasets, and Re-evaluation

**Companion to `EVALUATION_REPORT.md` (audit of v1.0).** Date: 7 October 2026.
**Environment:** Ubuntu 24.04, Python 3.12.3, 1 vCPU, 3 GB RAM. Embeddings: WordLlama
(`l2_supercat`, 256-d, static). No paid LLM was available. The LLM-dependent experiments are
implemented and were tested only against a rule-based stand-in server (Section 7), so **no
answer-accuracy or hallucination numbers are reported here**.

Every number below is produced by a script in `scripts/` and stored in `results/`. Figures are
regenerated with `python scripts/make_figures.py`.

---

## 1. Summary

1. **All 21 audit findings are addressed** (Section 2). Tests went from 8/9 on a fresh checkout
   to 24/24, including 15 regression tests (one per fix). This includes a newly found critical bug:
   with an API key set, v1.0 never sent the retrieved evidence to the LLM.
2. **Retrieval improved significantly but does not beat plain BM25.** On LoCoMo conversations 6–10
   (held out from every selection step), v1.1 reaches Recall@5 **0.406**, against 0.334 for v1.0
   (p = 3.2×10⁻⁵). That is statistically on par with Okapi BM25 (0.425, p = 0.37) and a BM25 + dense
   hybrid (0.427, p = 0.12). Memory Lane's own FTS5 BM25 alone reaches **0.454**, the best of all
   systems. The dense channel (WordLlama over short memory units, 0.286 alone) still pulls the
   fusion down.
3. **Change detection improved substantially, within clear limits.** On the held-out MLLB-Synth test
   split, the v1.1 default compares with v1.0 as follows:
   - change-point F1: **0.351** vs 0.118;
   - reversals found: **44%** vs 20%;
   - false alarms on stable personas: **1.6%** vs 50%.
   With lexicon-style phrasing, F1 is 0.80 for listed topics and 0.60 for unlisted ones (v1.0: 0.00 on
   unlisted). With paraphrased stance it is **0.00**, because rule-based polarity cannot see it. The
   LLM extractor is the intended remedy and is the most important experiment still to run.
4. **Stratification has a coverage–precision trade-off, now measured.**
   - On MLLB-dev, always stratifying gives temporal coverage 0.977 against 0.865 without stratification.
   - On LoCoMo-dev, the same setting lowers fact-lookup Recall@5 from 0.403 to 0.309.
   - A selection rule fixed before running and applied only to dev data chose `router` as the default
     (coverage 0.917, no recall loss).
   - The modes `always` and `soft` remain available for purely longitudinal workloads.
   - A better intent classifier is the clear next step.
5. **Ingestion is no longer quadratic.** v1.1 needs 14–24 ms per document from 250 to 10,000
   documents. v1.0 needed 265, 514 and 985 ms at 250, 500 and 1,000 documents (doubling with corpus
   size; 65× slower than v1.1 at 1,000).
   Retrieval p50 at 10,000 documents is 99 ms. A new cost: storage is about 12 KB per document,
   because the text is kept alongside the vectors.

---

## 2. Changes (git: `0eb0eba original v1.0.0` → `HEAD`; see `memory_lane_v1.1.patch`)

| Audit finding | v1.1 change | Verified by |
|---|---|---|
| A1/A2 hashed "embeddings", unused model setting | `storage/embeddings.py`: backends `wordllama` (default), `st:<model>` (sentence-transformers, e.g. BGE-M3, Qwen3-Embedding), `openai:<model>`, `hash` (v1.0 function, ablation only) | `test_default_embedder_is_not_word_hashing`, `test_hash_backend_preserved_for_ablation` |
| A3/A4 unused fusion weights, no temporal list | Unused weights removed; `RRF_K` setting; documentation now matches the code (dense + sparse RRF) | code |
| A5 "temporal" pipeline = Memory Lane | Real temporal baseline: dense top-k + date filter + chronological order, no change analysis | `test_temporal_pipeline_differs_from_memory_lane` |
| A6/A7 keyword-gated, calendar-year epochs | `STRATIFICATION_MODE` = router / always / soft / off (also per request); `EPOCH_MODE` = adaptive / year; default chosen by a fixed rule on dev data (Section 5) | `test_adaptive_epochs_*`, `test_default_stratification_*` |
| A8 lexicon-bound extraction | Optional LLM extractor (`ML_EXTRACTOR=llm`); query-focused change and reversal detection (tracks the subject named in the query); only stance-bearing memories compared | `test_query_focused_change_detection_*` |
| A10–A12 metrics fixed by construction | COA on the claim order of LLM answers (undefined for the deterministic synthesizer); UHCR undefined for the deterministic synthesizer; Change-F1 with topic matching and year tolerance, undefined when both sides are empty | `test_metrics_no_longer_fixed_by_construction`, `test_change_f1_*` |
| A14 invented token count | Removed (0 unless measured) | code |
| A15 wrong reversal direction | Rationale states the actual direction | `test_contradiction_message_reports_true_direction` |
| A16 chunk vectors tagged `default_user` | `user_id` passed through | `test_chunk_vectors_carry_user_id_*` |
| A17 upload overwrite | Unique file names per upload | same test |
| A18 queries wrote to the DB | Query-time analysis is read-only (`ML_PERSIST_ANALYSIS=1` restores the old behaviour); whole-archive analysis still persists | `test_query_focused_*` (row count unchanged) |
| A19 O(N²) JSON rewrite, cross-user scan | Vectors in SQLite (`vectors` table, written in the document's transaction), per-user cached matrix, one matrix product per query | `test_vector_store_*`, Section 6 |
| A20 README endpoint 404 | `/api/research/run-benchmark` alias | `test_documented_benchmark_endpoint_exists` |
| **A21 (new): LLM never saw the evidence** | Prompt now contains the evidence (id, date, type, statement, source), detected changes and the JSON output contract; citations to ids that were not retrieved are stripped (so the claim counts as unsupported) | `test_llm_prompt_contains_evidence_and_bogus_citations_are_stripped` |
| Tests depended on leftover state | `conftest.py`: temporary data directory per session; LLM disabled in unit tests | 24/24 on a fresh checkout |
| Deleting a document left TMU full-text rows | Removed in the same transaction | code |

**Thresholds chosen on dev data only:** the drift threshold of 0.70 (v1.0: 0.42) maximises
change-point F1 on MLLB-dev (0.344 vs 0.241; `results/drift_calibration_dev.json`). It depends on the
embedder: re-run `scripts/calibrate_drift.py` after changing `ML_EMBEDDING_BACKEND`.

---

## 3. Datasets

**MLLB-Synth v1** (`data/mllb_synth_v1/`, card: `DATASET_CARD.md`): 224 personas, 5,376 dated
documents, 704 queries, generated by `scripts/build_mllb_synth.py`.
- **`dev`:** 96 personas. Byte-identical to the corpus of the v1.0 audit, and used for development
  and calibration.
- **`test`:** 128 personas, held out. Its topics, every sentence template and two of four query
  styles are new, and it adds 32 stable-stance controls for measuring false alarms.

**MLLB-Human kit** (`annotation_kit/`): guidelines, templates, sentence segmentation,
inter-annotator agreement (Cohen's κ for memory type; quadratic-weighted κ, Krippendorff's α and
sign agreement for polarity; transition F1 between annotators) and a converter into the MLLB format
(`--split human`). It was tested end to end on a two-persona example that is marked as illustration
only. **The human-written data itself must be collected by people** (Section 9).

---

## 4. Re-evaluation on MLLB-Synth (held-out test split, 512 queries, top_k = 8)

| System | TCR uniform | TCR skewed | CP-F1 | CP-F1 ±1 yr | Reversals found | False alarms (stable) | Changes / query |
|---|---|---|---|---|---|---|---|
| v1.0 baseline | 0.92 | 0.76 | – | – | – | – | 0 |
| v1.0 Memory Lane | 0.97 | 0.89 | 0.118 [0.102, 0.133] | 0.153 | 0.198 | 0.500 [0.414, 0.586] | 2.74 |
| v1.1 baseline (dense) | 0.93 | 0.71 | – | – | – | – | 0 |
| v1.1 temporal RAG | 0.93 | 0.71 | – | – | – | – | 0 |
| **v1.1 Memory Lane (default: router)** | 0.94 | 0.86 | **0.351 [0.303, 0.397]** | 0.411 | **0.440** | **0.016 [0.000, 0.039]** | 0.35 |
| v1.1 ML, always | 0.96 | 0.98 | 0.368 | 0.454 | 0.487 | 0.023 | 0.39 |
| v1.1 ML, always + year bins | 1.00 | 1.00 | 0.361 | 0.454 | 0.487 | 0.023 | 0.39 |
| v1.1 ML, always, no query focus | 0.96 | 0.98 | 0.203 | 0.245 | 0.487 | 0.000 | 0.19 |
| v1.1 ML, always, hash vectors | 0.97 | 0.98 | 0.226 | 0.300 | 0.495 | 0.414 | 1.18 |

TCR rows: overall 95% CIs in `results/mllb_summary.json`. The v1.1 temporal RAG matches the dense
baseline on TCR because both retrieve the same top-k; it differs only in ordering and date filtering.

**By condition (v1.1 default, change-point F1 / reversals found):**

| | Listed phrasing | Paraphrase |
|---|---|---|
| Listed topic | 0.80 / 0.92 | 0.00 / 0.00 |
| Unlisted topic | 0.60 / 0.84 | 0.00 / 0.00 |

The corresponding v1.0 values are 0.24/0.79, 0.23/0.00, 0.00/0.00 and 0.00/0.00.

**By query style (v1.1 default, TCR / F1):**

| Query style | TCR | F1 |
|---|---|---|
| evolution | 0.97 | 0.48 |
| history | 0.97 | 0.48 |
| when-changed | 0.86 | 0.33 |
| plain ("What do I think about X?") | 0.81 | 0.12 |

The router does not recognise the plain style, which is the main argument for a learned intent classifier.

**Ablations, in short:**
- Query focus is responsible for most of the F1 gain (0.203 → 0.368).
- The real embedding plus the calibrated threshold removes the false alarms (0.414 → 0.023).
- Calendar-year bins maximise year-based TCR (the metric itself counts calendar years).
- Adaptive bins are what make single-year histories stratifiable (unit test); they cost 0.02–0.04 TCR here.

---

## 5. Choosing the stratification default (dev data only)

**Rule, written before any run** (`scripts/select_stratification.py`): choose the mode with the
highest MLLB-dev TCR, subject to LoCoMo-dev Recall@5 (conversations 1–5) being no more than 0.01
below `off`.

| Mode | LoCoMo-dev R@5 | MLLB-dev TCR |
|---|---|---|
| off | 0.403 | 0.865 |
| **router (selected)** | **0.403** | **0.917** |
| soft 0.75 | 0.384 | 0.958 |
| soft 0.50 | 0.334 | 0.977 |
| soft 0.25 | 0.308 | 0.969 |
| always | 0.309 | 0.977 |

See `figures/fig4_stratification_tradeoff.png`. No mode reaches both high coverage and full
fact-lookup recall. This is a central, reportable result: temporal diversity and point relevance
compete for the same k slots, so the gate that decides between them matters as much as the sampler.

---

## 6. LoCoMo evidence retrieval (1,536 questions; turn-level Recall@k)

| System | R@5 all | R@5 held out (conv 6–10, n = 776) | R@10 all | p50 ms |
|---|---|---|---|---|
| Most-recent turns | 0.007 | 0.009 | 0.018 | 0.2 |
| v1.0 Memory Lane (as shipped) | 0.334 | 0.334 [0.302, 0.366] | 0.401 | 64.8* |
| v1.1 ML: always | 0.311 | 0.312 | 0.379 | 42.5 |
| v1.1 ML: hash vectors (always) | 0.264 | 0.257 | 0.339 | 43.9 |
| v1.1 ML: dense only | 0.293 | 0.286 | 0.346 | 17.7 |
| **v1.1 ML: default (router)** | **0.404** | **0.406 [0.374, 0.440]** | 0.467 | 42.5 |
| WordLlama dense (turns) | 0.340 | 0.313 | 0.413 | 1.6 |
| BM25 (turns) | 0.435 | 0.425 [0.393, 0.457] | 0.515 | 1.4 |
| BM25 + WordLlama RRF (turns) | 0.443 | 0.427 [0.394, 0.460] | 0.521 | 1.7 |
| **v1.1 ML: FTS5 BM25 only** | **0.447** | **0.454 [0.420, 0.487]** | 0.515 | 29.6 |

\* v1.0 latency from the original audit run.

Paired Wilcoxon tests on held-out R@5, against the v1.1 default:

| Comparison | p |
|---|---|
| v1.0 | 3.2×10⁻⁵ (v1.1 better) |
| BM25 | 0.37 |
| BM25 + dense hybrid | 0.12 |
| FTS5-only | 0.004 (FTS5-only better) |

---

## 7. LLM-dependent experiments: implemented and tested, not yet run

| Script | Measures | Tested here with |
|---|---|---|
| `eval_llm_qa.py` | End-to-end QA on LoCoMo / LongMemEval. Same reader and judge for memory_lane, ml_dense, turn_bm25, full_context and **mem0**. Reports J (LLM judge, repeatable `--judge_runs`), token F1, BLEU-1, context tokens and latency; resumable | stand-in server: 5 systems × 20 questions, 2 judge runs; resume made 0 new calls |
| `eval_llm_grounding.py` | Claim-level grounding of Memory Lane's own LLM synthesis on MLLB: unsupported-claim rate (judge checks claim against cited evidence), invalid-citation rate, COA on claim order, whether a reversal is stated (also on stable controls) | stand-in server with `ML_EXTRACTOR=llm` and `ML_EMBEDDING_BACKEND=openai:...`; a planted fake citation was stripped and counted as unsupported |
| `bench_conversations.py --dataset longmemeval` | Session-level Recall/NDCG on LongMemEval | fixture in the official file format (abstention items skipped) |

The stand-in server (`scripts/dev/mock_openai_server.py`) is rule-based. Numbers obtained with it
are meaningless and are not reported.

**For a fair Mem0 comparison:**
- Install `mem0ai[nlp,extras]`; otherwise Mem0 2.x silently disables its keyword search.
- The open-source SDK does not accept event timestamps and dates every memory "today". The adapter
  therefore prefixes each message with its real date. State this as a limitation.

**Not implemented:** adapters for Zep/Graphiti (needs Neo4j) and A-MEM. Quote their published
numbers as "reported", or run them through their official harnesses with the same judge model.

---

## 8. Scaling (idle CPU, persistence on, 5 users)

| Documents | v1.0 ingest / doc | v1.1 ingest / doc | v1.0 query p50 | v1.1 query p50 | v1.1 store |
|---|---|---|---|---|---|
| 250 | 265 ms | 14 ms | 30 ms | 32 ms | 3.2 MB |
| 500 | 514 ms | 14 ms | 38 ms | 33 ms | 6.1 MB |
| 1,000 | 985 ms | 15 ms | 50 ms | 53 ms | 12 MB |
| 2,000 | – | 17 ms | – | 42 ms | 24 MB |
| 5,000 | – | 23 ms | – | 59 ms | 59 MB |
| 10,000 | – | 24 ms | – | 99 ms | 118 MB |

v1.0 was not run beyond 1,000 documents because its per-document cost grows linearly (quadratic in
total). Remaining v1.1 costs: one SQLite lookup per candidate memory at query time, and storage of the
text alongside the vectors.

---

## 9. What still requires you

1. **LLM runs (needs an API key or a local OpenAI-compatible server):**
   - `eval_llm_qa.py` on LoCoMo (all 1,540) and LongMemEval_S, for GPT-4o-mini and one open model.
   - `eval_llm_grounding.py --split test`.
   - The MLLB evaluation with `ML_EXTRACTOR=llm`, which is the decisive test of paraphrase generalisation.
2. **LongMemEval data** from HuggingFace (`xiaowu0162/longmemeval-cleaned`).
3. **Stronger embeddings:** `ML_EMBEDDING_BACKEND=st:BAAI/bge-m3` (or `st:Qwen/Qwen3-Embedding-0.6B`).
   Then re-run `calibrate_drift.py` and `select_stratification.py`, and only then the test-split evaluations.
4. **MLLB-Human:** recruit writers or volunteers and two annotators who are not the developers. Report
   agreement, adjudicate, convert, evaluate, and freeze before any further change.
5. **Zep/Graphiti and A-MEM:** official harnesses, same judge model.

## 10. Threats to validity

- **MLLB-Synth is template text.** The test split guards against tuning, but not against the
  simplicity of the language. LoCoMo results are retrieval-only.
- **The drift threshold and stratification mode were selected on dev data.** The LoCoMo dev/test split
  is by conversation (5/5), so the held-out sample is small (776 questions; CIs about ±0.033).
- **WordLlama is a weak embedder.** Conclusions about dense fusion may change with BGE-M3/Qwen3.
- **Latencies come from one machine with one core.** Absolute values will differ; the scaling trends
  are the result.
