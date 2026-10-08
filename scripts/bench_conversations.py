"""
Evidence-retrieval benchmark on LoCoMo and LongMemEval (no LLM required).

Each dialogue turn is ingested through Memory Lane's own pipeline as a dated document;
retrieved memories are mapped back to turns/sessions and scored against gold evidence.

  LoCoMo      : gold = annotated evidence turns (dia_id); unit = turn; one user per conversation.
  LongMemEval : gold = answer_session_ids; unit = session; one user per question (each question has
                its own haystack). Abstention questions (*_abs) are skipped, as in the official
                retrieval evaluation.

Metrics: Recall@k (fraction of gold units among the first k unique retrieved units), Hit@k,
NDCG@k, latency.

Usage
  python scripts/bench_conversations.py --dataset locomo --data data/locomo10.json
  python scripts/bench_conversations.py --dataset longmemeval --data data/longmemeval_s_cleaned.json [--limit 100]
Env: ML_REPO (repo root), ML_DATA_DIR (fresh store dir), ML_EMBEDDING_BACKEND (e.g. st:BAAI/bge-m3), OUT_DIR.
Download LongMemEval:  https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned
"""
import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--dataset", choices=["locomo", "longmemeval"], required=True)
ap.add_argument("--data", required=True)
ap.add_argument("--limit", type=int, default=0, help="LongMemEval: number of questions (0 = all)")
ap.add_argument("--ks", default="5,10")
ap.add_argument("--configs", default="ml_default,ml_router,ml_strat_off,ml_sparse_only,ml_dense_only,ml_hash,"
                                     "ext_bm25,ext_dense,ext_hybrid,ext_recency")
ap.add_argument("--tag", default="")
args = ap.parse_args()
KS = [int(k) for k in args.ks.split(",")]

REPO = os.environ.get("ML_REPO", ".")
OUT = os.environ.get("OUT_DIR", "results")
sys.path.insert(0, os.path.join(REPO, "backend"))
os.environ.setdefault("ML_LLM_BACKEND", "deterministic")
from app.core.database import init_db  # noqa: E402

init_db()
from app.core.config import settings  # noqa: E402
from app.ingestion.ingestion_service import ingestion_service  # noqa: E402
from app.retrieval.hybrid_retriever import hybrid_retriever  # noqa: E402
from app.storage.embeddings import HashEmbedder, get_embedder  # noqa: E402
from app.storage.repository import Repository  # noqa: E402
from app.storage.vector_store import tmu_vector_store  # noqa: E402


# ------------------------------------------------------------------ loading
def locomo_items(path):
    data = json.load(open(path))
    cats = {1: "multi_hop", 2: "temporal", 3: "open_domain", 4: "single_hop"}
    users, questions = {}, []
    for conv in data:
        sid, c = conv["sample_id"], conv["conversation"]
        turns = []
        for s in sorted({int(k.split("_")[1]) for k in c if re.fullmatch(r"session_\d+", k)}):
            m = re.search(r"on (\d{1,2}) (\w+),? (\d{4})", c[f"session_{s}_date_time"])
            date = datetime.strptime(" ".join(m.groups()), "%d %B %Y").strftime("%Y-%m-%d")
            for t in c[f"session_{s}"]:
                turns.append({"unit": t["dia_id"], "date": date, "text": f"{t['speaker']}: {t['text']}"})
        users[sid] = turns
        for q in conv["qa"]:
            if q["category"] == 5:
                continue
            ev = set(re.findall(r"D\d+:\d+", " ".join(q["evidence"])))
            if ev:
                questions.append({"user": sid, "q": q["question"], "gold": ev, "cat": cats[q["category"]],
                                  "answer": str(q.get("answer", ""))})
    return users, questions


