"""
End-to-end question answering on LoCoMo / LongMemEval with an LLM reader and an LLM judge.

All systems share the same reader model, reader prompt and judge, so only the memory/retrieval
layer differs:
  memory_lane   Memory Lane v1.1 hybrid retrieval (memory units, stratified), top-k
  ml_dense      Memory Lane store, dense retrieval only (plain-RAG baseline on the same units)
  turn_bm25     BM25 over full dialogue turns, top-k turns
  full_context  every turn of the history (upper bound when it fits the reader's context window)
  mem0          Mem0 open-source library (pip install mem0ai) with the same LLM endpoint

Endpoints (OpenAI-compatible; works with OpenAI, vLLM, Ollama, LM Studio, Together, ...):
  reader : OPENAI_BASE_URL, OPENAI_API_KEY, ML_READER_MODEL   (default gpt-4o-mini)
  judge  : ML_JUDGE_BASE_URL, ML_JUDGE_API_KEY, ML_JUDGE_MODEL (default: same endpoint, gpt-4o-mini)
  mem0   : MEM0_LLM_MODEL (default reader), MEM0_EMBED_MODEL (text-embedding-3-small), MEM0_EMBED_DIMS (1536)

Judge prompts are written for this project following the published protocols (Mem0's binary
LLM-as-judge "J" for LoCoMo; LongMemEval's per-question-type yes/no prompts). For numbers that
are directly comparable to a leaderboard, also run that benchmark's official evaluation script
on the saved answers (answers are written to <OUT_DIR>/qa_<dataset>_answers.jsonl).

Usage
  python scripts/eval_llm_qa.py --dataset locomo --data data/locomo10.json --systems memory_lane,ml_dense,turn_bm25,full_context
  python scripts/eval_llm_qa.py --dataset longmemeval --data data/longmemeval_s_cleaned.json --limit 100 --systems memory_lane,turn_bm25
"""
import argparse
import json
import math
import os
import random
import re
import string
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conv_data import load  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--dataset", choices=["locomo", "longmemeval"], required=True)
ap.add_argument("--data", required=True)
ap.add_argument("--systems", default="memory_lane,ml_dense,turn_bm25,full_context")
ap.add_argument("--k", type=int, default=10)
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--workers", type=int, default=int(os.getenv("ML_QA_WORKERS", "8")))
ap.add_argument("--judge_runs", type=int, default=1, help="repeat judging N times (Mem0 reports mean +- sd over 10)")
ap.add_argument("--include_abstention", action="store_true", help="LongMemEval: keep *_abs questions")
args = ap.parse_args()

REPO = os.environ.get("ML_REPO", ".")
OUT = os.environ.get("OUT_DIR", "results")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(REPO, "backend"))
os.environ.setdefault("ML_LLM_BACKEND", "deterministic")  # Memory Lane's own synthesis is not used here

from eval_llm_qa_client import Chat, judge, parse_json, reader  # noqa: E402


# ------------------------------------------------------------------ prompts
READER_SYSTEM = ("You answer questions about a person's past conversations using only the provided MEMORIES. "
                 "Memories are prefixed with the date they were recorded. Resolve relative time expressions "
                 "(e.g. 'last week') against that date. Answer in as few words as possible (a short phrase); "
                 "if the memories do not contain the answer, reply exactly: I don't know.")


def reader_prompt(q, ctx_lines):
    now = f"Current date: {q['question_date']}\n" if q.get("question_date") else ""
    return f"MEMORIES:\n" + "\n".join(ctx_lines) + f"\n\n{now}QUESTION: {q['q']}\nANSWER:"


JUDGE_SYSTEM = "You are a strict but fair grader. Output JSON only."


def judge_prompt(q, pred):
    gold = q["answer"]
    if args.dataset == "locomo":
        return (f"Label the generated answer to a question as CORRECT or WRONG.\nQuestion: {q['q']}\n"
                f"Gold answer: {gold}\nGenerated answer: {pred}\n"
                "Be generous with wording: the generated answer is CORRECT if it conveys the same fact as the gold "
                "answer, even if longer. For dates and times, accept any format or relative expression that denotes "
                "the same date/period. It is WRONG if it is missing the key fact, contradicts it, or says it does not know.\n"
                'Return {"reasoning": "<one sentence>", "label": "CORRECT" or "WRONG"}.')
    t = q["cat"]
    rule = "Answer yes if the response contains the correct answer or an equivalent; no if it contains only part of it or is wrong."
    if q.get("abstention"):
        rule = "Answer yes if the response correctly says the question cannot be answered from the available information."
    elif t == "temporal-reasoning":
        rule += " Do not penalise off-by-one errors in numbers of days, weeks or months."
    elif t == "knowledge-update":
        rule += " If the response mentions outdated information along with the updated answer, it is correct as long as the updated answer is the one given as the answer."
    elif t == "single-session-preference":
        rule = ("The gold field is a rubric describing the desired personalised response. Answer yes if the response "
                "satisfies the rubric by correctly using the user's personal information; it need not mention every point.")
    return (f"Question: {q['q']}\nGold answer / rubric: {gold}\nModel response: {pred}\n{rule}\n"
            'Return {"reasoning": "<one sentence>", "label": "yes" or "no"}.')


