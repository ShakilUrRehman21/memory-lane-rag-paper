"""Summaries (95% bootstrap CIs, paired Wilcoxon vs. a reference config) for bench_conversations.py output.
For LoCoMo also reports the held-out half (conversations 6-10) not used by select_stratification.py."""
import json, os, re, sys
import numpy as np
from scipy import stats
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conv_data import locomo_items
OUT = os.environ.get("OUT_DIR", "results")
fn = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "conv_locomo.json")
ref = sys.argv[2] if len(sys.argv) > 2 else "ml_router"
D = json.load(open(fn)); R = D["results"]; L = D["latency"]
subsets = {"all": None}
if D["meta"]["dataset"] == "locomo":
    users, qs = locomo_items(os.environ.get("LOCOMO_JSON", "data/locomo10.json"))
    qs = [q for q in qs if q["gold"]]
    held = set(list(users)[5:])
    subsets["heldout_conv6-10"] = np.array([q["user"] in held for q in qs])
rng = np.random.default_rng(0)
def ci(x):
    x = np.asarray(x, float); m = x[rng.integers(0, len(x), (5000, len(x)))].mean(1)
    return [round(float(x.mean()), 4), round(float(np.percentile(m, 2.5)), 4), round(float(np.percentile(m, 97.5)), 4)]
out = {}
for sub, mask in subsets.items():
    out[sub] = {}
    for name, rows in R.items():
        idx = range(len(rows)) if mask is None else np.where(mask)[0]
        rs = [rows[i] for i in idx]
        e = {m: ci([r[m] for r in rs]) for m in ["R@5", "R@10", "N@10", "H@5"]}
        e["n"] = len(rs)
        e["per_category_R@5"] = {c: round(float(np.mean([r["R@5"] for r in rs if r["cat"] == c])), 4) for c in sorted({r["cat"] for r in rs})}
        e["latency_p50_ms"] = round(float(np.percentile(L[name], 50)), 1)
        if name != ref and ref in R:
            a = np.array([r["R@5"] for r in rs]); b = np.array([R[ref][i]["R@5"] for i in idx])
            e[f"wilcoxon_p_vs_{ref}"] = float(stats.wilcoxon(a, b, zero_method="zsplit").pvalue) if np.any(a != b) else 1.0
        out[sub][name] = e
json.dump({"meta": D["meta"], "summary": out}, open(fn.replace(".json", "_summary.json"), "w"), indent=1)
for sub in out:
    print(f"== {sub}")
    for n, e in out[sub].items():
        print(f"  {n:16s} R@5={e['R@5']} R@10={e['R@10'][0]} n={e['n']} p={e.get(f'wilcoxon_p_vs_{ref}', '-')}")