def lme_date(s):
    m = re.match(r"(\d{4})/(\d{2})/(\d{2})", s or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def longmemeval_items(path, limit):
    data = json.load(open(path))
    data = [d for d in data if not str(d["question_id"]).endswith("_abs")]
    if limit:
        data = data[:limit]
    users, questions = {}, []
    for d in data:
        uid = f"lme_{d['question_id']}"
        turns = []
        for sid, date, sess in zip(d["haystack_session_ids"], d["haystack_dates"], d["haystack_sessions"]):
            for j, t in enumerate(sess):
                turns.append({"unit": sid, "date": lme_date(date), "text": f"{t['role']}: {t['content']}"})
        users[uid] = turns
        questions.append({"user": uid, "q": d["question"], "gold": set(d["answer_session_ids"]),
                          "cat": d["question_type"], "answer": str(d.get("answer", "")),
                          "question_date": lme_date(d.get("question_date"))})
    return users, questions


users, questions = (locomo_items(args.data) if args.dataset == "locomo"
                    else longmemeval_items(args.data, args.limit))
print(f"{args.dataset}: {len(users)} users, {sum(len(v) for v in users.values())} turns, {len(questions)} questions",
      flush=True)

# ------------------------------------------------------------------ ingestion through Memory Lane
doc2unit = {}
t0 = time.perf_counter()
for uid, turns in users.items():
    for i, t in enumerate(turns):
        if len(t["text"]) > 20000:  # pathological very long turns
            t = dict(t, text=t["text"][:20000])
        doc = ingestion_service.ingest_text_content(content=t["text"], title=f"{uid}__{i}", user_id=uid,
                                                    document_date=t["date"])
        doc2unit[doc.id] = t["unit"]
ingest_s = time.perf_counter() - t0
print(f"ingested in {ingest_s:.1f}s with embedder {tmu_vector_store.embedder.name}", flush=True)

# ------------------------------------------------------------------ external turn-level baselines
from rank_bm25 import BM25Okapi  # noqa: E402

ext = {}
for uid, turns in users.items():
    texts = [t["text"] for t in turns]
    ext[uid] = {"units": [t["unit"] for t in turns], "dates": [t["date"] or "" for t in turns],
                "bm25": BM25Okapi([re.findall(r"\w+", x.lower()) for x in texts]),
                "emb": tmu_vector_store.embedder.embed(texts)}


def ext_rank(name, uid, q):
    E = ext[uid]
    if name == "ext_recency":
        return [E["units"][i] for i in np.argsort(E["dates"])[::-1]]
    bm = E["bm25"].get_scores(re.findall(r"\w+", q.lower()))
    if name == "ext_bm25":
        order = np.argsort(-bm)
    else:
        de = E["emb"] @ tmu_vector_store.embedder.embed_one(q)
        if name == "ext_dense":
            order = np.argsort(-de)
        else:  # hybrid RRF
            sc = np.zeros(len(bm))
            for r in (np.argsort(-bm), np.argsort(-de)):
                sc[r] += 1.0 / (60 + np.arange(1, len(r) + 1))
            order = np.argsort(-sc)
    return [E["units"][i] for i in order]


# ------------------------------------------------------------------ Memory Lane configs
def ml_rank(cfg, uid, q, k):
    kw = dict(query=q, user_id=uid, top_k=k)
    if cfg == "ml_router":
        kw["stratification_mode"] = "router"
    elif cfg == "ml_strat_off":
        kw["stratification_mode"] = "off"
    elif cfg == "ml_sparse_only":
        kw.update(sparse_only=True, stratification_mode="off")
    elif cfg == "ml_dense_only":
        kw.update(dense_only=True, stratification_mode="off")
    pack = hybrid_retriever.retrieve(**kw)
    return [doc2unit.get(t.document_id) for t in pack["ranked_results"]]


def score(ranked, gold, k):
    seen = []
    for u in ranked:
        if u is not None and u not in seen:
            seen.append(u)
    top = seen[:k]
    rec = len(set(top) & gold) / len(gold)
    hit = float(bool(set(top) & gold))
    dcg = sum(1 / math.log2(i + 2) for i, u in enumerate(top) if u in gold)
    idcg = sum(1 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return rec, hit, dcg / idcg if idcg else 0.0


results, lat = {}, {}
for cfg in args.configs.split(","):
    if cfg == "ml_hash":
        tmu_vector_store.set_embedder(HashEmbedder())
    rows, L = [], []
    for qi in questions:
        r = {"cat": qi["cat"]}
        if cfg.startswith("ext_"):
            ts = time.perf_counter(); ranked = ext_rank(cfg, qi["user"], qi["q"]); L.append((time.perf_counter() - ts) * 1000)
            for k in KS:
                r[f"R@{k}"], r[f"H@{k}"], r[f"N@{k}"] = score(ranked, qi["gold"], k)
        else:
            for k in KS:
                ts = time.perf_counter(); ranked = ml_rank(cfg, qi["user"], qi["q"], k); L.append((time.perf_counter() - ts) * 1000)
                r[f"R@{k}"], r[f"H@{k}"], r[f"N@{k}"] = score(ranked, qi["gold"], k)
        rows.append(r)
    if cfg == "ml_hash":
        tmu_vector_store.set_embedder(get_embedder())
    results[cfg], lat[cfg] = rows, L
    print(cfg, {m: round(float(np.mean([x[m] for x in rows])), 4) for m in [f"R@{KS[0]}", f"R@{KS[-1]}", f"N@{KS[-1]}"]},
          f"p50={np.percentile(L, 50):.1f}ms", flush=True)
    os.makedirs(OUT, exist_ok=True)
    json.dump({"meta": {"dataset": args.dataset, "embedder": get_embedder().name, "n_questions": len(questions),
                        "ingest_seconds": ingest_s, "settings": {"STRATIFICATION_MODE": settings.STRATIFICATION_MODE,
                                                                 "EPOCH_MODE": settings.EPOCH_MODE, "RRF_K": settings.RRF_K}},
               "results": results, "latency": lat},
              open(os.path.join(OUT, f"conv_{args.dataset}{args.tag}.json"), "w"))
print("done")
