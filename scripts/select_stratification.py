"""
Pre-registered selection of the default stratification mode (dev data only).

Rule (fixed before running): among the candidate modes, choose the one with the highest mean
Temporal Coverage Recall on MLLB-Synth DEV (all query styles), subject to LoCoMo-DEV Recall@5
(conversations 1-5) being no more than 0.01 below the "off" mode. Ties -> fewer stratified slots.
Held-out evaluation afterwards: LoCoMo conversations 6-10 and MLLB-Synth TEST.

Usage: ML_REPO=. ML_DATA_DIR=/tmp/sel python scripts/select_stratification.py
"""
import json, os, re, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("ML_REPO", "."); OUT = os.environ.get("OUT_DIR", "results")
sys.path.insert(0, os.path.join(REPO, "backend"))
os.environ.setdefault("ML_LLM_BACKEND", "deterministic")
from conv_data import locomo_items
from app.core.database import init_db
init_db()
from app.core.config import settings
from app.ingestion.ingestion_service import ingestion_service
from app.retrieval.hybrid_retriever import hybrid_retriever
from app.synthesis.grounded_synthesizer import grounded_synthesizer
from app.models.schemas import QueryRequest

CANDIDATES = [("off", None), ("router", None), ("soft", 0.75), ("soft", 0.5), ("soft", 0.25), ("always", None)]
LOCOMO = os.environ.get("LOCOMO_JSON", "data/locomo10.json"); MLLB = os.environ.get("MLLB_DIR", "data/mllb_synth_v1")

users, qs = locomo_items(LOCOMO)
dev_users = list(users)[:5]  # conversations 1-5 in file order
qs = [q for q in qs if q["user"] in dev_users and q["gold"]]  # recall needs annotated evidence
doc2unit = {}
for uid in dev_users:
    for i, t in enumerate(users[uid]):
        d = ingestion_service.ingest_text_content(t["text"], f"{uid}__{i}", uid, t["date"]); doc2unit[d.id] = t["unit"]
mdocs = [json.loads(l) for l in open(os.path.join(MLLB, "documents.jsonl"))]
mq = [json.loads(l) for l in open(os.path.join(MLLB, "queries.jsonl"))]
for d in mdocs:
    if d["split"] == "dev":
        ingestion_service.ingest_text_content(d["text"], d["doc_id"], d["persona_id"], d["date"])
mq = [q for q in mq if q["split"] == "dev"]
print(f"LoCoMo-dev: {len(dev_users)} conversations, {len(qs)} questions; MLLB-dev: {len(mq)} queries", flush=True)


def recall5(mode, frac):
    settings.STRATIFICATION_MODE = mode
    if frac is not None:
        settings.SOFT_RELEVANCE_FRACTION = frac
    r = []
    for q in qs:
        pack = hybrid_retriever.retrieve(query=q["q"], user_id=q["user"], top_k=5)
        got = {doc2unit.get(t.document_id) for t in pack["results"]}
        r.append(len(got & q["gold"]) / len(q["gold"]))
    return float(np.mean(r))


def tcr(mode, frac):
    settings.STRATIFICATION_MODE = mode
    if frac is not None:
        settings.SOFT_RELEVANCE_FRACTION = frac
    v = []
    for q in mq:
        res = grounded_synthesizer.synthesize(QueryRequest(query=q["query"], user_id=q["persona_id"], top_k=8))
        got = {p.event_date[:4] for p in res.timeline}
        v.append(len(got & set(q["expected_years"])) / len(q["expected_years"]))
    return float(np.mean(v))


table = []
for mode, frac in CANDIDATES:
    row = {"mode": mode, "soft_fraction": frac, "locomo_dev_R@5": round(recall5(mode, frac), 4),
           "mllb_dev_TCR": round(tcr(mode, frac), 4)}
    table.append(row); print(row, flush=True)
off = next(r for r in table if r["mode"] == "off")["locomo_dev_R@5"]
eligible = [r for r in table if r["locomo_dev_R@5"] >= off - 0.01]
best = max(eligible, key=lambda r: (r["mllb_dev_TCR"], -table.index(r)))  # tie -> less stratification (earlier in CANDIDATES)
json.dump({"rule": __doc__.strip().split("\n\n")[1], "candidates": table, "selected": best},
          open(os.path.join(OUT, "stratification_selection_dev.json"), "w"), indent=1)
print("SELECTED", best)
