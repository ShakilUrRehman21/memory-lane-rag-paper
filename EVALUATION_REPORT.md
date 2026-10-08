# Memory Lane RAG — Independent Code Audit, Testing and Benchmark Report

> **Note:** this is the audit of v1.0 as originally shipped. All issues listed here are addressed in v1.1; see `EVALUATION_REPORT_v1.1.md`. Raw files for this report are in `results/v1.0_audit/`.

**Subject:** `memory-lane-rag-main` (GitHub: ShakilUrRehman21/memory-lane-rag), v1.0.0 as shipped in the uploaded zip
**Date of evaluation:** 7 October 2026
**Environment:** Ubuntu 24.04, Python 3.12.3, 1 vCPU, 3 GB RAM; fastapi 0.142, pydantic 2.13, numpy 2.4, pytest 9.1. No LLM API key was configured, so every run used the system's built-in deterministic synthesizer. All retrieval numbers are independent of the LLM.

Every number in this report was produced by the scripts in `scripts/`. The raw outputs are in `results/`.

---

## 1. Summary

1. **The README's results table cannot be reproduced from the shipped code.** Running the repo's own benchmark on a fresh database gives Change-Point F1 = 0.389 (README: 0.92). Chronological Ordering Accuracy is 1.00 for *every* pipeline, including the baseline (README: 0.40 for the baseline).
2. **Several described components are not implemented as described:**
   - The "semantic" vectors are word-hash features, not a neural embedding.
   - The "Temporal RAG" pipeline is the same code path as "Memory Lane RAG".
   - The RRF has no temporal ranking list.
   - Three retrieval weights in `config.py` are never used.
3. **Three of the four in-repo metrics are fixed by construction** (ordering accuracy, hallucination rate, and Change-F1 on queries with no ground-truth changes).
4. **Real, statistically supported result: period-stratified retrieval removes temporal coverage loss under density skew.** On 96 controlled personas with evolution-phrased queries, Temporal Coverage Recall rises from 0.729 [0.691, 0.771] to 1.000 when the final year is over-represented (Wilcoxon p = 1.6 × 10⁻⁹). This is the claim the paper can be built on.
5. **That gain depends on keyword routing.** With the plain question "What do I think about X?", the benefit disappears (0.764 vs 0.778, p = 0.58). On LoCoMo, 0 of 1,540 answerable questions trigger the stratification path.
6. **Change and reversal detection depend on hard-coded lexicons.** Reversals are detected in 100% of cases when the topic and phrasing are in the lexicon, and in 0% otherwise. Change-point F1 is at most 0.29, with about 6 changes flagged per query against 1 true change.
7. **On the public LoCoMo benchmark the full pipeline retrieves worse than plain BM25:** Recall@5 0.334 vs 0.435. Using the system's own FTS5 BM25 alone gives 0.448. The hashed vectors are what pull the fused ranking down; swapping in a real embedding (WordLlama) raises the full pipeline to 0.404.
8. **Engineering:**
   - 8 of 9 tests pass on a fresh database; the suite reaches 9/9 only on a second run.
   - Coverage is 74%.
   - Ingestion time per document grows linearly with corpus size (quadratic total) because the whole vector file is rewritten on every insert.
   - The README's benchmark endpoint returns HTTP 404.

---

## 2. Code audit (verified against source)