def judge_label(raw):
    lab = str(parse_json(raw).get("label", raw)).strip().lower()
    return 1.0 if lab.startswith("correct") or lab.startswith("yes") else 0.0


# ------------------------------------------------------------------ lexical metrics
def _norm(s):
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    return [w for w in s.split() if w not in {"a", "an", "the"}]


def token_f1(pred, gold):
    p, g = _norm(pred), _norm(gold)
    common = Counter(p) & Counter(g)
    ns = sum(common.values())
    if not p or not g or ns == 0:
        return 0.0
    pr, rc = ns / len(p), ns / len(g)
    return 2 * pr * rc / (pr + rc)


def bleu1(pred, gold):
    p, g = _norm(pred), _norm(gold)
    if not p or not g:
        return 0.0
    clip = sum((Counter(p) & Counter(g)).values()) / len(p)
    bp = 1.0 if len(p) > len(g) else math.exp(1 - len(g) / len(p))
    return bp * clip


def approx_tokens(lines):
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return sum(len(enc.encode(x)) for x in lines)
    except Exception:
        return int(sum(len(x) for x in lines) / 4)


# ------------------------------------------------------------------ data + systems
users, questions = load(args.dataset, args.data, args.limit, args.include_abstention)
systems = args.systems.split(",")
print(f"{args.dataset}: {len(users)} histories, {len(questions)} questions; systems={systems}", flush=True)

contexts = {}  # (system, qid) -> list of lines

if any(s in systems for s in ("memory_lane", "ml_dense")):
    from app.core.database import init_db
    init_db()
    from app.ingestion.ingestion_service import ingestion_service
    from app.retrieval.hybrid_retriever import hybrid_retriever
    from app.storage.repository import Repository
    marker = os.path.join(os.environ.get("ML_DATA_DIR", "."), f".ingested_{args.dataset}_{len(users)}")
    if not os.path.exists(marker):
        t0 = time.perf_counter()
        for uid, turns in users.items():
            for i, t in enumerate(turns):
                ingestion_service.ingest_text_content(content=t["text"][:20000], title=f"{uid}__{i}", user_id=uid,
                                                      document_date=t["date"])
        open(marker, "w").write(str(time.perf_counter() - t0))
        print(f"Memory Lane ingestion: {time.perf_counter() - t0:.1f}s", flush=True)
    for q in questions:
        for s in ("memory_lane", "ml_dense"):
            if s in systems:
                kw = {"dense_only": True, "stratification_mode": "off"} if s == "ml_dense" else {}
                pack = hybrid_retriever.retrieve(query=q["q"], user_id=q["user"], top_k=args.k, **kw)
                contexts[(s, q["qid"])] = [f"[{t.event_date_start or 'undated'}] {t.statement}" for t in pack["results"]]

if "turn_bm25" in systems:
    from rank_bm25 import BM25Okapi
    idx = {uid: BM25Okapi([re.findall(r"\w+", t["text"].lower()) for t in turns]) for uid, turns in users.items()}
    for q in questions:
        turns = users[q["user"]]
        sc = idx[q["user"]].get_scores(re.findall(r"\w+", q["q"].lower()))
        top = sorted(np.argsort(-sc)[:args.k], key=lambda i: (turns[i]["date"] or "", i))
        contexts[("turn_bm25", q["qid"])] = [f"[{turns[i]['date']}] {turns[i]['text']}" for i in top]

if "full_context" in systems:
    for q in questions:
        contexts[("full_context", q["qid"])] = [f"[{t['date']}] {t['text']}" for t in users[q["user"]]]

