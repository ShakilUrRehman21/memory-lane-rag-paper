"""Summaries with 95% bootstrap CIs and paired Wilcoxon tests for eval_mllb_synth.py outputs."""
import json
import os
import sys
from collections import defaultdict

import numpy as np
from scipy import stats

OUT = os.environ.get("OUT_DIR", "results")
rng = np.random.default_rng(0)


def ci(x):
    x = np.asarray([v for v in x if v is not None], float)
    if len(x) == 0:
        return None
    m = x[rng.integers(0, len(x), (5000, len(x)))].mean(1)
    return [round(float(x.mean()), 3), round(float(np.percentile(m, 2.5)), 3), round(float(np.percentile(m, 97.5)), 3), len(x)]


def paired_p(a_rows, b_rows, key):
    a = {r["query_id"]: r[key] for r in a_rows}; b = {r["query_id"]: r[key] for r in b_rows}
    ids = [i for i in a if i in b and a[i] is not None and b[i] is not None]
    x, y = np.array([a[i] for i in ids]), np.array([b[i] for i in ids])
    if len(ids) == 0 or np.all(x == y):
        return 1.0
    return float(stats.wilcoxon(x, y, zero_method="zsplit").pvalue)


def summarize(rows):
    return {"TCR": ci(r["TCR"] for r in rows),
            "CP_F1": ci(r["cp_f1"] for r in rows if r["kind"] == "reversal"),
            "CP_F1_tol1": ci(r["cp_f1_tol1"] for r in rows if r["kind"] == "reversal"),
            "CP_precision": ci(r["cp_precision"] for r in rows if r["kind"] == "reversal"),
            "reversal_found": ci(r["reversal_found"] for r in rows if r["kind"] == "reversal"),
            "false_alarm_stable": ci(r["false_alarm"] for r in rows if r["kind"] == "stable"),
            "changes_per_query": round(float(np.mean([r["n_changes"] for r in rows])), 2),
            "latency_p50_ms": round(float(np.percentile([r["latency_ms"] for r in rows], 50)), 1)}


def main(files):
    groups = defaultdict(list)
    for fn in files:
        d = json.load(open(fn))
        for r in d["rows"]:
            groups[(d["meta"]["split"], r["config"], r["pipeline"])].append(r)
    out = {}
    for (split, cfg, pipe), rows in sorted(groups.items()):
        key = f"{split}|{cfg}|{pipe}"
        out[key] = {"all": summarize(rows),
                    "by_query_style": {s: summarize([r for r in rows if r["query_style"] == s])
                                       for s in sorted({r["query_style"] for r in rows})},
                    "by_density": {s: summarize([r for r in rows if r["density"] == s]) for s in ["uniform", "skewed"]},
                    "by_lexicon_phrasing": {f"{l}|{p}": summarize([r for r in rows if r["lexicon"] == l and r["phrasing"] == p])
                                            for l in ["in_lexicon", "out_of_lexicon"] for p in ["lexicon", "paraphrase"]}}
    tests = {}
    for split in {k[0] for k in groups}:
        ref = groups.get((split, "v1.1:default", "memory_lane"))
        if not ref:
            continue
        for (sp, cfg, pipe), rows in groups.items():
            if sp != split or (cfg, pipe) == ("v1.1:default", "memory_lane"):
                continue
            tests[f"{split}|{cfg}|{pipe} vs v1.1:default|memory_lane"] = {
                k: paired_p(rows, ref, k) for k in ["TCR", "cp_f1", "reversal_found"]}
        # skewed-density TCR: baseline vs memory lane, per query style
        b = groups.get((split, "v1.1:default", "baseline"), [])
        for s in sorted({r["query_style"] for r in ref}):
            rs = [r for r in ref if r["query_style"] == s and r["density"] == "skewed"]
            bs = [r for r in b if r["query_style"] == s and r["density"] == "skewed"]
            tests[f"{split}|TCR skewed {s}: v1.1 baseline vs memory_lane"] = paired_p(bs, rs, "TCR")
    json.dump({"summary": out, "tests": tests}, open(os.path.join(OUT, "mllb_summary.json"), "w"), indent=1)
    for k, v in out.items():
        a = v["all"]
        print(f"{k:42s} TCR={a['TCR']} F1={a['CP_F1']} F1±1={a['CP_F1_tol1']} rev={a['reversal_found']} "
              f"FA={a['false_alarm_stable']} chg/q={a['changes_per_query']}")
    return out, tests


if __name__ == "__main__":
    main(sys.argv[1:] or [os.path.join(OUT, f) for f in sorted(os.listdir(OUT)) if f.startswith("mllb_v")])