| # | Finding | Evidence (file:line) | Consequence for the paper |
|---|---|---|---|
| A1 | The "dense embedding" is feature hashing: each word is MD5-hashed and each 3-character prefix SHA-256-hashed into 384 slots, plus fixed +2.0 boosts for 11 hand-picked words ("ai", "java", "python", "goal", …). | `storage/vector_store.py:33`, `:42` | Must not be described as semantic or neural embedding. Drift Δ = 1 − cos(e_i, e_j) measures word overlap, not meaning. |
| A2 | `EMBEDDING_MODEL = "text-embedding-3-small"` is declared but never used anywhere. | `core/config.py:19` | Misleading configuration; remove it or implement it. |
| A3 | `BM25_WEIGHT`, `SEMANTIC_WEIGHT` and `TEMPORAL_WEIGHT` are declared but never read. | `core/config.py:29–31` | The weighted fusion described in the docs does not exist. |
| A4 | RRF (k = 60) fuses only the dense and sparse ranked lists. There is no temporal ranking list; "temporal" influence comes only from type/polarity multipliers (+0.25 / +0.20). | `retrieval/reranker.py:16` | The formula RRF = Σ over {dense, sparse, temporal} in the README is inaccurate. |
| A5 | Only `pipeline_mode == "baseline"` is checked. `"temporal"` and `"memory_lane"` execute identical code. | `synthesis/grounded_synthesizer.py:34–36` | The three-way comparison is really two-way. The README describes Temporal RAG as "Vector + Date Filter/Sort", which is not implemented. |
| A6 | Stratified sampling runs only when a keyword-based router labels the query as evolution, timeline or change-point. | `retrieval/hybrid_retriever.py:93`, `retrieval/query_router.py` | The core contribution is gated by surface phrasing (see E2, E3). |
| A7 | Epochs are calendar years (`dt[:4]`). | `retrieval/stratified_sampler.py:27` | No effect on histories inside one year (all of LoCoMo). Bin granularity should adapt to the data. |
| A8 | TMU extraction is fully rule-based: sentence split, memory type by keyword lists, polarity from 16 negative and 15 positive regexes, entities from a fixed list of 39 terms. Many phrases appear verbatim in the benchmark corpus ("don't think", "started learning", "stopped using"). | `ingestion/tmu_extractor.py:7`, `:15`, `:112`, `:119` | Polarity and entity extraction do not generalise (E2). There is risk of tuning to the test set. |
| A9 | Sentences of 15 characters or fewer are dropped. | `ingestion/tmu_extractor.py:47` | 12 of 5,882 LoCoMo turns produced no memory at all. |
| A10 | The timeline is always sorted by date before metrics are computed. | `synthesis/grounded_synthesizer.py:53` | COA = 1.0 for every pipeline by construction. |
| A11 | UHCR counts claims that have no evidence IDs; the deterministic synthesizer always attaches IDs. | `evaluation/metrics.py:72`, `synthesis/llm_provider.py` | UHCR = 0.0 by construction; it does not measure hallucination. |
| A12 | Change-F1 returns 1.0 when there is no ground truth and nothing is detected. | `evaluation/metrics.py:46` | The baseline (detector off) gets free credit on query q3. |
| A13 | The in-repo benchmark has 5 documents (about 60 words each) and 3 queries. | `evaluation/benchmark_dataset.py` | Far too small for statistical claims. |
| A14 | Token usage is estimated as `words × 1.3 + 350`. | `evaluation/experiment_runner.py:74` | Not a measured quantity; do not report it as cost. |
| A15 | The contradiction rationale always says "polarity was negative … became positive", whatever the actual direction. | `reasoning/contradiction_detector.py:54` | User-facing misinformation for positive→negative reversals. |
| A16 | `insert_chunks` is called without `user_id`, so every chunk vector is tagged `default_user`. | `ingestion/ingestion_service.py:71` | User-isolation metadata is wrong for chunks. |
| A17 | Uploaded text is saved as `<sanitised title>.txt` in one shared folder. | `ingestion/ingestion_service.py:114` | Documents with the same title from different users overwrite each other on disk. |
| A18 | Change points and relationships are written to the database during *queries*. | `reasoning/change_detector.py:101`, `reasoning/contradiction_detector.py:74` | Read operations have side effects; state accumulates across benchmark runs. |
| A19 | Vector search loops in Python over *all* users' vectors, then filters. The whole JSON vector file is rewritten after each document. | `storage/vector_store.py:73`, `storage/repository.py:303` | Linear query cost in total corpus size; quadratic total ingestion cost (E4). |
| A20 | The README documents `POST /api/research/run-benchmark`; the actual route is `/api/research/benchmark`. | README line 366; `api/routes_research.py` | The documented call returns HTTP 404 (verified). |