if "mem0" in systems:
    os.environ.setdefault("MEM0_TELEMETRY", "False")
    from mem0 import Memory
    m0_path = os.path.join(OUT, f"mem0_store_{args.dataset}")
    cfg = {
        "llm": {"provider": "openai", "config": {"model": os.getenv("MEM0_LLM_MODEL", reader.model), "temperature": 0.0,
                                                 "openai_base_url": reader.base, "api_key": reader.key}},
        "embedder": {"provider": "openai", "config": {"model": os.getenv("MEM0_EMBED_MODEL", "text-embedding-3-small"),
                                                      "openai_base_url": os.getenv("MEM0_EMBED_BASE_URL", reader.base),
                                                      "api_key": os.getenv("MEM0_EMBED_API_KEY", reader.key),
                                                      "embedding_dims": int(os.getenv("MEM0_EMBED_DIMS", "1536"))}},
        "vector_store": {"provider": "qdrant", "config": {"path": os.path.join(m0_path, "qdrant"), "on_disk": True,
                                                          "collection_name": f"mlqa_{args.dataset}",
                                                          "embedding_model_dims": int(os.getenv("MEM0_EMBED_DIMS", "1536"))}},
        "history_db_path": os.path.join(m0_path, "history.db"),
    }
    os.makedirs(m0_path, exist_ok=True)
    mem = Memory.from_config(cfg)
    done_file = os.path.join(m0_path, "ingested_users.txt")
    done = set(open(done_file).read().split()) if os.path.exists(done_file) else set()
    for uid, turns in users.items():
        if uid in done:
            continue
        by_sess = defaultdict(list)
        for t in turns:
            by_sess[(t["session"], t["date"])].append(t)
        for (sess, date), ts in by_sess.items():
            # The OSS SDK (mem0ai 2.x) rejects `timestamp` (platform-only) and always uses today's date as the
            # "Observation Date" for resolving relative time. We therefore prefix every message with its real
            # session date. This is a known handicap for mem0 on temporal questions; report it with the results.
            msgs = [{"role": "user", "content": f"[{date}] {t['text']}"} for t in ts]
            mem.add(msgs, user_id=uid, metadata={"date": date, "session": sess})
        with open(done_file, "a") as f:
            f.write(uid + "\n")
    for q in questions:
        res = mem.search(q["q"], top_k=args.k, filters={"user_id": q["user"]})
        items = res.get("results", res) if isinstance(res, dict) else res
        lines = []
        for it in items:
            md = it.get("metadata") or {}
            lines.append(f"[{md.get('date') or (it.get('created_at') or '')[:10] or 'undated'}] {it.get('memory', '')}")
        contexts[("mem0", q["qid"])] = sorted(lines)

# ------------------------------------------------------------------ answer + judge (resumable)
ans_file = os.path.join(OUT, f"qa_{args.dataset}_answers.jsonl")
done = {}
if os.path.exists(ans_file):
    for l in open(ans_file):
        r = json.loads(l)
        done[(r["system"], r["qid"])] = r
lock = threading.Lock()


def work(item):
    s, q = item
    key = (s, q["qid"])
    if key in done and len(done[key].get("judge", [])) >= args.judge_runs:
        return done[key]
    ctx = contexts[key]
    t0 = time.perf_counter()
    pred = done[key]["prediction"] if key in done else reader(READER_SYSTEM, reader_prompt(q, ctx), max_tokens=100).strip()
    latency = done[key]["reader_latency_s"] if key in done else time.perf_counter() - t0
    labels = list(done.get(key, {}).get("judge", []))
    while len(labels) < args.judge_runs:
        labels.append(judge_label(judge(JUDGE_SYSTEM, judge_prompt(q, pred), json_out=True, max_tokens=200)))
    rec = {"system": s, "qid": q["qid"], "cat": q["cat"], "question": q["q"], "gold": q["answer"],
           "prediction": pred, "judge": labels, "f1": token_f1(pred, q["answer"]), "bleu1": bleu1(pred, q["answer"]),
           "context_tokens": approx_tokens(ctx), "n_context_items": len(ctx), "reader_latency_s": latency,
           "reader_model": reader.model, "judge_model": judge.model}
    with lock:
        with open(ans_file, "a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


jobs = [(s, q) for s in systems for q in questions]
recs = []
with ThreadPoolExecutor(max_workers=args.workers) as ex:
    for i, r in enumerate(ex.map(work, jobs)):
        recs.append(r)
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(jobs)}", flush=True)

# ------------------------------------------------------------------ summary
rng = np.random.default_rng(0)


def ci(x):
    x = np.asarray(x, float)
    m = x[rng.integers(0, len(x), (5000, len(x)))].mean(1)
    return [round(float(x.mean()), 4), round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]


summary = {}
for s in systems:
    rs = [r for r in recs if r["system"] == s]
    acc = [float(np.mean(r["judge"])) for r in rs]
    runs = np.array([r["judge"] for r in rs]).T  # judge_runs x n
    summary[s] = {"n": len(rs), "J": ci(acc), "J_sd_over_judge_runs": round(float(runs.mean(1).std()), 4) if len(runs) > 1 else None,
                  "F1": round(float(np.mean([r["f1"] for r in rs])), 4), "BLEU1": round(float(np.mean([r["bleu1"] for r in rs])), 4),
                  "mean_context_tokens": round(float(np.mean([r["context_tokens"] for r in rs])), 1),
                  "reader_latency_p50_s": round(float(np.percentile([r["reader_latency_s"] for r in rs], 50)), 3),
                  "J_by_category": {c: round(float(np.mean([float(np.mean(r["judge"])) for r in rs if r["cat"] == c])), 4)
                                    for c in sorted({r["cat"] for r in rs})}}
summary["_meta"] = {"dataset": args.dataset, "k": args.k, "reader_model": reader.model, "judge_model": judge.model,
                    "reader_calls": reader.calls, "reader_prompt_tokens": reader.prompt_tokens,
                    "judge_calls": judge.calls, "n_questions": len(questions), "judge_runs": args.judge_runs}
json.dump(summary, open(os.path.join(OUT, f"qa_{args.dataset}_summary.json"), "w"), indent=1)
for s in systems:
    v = summary[s]
    print(f"{s:14s} J={v['J']} F1={v['F1']} B1={v['BLEU1']} ctx_tokens={v['mean_context_tokens']}")
