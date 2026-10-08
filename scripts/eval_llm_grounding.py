"""
Claim-level grounding of Memory Lane's LLM synthesis on MLLB-Synth (replaces v1.0's UHCR, which
was 0 by construction).

For each query the full pipeline runs with an LLM synthesizer (ML_LLM_BACKEND=openai or gemini).
Every claim in the answer is then checked:
  citation_valid   cites at least one memory that was actually retrieved (structural UHCR)
  supported        an LLM judge says the cited evidence entails the claim (NLI-style)
Per answer we also record:
  COA              order of claims vs. the dates of their evidence (meaningful only for an LLM)
  reversal_stated  the answer states a change of stance (judged) - compared with ground truth

Env: as eval_llm_qa.py (OPENAI_BASE_URL / OPENAI_API_KEY / ML_LLM_MODEL for the synthesizer,
ML_JUDGE_* for the judge). ML_EXTRACTOR=llm to also use LLM-based TMU extraction.
Usage: ML_REPO=. ML_DATA_DIR=/tmp/g python scripts/eval_llm_grounding.py --split test --limit 128
"""
import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--data", default=os.environ.get("MLLB_DIR", "data/mllb_synth_v1"))
ap.add_argument("--limit", type=int, default=0, help="number of personas (0 = all)")
ap.add_argument("--query_style", default="evolution")
ap.add_argument("--pipelines", default="memory_lane,baseline")
ap.add_argument("--workers", type=int, default=4)
args = ap.parse_args()

REPO = os.environ.get("ML_REPO", ".")
OUT = os.environ.get("OUT_DIR", "results")
sys.path.insert(0, os.path.join(REPO, "backend"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("ML_LLM_BACKEND", "openai")
os.environ.setdefault("ML_LLM_STRICT", "1")  # fail loudly instead of silently using the deterministic path

from app.core.database import init_db  # noqa: E402

init_db()
from app.evaluation.metrics import EvaluationMetrics as M  # noqa: E402
from app.ingestion.ingestion_service import ingestion_service  # noqa: E402
from app.models.schemas import QueryRequest  # noqa: E402
from app.synthesis.grounded_synthesizer import grounded_synthesizer  # noqa: E402
from eval_llm_qa_client import judge, parse_json  # noqa: E402

load = lambda fn: [json.loads(l) for l in open(os.path.join(args.data, fn))]
personas = [p for p in load("personas.jsonl") if p["split"] == args.split]
if args.limit:
    personas = personas[:args.limit]
pids = {p["persona_id"] for p in personas}
docs = [d for d in load("documents.jsonl") if d["persona_id"] in pids]
queries = [q for q in load("queries.jsonl") if q["persona_id"] in pids and q["query_style"] == args.query_style]
pmeta = {p["persona_id"]: p for p in personas}

marker = os.path.join(os.environ.get("ML_DATA_DIR", "."), f".ingested_mllb_{args.split}_{len(pids)}")
if not os.path.exists(marker):
    for d in docs:
        ingestion_service.ingest_text_content(content=d["text"], title=d["doc_id"], user_id=d["persona_id"],
                                              document_date=d["date"])
    open(marker, "w").write("ok")

SUPPORT_SYS = "You check whether evidence supports a claim. Output JSON only."


def supported(claim, evidence):
    if not evidence:
        return 0.0
    p = ("EVIDENCE:\n" + "\n".join(f"- [{d}] {s}" for d, s in evidence) + f"\n\nCLAIM: {claim}\n"
         "Is the claim fully supported by the evidence (entailed, not merely related)? Dates in the claim must "
         'match the evidence. Return {"label": "supported" or "unsupported", "reason": "<short>"}.')
    lab = str(parse_json(judge(SUPPORT_SYS, p, json_out=True, max_tokens=150)).get("label", "")).lower()
    return 1.0 if lab.startswith("supported") else 0.0


def states_reversal(answer, topic):
    p = (f"ANSWER: {answer}\n\nDoes this answer state that the person's attitude towards {topic} changed from "
         'negative to positive (or reversed)? Return {"label": "yes" or "no"}.')
    return 1.0 if str(parse_json(judge(SUPPORT_SYS, p, json_out=True, max_tokens=50)).get("label", "")).lower().startswith("y") else 0.0


rows, lock = [], threading.Lock()


def work(item):
    q, pipe = item
    res = grounded_synthesizer.synthesize(QueryRequest(query=q["query"], user_id=q["persona_id"], pipeline_mode=pipe, top_k=8))
    by_id = {t.id: t for t in res.retrieved_tmus}
    claim_rows = []
    for c in res.grounded_claims:
        ev = [(by_id[i].event_date_start, by_id[i].statement) for i in c.evidence_tmu_ids if i in by_id]
        claim_rows.append({"claim": c.claim_text, "citation_valid": float(bool(ev)), "supported": supported(c.claim_text, ev)})
    kind = pmeta[q["persona_id"]]["kind"]
    r = {"pipeline": pipe, "query_id": q["query_id"], "kind": kind, "backend": res.synthesis_backend,
         "n_claims": len(claim_rows),
         "unsupported_rate": (1 - float(np.mean([x["supported"] for x in claim_rows]))) if claim_rows else None,
         "invalid_citation_rate": (1 - float(np.mean([x["citation_valid"] for x in claim_rows]))) if claim_rows else None,
         "COA": M.chronological_ordering_accuracy(res.grounded_claims, res.retrieved_tmus, res.synthesis_backend),
         "reversal_stated": states_reversal(res.answer, q["topic"]), "answer": res.answer, "claims": claim_rows}
    with lock:
        rows.append(r)
    return r


jobs = [(q, p) for q in queries for p in args.pipelines.split(",")]
with ThreadPoolExecutor(max_workers=args.workers) as ex:
    list(ex.map(work, jobs))


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(float(np.mean(xs)), 4) if xs else None


summary = {}
for pipe in args.pipelines.split(","):
    rs = [r for r in rows if r["pipeline"] == pipe]
    summary[pipe] = {"n": len(rs), "unsupported_claim_rate": mean(r["unsupported_rate"] for r in rs),
                     "invalid_citation_rate": mean(r["invalid_citation_rate"] for r in rs),
                     "COA": mean(r["COA"] for r in rs), "claims_per_answer": mean(r["n_claims"] for r in rs),
                     "reversal_stated|reversal_persona": mean(r["reversal_stated"] for r in rs if r["kind"] == "reversal"),
                     "reversal_stated|stable_persona": mean(r["reversal_stated"] for r in rs if r["kind"] == "stable")}
os.makedirs(OUT, exist_ok=True)
json.dump({"summary": summary, "rows": rows}, open(os.path.join(OUT, f"grounding_{args.split}.json"), "w"), indent=1)
print(json.dumps(summary, indent=1))