---

## 3. Test suite

`pytest -q --cov=backend/app` on a fresh clone (log: `results/pytest_log.txt`):

- **Run 1, fresh database:** 8 passed, 1 failed. `test_auth_flow.py::test_full_auth_and_user_flow` raises `sqlite3.OperationalError: no such table: users`. The auth test never calls `init_db()`, and all tests share the real `data/storage/memory_lane.db`.
- **Run 2, same directory:** 9 passed. The README's "100% passing" claim depends on leftover state.
- **Statement coverage:** 74% (2,060 statements). The weakest modules are `seed.py` 0%, `routes_auth.py` 31%, `parsers.py` 34%, `routes_users.py` 35%, `date_extractor.py` 43%, `stratified_sampler.py` 58% and `fts_store.py` 59%. The paper's central algorithm (stratified sampling) is among the least tested.

**Fix:** use a `tmp_path` database fixture per test (override `settings.DB_PATH` and `VECTOR_STORE_DIR`), and add unit tests for the sampler, the date extractor and every metric.

---

## 4. Experiment E1 — Reproducing the repo's own benchmark

`ExperimentRunner.run_benchmark()` on a fresh database, repeated 5 times. Results were identical across runs (`results/inrepo_benchmark_5runs.json`, per-query detail in `results/inrepo_per_query.txt`).

| Metric | README: Baseline / Temporal / ML | **Measured: Baseline / Temporal / ML** |
|---|---|---|
| Chronological Ordering Accuracy | 0.40 / 0.82 / 1.00 | **1.00 / 1.00 / 1.00** |
| Temporal Coverage Recall | 0.35 / 0.70 / 0.95 | **0.767 / 1.000 / 1.000** |
| Change-Point F1 | 0.00 / 0.20 / 0.92 | **0.333 / 0.389 / 0.389** |
| Unsupported Claim Rate | 0.28 / 0.15 / 0.00 | **0.00 / 0.00 / 0.00** |
| Mean latency | 120 / 140 / 220 ms | **~17 / ~173 / ~176 ms** |

**Per-query detail:**

- **q1, AI evolution.** Memory Lane flags 5 changes against 4 true ones; F1 = 0.667.
- **q2, Java.** The router classifies the query as a fact lookup, so stratification is not applied. Three "sudden_shift" changes are flagged, two of them within 2022; F1 = 0.5.
- **q3, career goals.** The ground truth has no transitions, yet Memory Lane flags 5 changes (F1 = 0.0). The baseline, with detection switched off, receives F1 = 1.0.

---

## 5. Experiment E2 — Controlled longitudinal benchmark (new)

**Design.** A 2 × 2 × 2 factorial design with 12 personas per cell, 96 personas in total and 2,304 documents. Each persona documents one stance reversal (negative → positive) on a target topic over 6 years, with the flip at year 3 or 4. Each year also contains one neutral mention of the topic and one distractor document. The three factors are:

- **Topic:** listed in the extractor's entity list (Java, Python, Rust, Kubernetes) or not (Haskell, Elixir, Terraform, Kotlin).
- **Phrasing:** stance sentences that match the hard-coded polarity regexes, or natural paraphrases ("I've grown to really appreciate X").
- **Density:** uniform (3 docs/year) or skewed (12 extra on-topic docs in the final year).

Each persona is queried with an evolution phrasing ("How has my view on X changed over the years?") and a plain phrasing ("What do I think about X?"), with top_k = 8. Statistics are 5,000-sample bootstrap 95% CIs and paired Wilcoxon signed-rank tests.

**Table E2.1 — Temporal Coverage Recall (n = 48 personas per cell)**

