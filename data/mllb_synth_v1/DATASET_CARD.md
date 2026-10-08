# Dataset card: MLLB-Synth v1 (Memory Lane Longitudinal Benchmark, synthetic part)

## Summary
Template-generated personal "archives" in which an author documents an attitude toward one
topic over six years. Most personas contain exactly one stance reversal (negative to positive);
held-out control personas keep a constant stance. Each persona comes with natural-language
questions and gold labels for the years covered and the year pair of the reversal. The dataset
is a **controlled probe** for (i) temporal coverage of retrieval under uneven document density,
(ii) change-point and reversal detection, and (iii) generalisation beyond lexicon-matched wording.
It does **not** measure performance on real personal writing; use MLLB-Human for that.

## Files
| file | rows | fields |
|---|---|---|
| `documents.jsonl` | 5,376 | split, persona_id, doc_id, date (YYYY-MM-DD), role (stance / neutral / distractor / burst), text |
| `queries.jsonl` | 704 | split, query_id, persona_id, query, query_style, topic, expected_years, ground_truth_transitions [[from_year, to_year, type]] |
| `personas.jsonl` | 224 | split, persona_id, topic, lexicon, phrasing, density, kind (reversal / stable), flip_year, stable_sign, years, n_documents |

## Splits
| split | personas | documents | queries | query styles | purpose |
|---|---|---|---|---|---|
| dev | 96 (all reversal) | 2,304 | 192 | evolution, plain | development and calibration (drift threshold, stratification mode) |
| test | 128 (96 reversal + 32 stable) | 3,072 | 512 | evolution, plain, when_changed, history | **held out**; created after the v1.1 code was frozen; never used for tuning |

The dev split is byte-identical to the 96-persona corpus used in the original audit of v1.0
(verified in `build_mllb_synth.py`).

## Design (per split): 2 x 2 x 2 factorial, balanced
- **topic**: in the rule-based extractor's entity list (dev: Java, Python, Rust, Kubernetes; test:
  TypeScript, Docker, PostgreSQL, React) vs. not (dev: Haskell, Elixir, Terraform, Kotlin; test:
  Clojure, Svelte, Ansible, Julia).
- **phrasing**: stance sentences matching the extractor's polarity patterns vs. natural paraphrases.
  The test split uses entirely different templates from dev for every sentence type.
- **density**: 3 documents per year (stance, neutral mention, distractor) vs. the same plus 12
  extra on-topic documents in the final year.
Reversal year: uniformly year 3 or 4 of 6. Start year: 2018-2020.

## Intended use and metrics
Temporal Coverage Recall (years of retrieved memories vs. `expected_years`); change-point
precision/recall/F1 matched on topic and year pair (exact and +-1 year); reversal detection rate;
false-alarm rate on stable personas. Reference implementation: `scripts/eval_mllb_synth.py`.

## Limitations and biases
- Template text is short, formulaic and unlike real journals; results are optimistic about
  extraction and pessimistic about nothing. Report alongside MLLB-Human and public benchmarks.
- Only one topic and at most one reversal per persona; no gradual drift, no multiple topics
  interacting, no conflicting documents on the same date.
- English only. Topics are mainly software technologies.
- Templates were written by the evaluators (with AI assistance), not by independent writers.
- Ground truth is defined at year granularity.

## Generation and reproducibility
`python scripts/build_mllb_synth.py --out data/mllb_synth_v1` (Python `random.Random`, seeds 42 / 7).
No personal data. License: CC BY 4.0 (data), MIT (code) - adjust to your choice before release.

## Citation
Cite the Memory Lane RAG paper and this dataset version (MLLB-Synth v1).
