"""
Ingestion and retrieval scaling, identical procedure for v1.0 and v1.1 (persistence ON, as shipped).
Run on an otherwise idle machine. Synthetic 3-sentence documents spread over 5 users.
Usage: ML_REPO=<repo> [ML_DATA_DIR=<fresh dir> for v1.1] python scripts/bench_scale.py --checkpoints 250,500,1000 --tag v10
"""
import argparse
import json
import os
import random
import sys
import time

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--checkpoints", default="250,500,1000,2000,5000,10000")
ap.add_argument("--tag", required=True)
a = ap.parse_args()
REPO = os.environ.get("ML_REPO", ".")
OUT = os.environ.get("OUT_DIR", "results")
sys.path.insert(0, os.path.join(REPO, "backend"))
os.environ.setdefault("ML_LLM_BACKEND", "deterministic")
from app.core.database import init_db  # noqa: E402

init_db()
from app.core.config import settings  # noqa: E402
from app.ingestion.ingestion_service import ingestion_service  # noqa: E402
from app.retrieval.hybrid_retriever import hybrid_retriever  # noqa: E402

random.seed(1)
W = ("python java research goal career learning model data team project system design paper idea plan travel family "
     "book music health garden running coffee city friend course exam budget").split()


def sent():
    return " ".join(random.choice(W) for _ in range(12)).capitalize() + "."


rows, n = [], 0
for cp in map(int, a.checkpoints.split(",")):
    times = []
    while n < cp:
        t = time.perf_counter()
        ingestion_service.ingest_text_content(" ".join(sent() for _ in range(3)), f"d{n}", f"u{n % 5}",
                                              f"{2018 + n % 7}-0{1 + n % 9}-15")
        times.append(time.perf_counter() - t)
        n += 1
    for _ in range(3):  # warm caches
        hybrid_retriever.retrieve("How has my view on python research changed over the years?", user_id="u0", top_k=10)
    lat = []
    for i in range(50):
        t = time.perf_counter()
        hybrid_retriever.retrieve(f"what did I write about {random.choice(W)} and {random.choice(W)}?",
                                  user_id=f"u{i % 5}", top_k=10)
        lat.append((time.perf_counter() - t) * 1000)
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(settings.STORAGE_DIR)
               for f in fs if not f.endswith(".txt"))
    row = {"version": a.tag, "docs": n, "ingest_ms_per_doc_last100": round(1000 * float(np.mean(times[-100:])), 2),
           "query_p50_ms": round(float(np.percentile(lat, 50)), 2),
           "query_p95_ms": round(float(np.percentile(lat, 95)), 2), "store_MB": round(size / 1e6, 2)}
    rows.append(row)
    print(row, flush=True)
    os.makedirs(OUT, exist_ok=True)
    json.dump(rows, open(os.path.join(OUT, f"scale_{a.tag}.json"), "w"), indent=1)