| Query phrasing | Density | Baseline | Memory Lane | Wilcoxon p |
|---|---|---|---|---|
| Evolution | Uniform | 0.903 [0.875, 0.930] | **1.000 [1.000, 1.000]** | 1.1 × 10⁻⁶ |
| Evolution | Skewed | 0.729 [0.691, 0.771] | **1.000 [1.000, 1.000]** | 1.6 × 10⁻⁹ |
| Plain | Uniform | 0.920 [0.892, 0.944] | 0.920 [0.892, 0.944] | 0.99 |
| Plain | Skewed | 0.764 [0.726, 0.802] | 0.778 [0.743, 0.812] | 0.58 |

**Table E2.2 — Memory Lane change and reversal detection (evolution phrasing, n = 24 per row)**

| Topic | Phrasing | Change-Point F1 | Reversal detected | Changes flagged / query (truth = 1) |
|---|---|---|---|---|
| Listed | Listed | 0.290 [0.276, 0.306] | **1.00** | 6.0 |
| Listed | Paraphrase | 0.229 [0.184, 0.267] | **0.00** | 6.1 |
| Unlisted | Listed | 0.000 | 0.00 | 0.0 |
| Unlisted | Paraphrase | 0.000 | 0.00 | 0.0 |

**Reading.** Stratification does what it claims: it fully restores coverage that dense top-k loses under density skew. However, it only fires on evolution-style wording. Change detection over-fires (low precision from word-overlap drift between neutral and stance sentences) and fails completely for topics outside the lexicon. Reversal detection works only when both the topic and the wording are in the hard-coded lists. UHCR was 0.00 in all 384 runs, which confirms finding A11.

---

## 6. Experiment E3 — LoCoMo retrieval (public benchmark)

**Setup.** LoCoMo (Maharana et al., ACL 2024; `locomo10.json` from the official repository) has 10 conversations and 5,882 turns. Every turn is ingested through Memory Lane's own pipeline as a dated document (user = conversation), which produces 15,628 TMUs. There are 1,540 non-adversarial questions; the 1,536 with parseable evidence IDs are scored. **Recall@k** is the fraction of a question's annotated evidence turns found among the first k unique retrieved turns, and **Hit@k** is whether any evidence turn is found. Memory Lane returns k memory units, which map to about k unique turns (measured 4.96 at k = 5 and 9.89 at k = 10), so the budget matches the turn-level baselines. Categories follow the common LoCoMo mapping (1 multi-hop, 2 temporal, 3 open-domain, 4 single-hop). No LLM is involved, so the results are fully deterministic and re-running reproduced every number exactly.

**Table E3 — Recall@5 [95% CI], Recall@10, per-category Recall@5, retrieval latency**

| System | R@5 | R@10 | Single-hop (n=841) | Multi-hop (282) | Temporal (321) | Open-dom. (92) | p50 ms |
|---|---|---|---|---|---|---|---|
| Most-recent turns | 0.012 [0.007, 0.017] | 0.021 | 0.011 | 0.003 | 0.019 | 0.022 | 0.1 |
| BM25 (Okapi, rank_bm25) | 0.435 [0.411, 0.460] | 0.515 | 0.535 | 0.135 | 0.511 | 0.175 | 1.3 |
| TF-IDF | 0.428 [0.405, 0.452] | 0.503 | 0.522 | 0.130 | 0.507 | 0.201 | 1.0 |
| WordLlama dense (256-d) | 0.340 [0.318, 0.363] | 0.413 | 0.388 | 0.138 | 0.445 | 0.161 | 0.4 |
| BM25 + WordLlama, RRF | 0.443 [0.419, 0.466] | 0.520 | 0.516 | 0.181 | 0.552 | 0.187 | 1.4 |
| ML: hashed vectors only (`baseline` mode) | 0.182 [0.163, 0.202] | 0.233 | 0.235 | 0.035 | 0.216 | 0.020 | 64.5 |
| ML: FTS5 BM25 only | **0.448 [0.425, 0.471]** | 0.519 | 0.524 | 0.173 | 0.558 | 0.205 | 22.9 |
| **ML: full pipeline (as shipped)** | **0.334 [0.311, 0.357]** | 0.401 | 0.401 | 0.115 | 0.424 | 0.078 | 64.8 |
| ML: full + forced stratification | 0.325 [0.303, 0.347] | 0.394 | 0.387 | 0.105 | 0.420 | 0.097 | 67.3 |
| ML: full + WordLlama embeddings | 0.404 [0.380, 0.426] | 0.463 | 0.473 | 0.159 | 0.505 | 0.168 | 59.7 |
| ML: full + WordLlama + forced strat. | 0.394 [0.372, 0.417] | 0.453 | 0.455 | 0.151 | 0.511 | 0.168 | 59.8 |

