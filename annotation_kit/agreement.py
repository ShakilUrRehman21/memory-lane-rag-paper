"""
Inter-annotator agreement for MLLB-Human.
Input dir must contain statements_<A>.csv and statements_<B>.csv (labelled) and transitions.csv
with rows from both annotators. Usage: python agreement.py <dir> <annotatorA> <annotatorB>
"""
import csv, json, os, sys
from itertools import combinations
import numpy as np
from sklearn.metrics import cohen_kappa_score

d, A, B = sys.argv[1], sys.argv[2], sys.argv[3]
def load(a):
    return {(r["doc_id"], r["sent_idx"]): r for r in csv.DictReader(open(os.path.join(d, f"statements_{a}.csv"), encoding="utf-8"))}
sa, sb = load(A), load(B)
keys = sorted(set(sa) & set(sb))
mt_a, mt_b = [sa[k]["memory_type"] for k in keys], [sb[k]["memory_type"] for k in keys]
pa, pb = np.array([float(sa[k]["polarity"] or 0) for k in keys]), np.array([float(sb[k]["polarity"] or 0) for k in keys])

def alpha_interval(x, y):
    """Krippendorff's alpha (interval metric) for two coders, no missing values."""
    vals = np.concatenate([x, y]); n = len(vals)
    do = np.mean((x - y) ** 2)
    de = sum((a - b) ** 2 for a, b in combinations(vals, 2)) / (n * (n - 1) / 2)
    return 1 - do / de if de else 1.0

tr = list(csv.DictReader(open(os.path.join(d, "transitions.csv"), encoding="utf-8")))
docs = {r["doc_id"]: i for i, r in enumerate(csv.DictReader(open(os.path.join(d, "documents.csv"), encoding="utf-8")))}
def tset(a): return [(r["persona_id"], r["topic"].lower(), r["from_doc_id"], r["to_doc_id"]) for r in tr if r["annotator_id"] == a]
def tf1(x, y, tol):
    used, tp = set(), 0
    for p, t, f, to in x:
        for j, (p2, t2, f2, to2) in enumerate(y):
            if j in used or p != p2 or t != t2: continue
            if abs(docs[f] - docs[f2]) <= tol and abs(docs[to] - docs[to2]) <= tol:
                used.add(j); tp += 1; break
    p = tp / len(x) if x else 0; r = tp / len(y) if y else 0
    return 2 * p * r / (p + r) if p + r else (1.0 if not x and not y else 0.0)
res = {"n_statements": len(keys),
       "memory_type_kappa": round(float(cohen_kappa_score(mt_a, mt_b)), 3),
       "polarity_quadratic_kappa": round(float(cohen_kappa_score(pa.astype(int), pb.astype(int), weights="quadratic")), 3),
       "polarity_alpha_interval": round(float(alpha_interval(pa, pb)), 3),
       "polarity_sign_agreement": round(float(np.mean(np.sign(pa) == np.sign(pb))), 3),
       "transition_f1_exact": round(tf1(tset(A), tset(B), 0), 3),
       "transition_f1_tol1doc": round(tf1(tset(A), tset(B), 1), 3),
       "n_transitions": {A: len(tset(A)), B: len(tset(B))}}
print(json.dumps(res, indent=1))
json.dump(res, open(os.path.join(d, "agreement.json"), "w"), indent=1)
