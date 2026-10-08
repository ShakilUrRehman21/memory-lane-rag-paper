"""
Evaluates a Memory Lane RAG code base on MLLB-Synth v1 (see build_mllb_synth.py).

Metrics are implemented HERE (not imported from the repo) so that v1.0 and v1.1 are scored
identically:
  TCR          fraction of the persona's years present among retrieved memories
  CP precision / recall / F1   change points on the queried topic, exact years (tol 0) and +-1 year
  reversal_found  a stance reversal on the topic is reported (reversal personas)
  false_alarm     any change or reversal on the topic is reported (stable personas)

Usage
  ML_REPO=path/to/repo ML_DATA_DIR=/tmp/x python scripts/eval_mllb_synth.py --code v11 --split test
  ML_REPO=path/to/original_repo python scripts/eval_mllb_synth.py --code v10 --split test
Configs for v1.1 are retrieval-time settings evaluated in one process (one ingestion).
"""
import argparse
import json
import os
import sys
import time

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--code", choices=["v10", "v11"], required=True)
ap.add_argument("--split", choices=["dev", "test", "human", "all"], default="test")
ap.add_argument("--data", default=os.environ.get("MLLB_DIR", "data/mllb_synth_v1"))
ap.add_argument("--out", default=os.environ.get("OUT_DIR", "results"))
ap.add_argument("--top_k", type=int, default=8)
ap.add_argument("--configs", default="default,router_strat,year_epochs,no_query_focus,hash_embed")
args = ap.parse_args()

REPO = os.environ.get("ML_REPO", ".")
sys.path.insert(0, os.path.join(REPO, "backend"))
os.environ.setdefault("ML_LLM_BACKEND", "deterministic")
from app.core.database import init_db  # noqa: E402

init_db()
from app.ingestion.ingestion_service import ingestion_service  # noqa: E402
from app.models.schemas import QueryRequest  # noqa: E402
from app.synthesis.grounded_synthesizer import grounded_synthesizer  # noqa: E402

if args.code == "v10":  # avoid v1.0's O(N^2) JSON rewrite during bulk ingest (does not change results)
    from app.storage import vector_store as _vs
    _vs.VectorStore.save = lambda self: None


def load(fn):
    return [json.loads(l) for l in open(os.path.join(args.data, fn))]


split_ok = (lambda r: True) if args.split == "all" else (lambda r: r["split"] == args.split)
docs = [d for d in load("documents.jsonl") if split_ok(d)]
queries = [q for q in load("queries.jsonl") if split_ok(q)]
personas = {p["persona_id"]: p for p in load("personas.jsonl") if split_ok(p)}

t0 = time.perf_counter()
for d in docs:
    ingestion_service.ingest_text_content(content=d["text"], title=d["doc_id"], user_id=d["persona_id"],
                                          document_date=d["date"])
ingest_s = time.perf_counter() - t0
print(f"ingested {len(docs)} docs in {ingest_s:.1f}s", flush=True)


def yr(s):
    return int(s[:4]) if s and s[:4].isdigit() else None


def about(topic, *texts):
    t = topic.lower()
    return any(t in (x or "").lower() for x in texts)


def cp_prf(changes, gt, topic, tol):
    det = [c for c in changes]
    used, tp = set(), 0
    for c in det:
        if not about(topic, c.topic_or_entity, c.earlier_statement, c.later_statement):
            continue
        f, t = yr(c.from_period), yr(c.to_period)
        for k, (gf, gtt, _) in enumerate(gt):
            if k not in used and f is not None and t is not None and abs(f - int(gf)) <= tol and abs(t - int(gtt)) <= tol:
                used.add(k); tp += 1
                break
    if not gt and not det:
        return None, None, None
    p = tp / len(det) if det else 0.0
    r = tp / len(gt) if gt else None
    f1 = (2 * p * r / (p + r) if (p + r) else 0.0) if r is not None else None
    return p, r, f1


def run(config, pipelines):
    rows = []
    for q in queries:
        per = personas[q["persona_id"]]
        for pipe in pipelines:
            kw = dict(query=q["query"], user_id=q["persona_id"], pipeline_mode=pipe, top_k=args.top_k)
            ts = time.perf_counter()
            res = grounded_synthesizer.synthesize(QueryRequest(**kw))
            lat = (time.perf_counter() - ts) * 1000
            years = set(q["expected_years"])
            got = {p.event_date[:4] for p in res.timeline if p.event_date}
            topic = q["topic"]
            on_topic_changes = [c for c in res.detected_changes
                                if about(topic, c.topic_or_entity, c.earlier_statement, c.later_statement)]
            on_topic_rev = [r for r in res.potential_contradictions
                            if about(topic, r.source_statement, r.target_statement)]
            gt = [tuple(x) for x in q["ground_truth_transitions"]]
            p0, r0, f0 = cp_prf(res.detected_changes, gt, topic, 0)
            p1, r1, f1 = cp_prf(res.detected_changes, gt, topic, 1)
            rows.append(dict(config=config, pipeline=pipe, query_id=q["query_id"], query_style=q["query_style"],
                             kind=per["kind"], lexicon=per["lexicon"], phrasing=per["phrasing"],
                             density=per["density"], TCR=len(got & years) / len(years),
                             cp_precision=p0, cp_recall=r0, cp_f1=f0, cp_f1_tol1=f1,
                             n_changes=len(res.detected_changes),
                             reversal_found=float(bool(on_topic_rev) or any(c.change_type == "reversal" for c in on_topic_changes)),
                             false_alarm=float(bool(on_topic_changes) or bool(on_topic_rev)),
                             stratified=getattr(res, "stratified", None), latency_ms=lat))
    print(f"  {config}: {len(rows)} rows", flush=True)
    return rows


all_rows = []
if args.code == "v10":
    all_rows += run("v1.0", ["baseline", "memory_lane"])
else:
    from app.core.config import settings
    from app.storage.embeddings import HashEmbedder, get_embedder
    from app.storage.vector_store import tmu_vector_store
    base = dict(STRATIFICATION_MODE=settings.STRATIFICATION_MODE, EPOCH_MODE=settings.EPOCH_MODE,
                QUERY_FOCUSED_CHANGES=settings.QUERY_FOCUSED_CHANGES)
    cfgs = {"default": {}, "router_strat": {"STRATIFICATION_MODE": "router"}, "year_epochs": {"EPOCH_MODE": "year"},
            "no_query_focus": {"QUERY_FOCUSED_CHANGES": False}, "hash_embed": {"_embedder": "hash"}}
    for name in args.configs.split(","):
        over = cfgs[name]
        for k, v in base.items():
            setattr(settings, k, v)
        tmu_vector_store.set_embedder(HashEmbedder() if over.get("_embedder") == "hash" else get_embedder())
        for k, v in over.items():
            if not k.startswith("_"):
                setattr(settings, k, v)
        all_rows += run(f"v1.1:{name}", ["baseline", "temporal", "memory_lane"] if name == "default" else ["memory_lane"])
    tmu_vector_store.set_embedder(get_embedder())

os.makedirs(args.out, exist_ok=True)
fn = os.path.join(args.out, f"mllb_{args.code}_{args.split}.json")
json.dump({"meta": {"code": args.code, "split": args.split, "top_k": args.top_k, "n_docs": len(docs),
                    "n_queries": len(queries), "ingest_seconds": ingest_s}, "rows": all_rows}, open(fn, "w"))
print("wrote", fn)
