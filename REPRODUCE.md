# Reproducing the experiments

```bash
pip install -r requirements.txt rank_bm25 scikit-learn scipy matplotlib
python -m pytest -q                                   # 24 tests
python scripts/build_mllb_synth.py                     # MLLB-Synth v1 -> data/mllb_synth_v1 (already included)
curl -L -o data/locomo10.json https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json
export OUT_DIR=results
```

## Retrieval-only experiments (deterministic, no API key)
| Experiment | Command | Output |
|---|---|---|
| Drift threshold (dev) | `ML_DATA_DIR=/tmp/a python scripts/eval_mllb_synth.py --code v11 --split dev --configs default && ML_DATA_DIR=/tmp/a python scripts/calibrate_drift.py` | `drift_calibration_dev.json` |
| Stratification default (dev) | `ML_DATA_DIR=/tmp/b python scripts/select_stratification.py` | `stratification_selection_dev.json` |
| MLLB-Synth v1.1 | `ML_DATA_DIR=/tmp/c python scripts/eval_mllb_synth.py --code v11 --split test` | `mllb_v11_test.json` |
| MLLB-Synth v1.0 | `ML_REPO=<original v1.0 checkout> python scripts/eval_mllb_synth.py --code v10 --split test` | `mllb_v10_test.json` |
| MLLB summary | `python scripts/analyze_mllb.py results/mllb_v1*_*.json` | `mllb_summary.json` |
| LoCoMo retrieval | `ML_DATA_DIR=/tmp/d python scripts/bench_conversations.py --dataset locomo --data data/locomo10.json` then `python scripts/analyze_conversations.py results/conv_locomo.json ml_router` | `conv_locomo*.json` |
| LongMemEval retrieval | `ML_DATA_DIR=/tmp/e python scripts/bench_conversations.py --dataset longmemeval --data data/longmemeval_s_cleaned.json` | `conv_longmemeval.json` |
| Scaling | `ML_DATA_DIR=/tmp/f python scripts/bench_scale.py --tag v11` (v1.0: `ML_REPO=<v1.0 checkout> ... --checkpoints 250,500,1000 --tag v10`) | `scale_*.json` |
| Figures | `python scripts/make_figures.py` | `figures/` |

Note: the `--configs default` label in `eval_mllb_synth.py` means the code defaults at run time. The
results shipped here were produced when the default was `always`; `router_strat` is the current default.

## LLM experiments (need an OpenAI-compatible endpoint)
```bash
export OPENAI_BASE_URL=https://api.openai.com/v1 OPENAI_API_KEY=...   # or a local vLLM/Ollama server
export ML_READER_MODEL=gpt-4o-mini ML_JUDGE_MODEL=gpt-4o-mini ML_LLM_MODEL=gpt-4o-mini
ML_DATA_DIR=/tmp/qa python scripts/eval_llm_qa.py --dataset locomo --data data/locomo10.json \
    --systems memory_lane,ml_dense,turn_bm25,full_context,mem0 --judge_runs 3
ML_DATA_DIR=/tmp/qa2 python scripts/eval_llm_qa.py --dataset longmemeval --data data/longmemeval_s_cleaned.json \
    --systems memory_lane,turn_bm25,full_context
ML_DATA_DIR=/tmp/g python scripts/eval_llm_grounding.py --split test
ML_EXTRACTOR=llm ML_DATA_DIR=/tmp/h python scripts/eval_mllb_synth.py --code v11 --split test --configs default,router_strat
```
For Mem0: `pip install "mem0ai[nlp,extras]"`; see the note in `eval_llm_qa.py` about event dates.
To test the plumbing without a key: `uvicorn scripts.dev.mock_openai_server:app --port 8765` and
`OPENAI_BASE_URL=http://127.0.0.1:8765/v1` (numbers from the mock are meaningless).
