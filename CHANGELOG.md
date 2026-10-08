# Changelog

## v1.1.0 (audit fixes)

- v1.1: real embeddings, SQLite vector store, stratification modes + adaptive epochs, temporal baseline, query-focused change detection, LLM evidence prompt fix, honest metrics, bug fixes, isolated tests
- Drift threshold 0.70 calibrated on MLLB-Synth dev; dataset builder, evaluators, LongMemEval fixture
- Soft stratification mode; pre-registered selection -> router default; annotation kit; dataset card; LLM QA/grounding eval scripts; mock server
- Mem0 adapter fixes (date prefix, telemetry), conversation analysis, scaling benchmark, results
- v1.1 report, figures, README results replaced with reproducible numbers, REPRODUCE.md, v1.0 audit archived
- Do not redistribute LoCoMo (download via REPRODUCE.md)

Full details: EVALUATION_REPORT_v1.1.md. Code diff against v1.0.0: memory_lane_v1.1.patch.