Paired Wilcoxon tests against the shipped pipeline on R@5: FTS5-only p = 2.1 × 10⁻¹⁹; BM25 p = 7.8 × 10⁻¹⁴; +WordLlama p = 2.1 × 10⁻⁸; forced stratification p = 0.44 (n.s.). Latency was measured on 1 vCPU with no other load.

**Reading.**

- The system's sparse index is competitive with a standard BM25.
- Fusing it with the hashed vectors costs 11.4 points of R@5. The dense component degrades retrieval rather than helping it.
- Replacing the hashed vectors with even a small static embedding recovers 7 of those points.
- Stratification never triggers naturally (0 of 1,540 questions). Forcing it has no significant effect, as expected when every conversation spans about one calendar year (A7).
- Memory Lane's temporal machinery gives no advantage on LoCoMo's temporal category (0.424 vs 0.511 for BM25).

---

## 7. Experiment E4 — Scalability of the reference implementation

Persistence is left enabled, as shipped. The corpus is synthetic 3-sentence documents across 5 users (`results/scaling.json`).

| Documents stored | TMUs | Ingest time per new document | Retrieval p50 / p95 | Vector file |
|---|---|---|---|---|
| 250 | 750 | 533 ms | 65 / 93 ms | 1.9 MB |
| 500 | 1,500 | 1,058 ms | 88 / 121 ms | 3.9 MB |
| 1,000 | 3,000 | 2,075 ms | 107 / 145 ms | 7.7 MB |

Ingest time per document roughly doubles each time the store doubles, so ingesting N documents costs O(N²). At this rate a 10,000-document personal archive would need about 20 s per document near the end, many hours in total. The cause is A19: the full JSON vector file is rewritten on every insert. These numbers were measured while another benchmark shared the CPU, so absolute values are inflated; the growth trend is what matters. The run was stopped after 1,000 documents.

---

## 8. Limitations of this evaluation

- **No LLM was used.** End-to-end answer accuracy (LLM-as-judge on LoCoMo/LongMemEval) and real hallucination rates were not measured. They need an API key or local model weights, which were unreachable from this environment (HuggingFace blocked).
- **The E2 personas are template-generated.** They isolate mechanisms but are not natural writing; a human-written test set is still needed.
- **WordLlama is a small static embedding model.** Strong models (BGE-M3, Qwen3-Embedding) would likely widen the gap reported in E3.
- **LongMemEval was not run.** Its data is hosted on HuggingFace.
- **LoCoMo category labels follow the widely used mapping,** which some papers dispute.

---

## 9. Changes required before the paper is submitted (priority order)

1. Replace the hashed vectors with a real embedding model, and make it configurable. Re-run E2 and E3.
2. Decouple stratification from keyword routing: always stratify, or use a learned or LLM intent classifier. Make epoch size adapt to the span of the user's history.
3. Replace or evaluate the rule-based TMU extractor. An LLM-based extractor is the obvious option; report polarity and type accuracy against human labels.
4. Fix the metrics:
   - Compute COA on the retrieval order, before sorting.
   - Measure hallucination with an NLI or LLM judge on real LLM outputs.
   - Score Change-F1 with topic matching and a temporal tolerance, and make empty-vs-empty undefined rather than 1.0.
