"""
Selects the semantic-drift threshold on the DEV split only (maximising mean change-point F1,
topic-matched, exact years). The held-out TEST split is never used for this choice.
Usage: ML_REPO=. ML_DATA_DIR=<dir already holding the ingested dev split> python scripts/calibrate_drift.py
"""
import json, os, sys
import numpy as np
REPO = os.environ.get("ML_REPO", "."); sys.path.insert(0, os.path.join(REPO, "backend"))
os.environ.setdefault("ML_LLM_BACKEND", "deterministic")
from app.core.config import settings
from app.models.schemas import QueryRequest
from app.synthesis.grounded_synthesizer import grounded_synthesizer
DATA = os.environ.get("MLLB_DIR", "data/mllb_synth_v1"); OUT = os.environ.get("OUT_DIR", "results")
qs = [json.loads(l) for l in open(os.path.join(DATA, "queries.jsonl"))]
qs = [q for q in qs if q["split"] == "dev"]

def f1(changes, gt, topic):
    t = topic.lower(); tp = 0; used = set()
    for c in changes:
        if t not in (c.topic_or_entity + c.earlier_statement + c.later_statement).lower(): continue
        for k, (a, b, _) in enumerate(gt):
            if k not in used and (c.from_period or "")[:4] == a and (c.to_period or "")[:4] == b:
                used.add(k); tp += 1; break
    p = tp / len(changes) if changes else 0.0; r = tp / len(gt)
    return 2 * p * r / (p + r) if p + r else 0.0

res = {}
for th in [0.3, 0.42, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]:
    settings.SEMANTIC_DRIFT_THRESHOLD = th
    s = [f1(grounded_synthesizer.synthesize(QueryRequest(query=q["query"], user_id=q["persona_id"], top_k=8)).detected_changes,
            [tuple(x) for x in q["ground_truth_transitions"]], q["topic"]) for q in qs]
    res[th] = round(float(np.mean(s)), 4); print(th, res[th], flush=True)
best = max(res, key=lambda k: (res[k], -k))
json.dump({"split": "dev", "objective": "mean change-point F1 (topic, exact years)", "sweep": res, "selected": best},
          open(os.path.join(OUT, "drift_calibration_dev.json"), "w"), indent=1)
print("selected", best)