5. Either implement a real "Temporal RAG" baseline (date filter + sort) or drop it.
6. Fix bugs A15–A20; isolate the tests; persist vectors in batches (or use FAISS/sqlite-vec); filter by user before scoring.
7. Remove the README results table and replace it with numbers from the fixed system produced by these scripts.

---

## 10. Draft "Experiments" section for the paper

*This reflects the system as currently shipped. If you implement the fixes in §9, re-run the scripts and update the numbers. The narrative below is written so that it stays honest either way.*

> **5 Experiments**
>
> We evaluate Memory Lane RAG along three axes: (i) whether period-stratified retrieval restores temporal coverage under uneven document density, (ii) how well change-point and reversal detection generalise beyond the extraction lexicon, and (iii) how the full retrieval stack compares with standard retrievers on a public long-term memory benchmark. All experiments use the deterministic synthesis path so that retrieval effects are isolated from LLM variance; code and raw outputs are released.
>
> **5.1 Controlled longitudinal benchmark.** We generate 96 personas in a 2 × 2 × 2 factorial design crossing topic vocabulary (in vs. out of the extractor lexicon), stance phrasing (lexicon-matching vs. paraphrased) and document density (uniform vs. a final-year burst of 12 additional on-topic documents). Each persona contains one documented stance reversal over six years. With evolution-phrased queries, stratified retrieval achieves complete Temporal Coverage Recall (1.00) in both density conditions, whereas dense top-k retrieval drops from 0.90 [0.88, 0.93] to 0.73 [0.69, 0.77] under density skew (paired Wilcoxon p < 10⁻⁸; Table X, Fig. 1). The benefit is contingent on the query router: for plainly phrased queries stratification is not invoked and coverage is indistinguishable from the baseline (p = 0.58).
>
> **5.2 Change and reversal detection.** Reversals are recovered in all cases where both the topic and the stance wording fall inside the extraction lexicon, and in none otherwise; change-point F1 does not exceed 0.29, with detections dominated by false positives from lexical drift (≈6 flagged transitions per true transition; Table Y, Fig. 2). We therefore regard the change-detection module as a proof of concept whose lexicon-based extraction is the main limitation.
>
> **5.3 LoCoMo retrieval.** We ingest all 5,882 turns of LoCoMo through the full pipeline and measure evidence-turn Recall@k on 1,536 non-adversarial questions (Table Z, Fig. 3). Memory Lane's FTS5 BM25 component alone attains R@5 = 0.448, on par with Okapi BM25 (0.435) and a BM25 + dense RRF hybrid (0.443), but the full pipeline reaches 0.334 because its hashed dense channel (0.182 alone) degrades the fused ranking; substituting a learned embedding raises it to 0.404. Since LoCoMo conversations each span roughly one calendar year, year-level stratification has no significant effect there (p = 0.44), which motivates adaptive epoch sizing.
>
> **5.4 Efficiency.** Retrieval latency is 60–65 ms p50 on a single CPU core for corpora of ~15k memory units. Ingestion cost per document grows linearly with corpus size in the reference implementation because the vector index is fully re-serialised on each insert (Fig. 4); batched or incremental persistence removes this bottleneck.

---

## 11. Contents of this package

- `scripts/`
  - `bench_longitudinal.py`: E2.
  - `bench_locomo.py`: E3.
  - `bench_scale.py`: E4.
  - `run_inrepo.py` and `inrepo_detail.py`: E1.
  - `stats_long.py` and `analyze_locomo.py`: statistics.
- `results/`: raw per-query JSON for every experiment, summaries with CIs, and the pytest log.
- `figures/`: four PNG figures (200 dpi) for the paper.
- `README.md`: how to re-run everything.
