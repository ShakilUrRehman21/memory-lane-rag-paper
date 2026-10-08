"""Regenerates all paper figures from the files in results/ (no system code is run)."""
import json, os, sys
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conv_data import locomo_items
R, F = os.environ.get("OUT_DIR", "results"), os.environ.get("FIG_DIR", "figures")
os.makedirs(F, exist_ok=True)
plt.rcParams.update({"font.size": 9, "figure.dpi": 200, "axes.spines.top": False, "axes.spines.right": False})
BLUE, GREY, ORANGE, GREEN = "#2f6f9f", "#9aa5b1", "#c0703a", "#4f8f5f"
M = json.load(open(os.path.join(R, "mllb_summary.json")))["summary"]
# Run labels -> actual settings (at run time the v1.1 "default" config was always-stratify + adaptive epochs)
LAB = {"test|v1.0|baseline": "v1.0 baseline", "test|v1.0|memory_lane": "v1.0 Memory Lane",
       "test|v1.1:default|baseline": "v1.1 baseline (dense)", "test|v1.1:default|temporal": "v1.1 temporal RAG",
       "test|v1.1:router_strat|memory_lane": "v1.1 ML: router (default)", "test|v1.1:default|memory_lane": "v1.1 ML: always",
       "test|v1.1:year_epochs|memory_lane": "v1.1 ML: always, year bins"}

def bars(ax, keys, metric, sub="all", color=None, fmt="%.2f"):
    v = [M[k][sub][metric] for k in keys]
    m = [x[0] for x in v]; lo = [x[0] - x[1] for x in v]; hi = [x[2] - x[0] for x in v]
    b = ax.bar(range(len(keys)), m, yerr=[lo, hi], capsize=2, color=color or [BLUE if "v1.1 ML" in LAB.get(k, k) else GREY for k in keys])
    ax.bar_label(b, fmt=fmt, fontsize=7, padding=2)
    return b

# Fig 1: temporal coverage on MLLB-Synth test, by density
keys = list(LAB)
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
for ax, d in zip(axs, ["uniform", "skewed"]):
    v = [M[k]["by_density"][d]["TCR"] for k in keys]
    b = ax.bar(range(len(keys)), [x[0] for x in v], yerr=[[x[0] - x[1] for x in v], [x[2] - x[0] for x in v]], capsize=2,
               color=[BLUE if "ML" in LAB[k] or "Memory Lane" in LAB[k] else GREY for k in keys])
    ax.bar_label(b, fmt="%.2f", fontsize=6.5, padding=2)
    ax.set_xticks(range(len(keys)), [LAB[k] for k in keys], rotation=40, ha="right", fontsize=7)
    ax.set_title(f"{d} density", fontsize=8.5); ax.set_ylim(0.5, 1.08)
axs[0].set_ylabel("Temporal Coverage Recall (95% CI)")
fig.suptitle("MLLB-Synth test (held out): temporal coverage, 512 queries per system", fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(F, "fig1_mllb_temporal_coverage.png")); plt.close()

# Fig 2: change / reversal detection and false alarms
ks = ["test|v1.0|memory_lane", "test|v1.1:router_strat|memory_lane", "test|v1.1:default|memory_lane",
      "test|v1.1:no_query_focus|memory_lane", "test|v1.1:hash_embed|memory_lane"]
names = ["v1.0", "v1.1 router\n(default)", "v1.1 always", "v1.1 always\nno query focus", "v1.1 always\nhash vectors"]
fig, ax = plt.subplots(figsize=(7.2, 3.2)); w = 0.26; x = np.arange(len(ks))
for i, (met, lab, col) in enumerate([("CP_F1", "Change-point F1", ORANGE), ("reversal_found", "Reversals found", BLUE),
                                     ("false_alarm_stable", "False alarms (stable personas)", GREY)]):
    v = [M[k]["all"][met] for k in ks]
    b = ax.bar(x + (i - 1) * w, [a[0] for a in v], w, yerr=[[a[0] - a[1] for a in v], [a[2] - a[0] for a in v]], capsize=2, color=col, label=lab)
    ax.bar_label(b, fmt="%.2f", fontsize=6.5, padding=1)
ax.set_xticks(x, names, fontsize=7.5); ax.set_ylim(0, 0.75); ax.legend(frameon=False, fontsize=7.5, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.12))
ax.set_ylabel("rate / F1 (95% CI)")
plt.tight_layout(); plt.savefig(os.path.join(F, "fig2_mllb_change_detection.png")); plt.close()

# Fig 3: LoCoMo held-out conversations 6-10, Recall@5
S = json.load(open(os.path.join(R, "conv_locomo_summary.json")))["summary"]["heldout_conv6-10"]
users, qs = locomo_items(os.environ.get("LOCOMO_JSON", "data/locomo10.json")); qs = [q for q in qs if q["gold"]]
held = np.array([q["user"] in set(list(users)[5:]) for q in qs])
v10 = json.load(open(os.path.join(R, "locomo_v10_per_question.json")))["results"]["ml_full"]
rng = np.random.default_rng(0); x10 = np.array([r["R@5"] for r in v10])[held]
b10 = x10[rng.integers(0, len(x10), (5000, len(x10)))].mean(1)
rows = [("v1.0 Memory Lane (as shipped)", [x10.mean(), np.percentile(b10, 2.5), np.percentile(b10, 97.5)], GREY),
        ("v1.1 ML: always", S["ml_default"]["R@5"], BLUE), ("v1.1 ML: dense only", S["ml_dense_only"]["R@5"], BLUE),
        ("v1.1 ML: router (default)", S["ml_router"]["R@5"], BLUE), ("BM25 (turns)", S["ext_bm25"]["R@5"], GREY),
        ("BM25 + dense RRF (turns)", S["ext_hybrid"]["R@5"], GREY), ("v1.1 ML: FTS5 BM25 only", S["ml_sparse_only"]["R@5"], BLUE)]
rows = sorted(rows, key=lambda r: r[1][0]); print("LoCoMo held-out:", [(r[0], round(float(r[1][0]), 3)) for r in rows])
fig, ax = plt.subplots(figsize=(6.4, 3.2)); y = np.arange(len(rows))
for i, (n, v, c) in enumerate(rows):
    ax.barh(i, v[0], xerr=[[v[0] - v[1]], [v[2] - v[0]]], color=c, capsize=2); ax.text(v[2] + 0.008, i, f"{v[0]:.3f}", va="center", fontsize=7.5)
ax.set_yticks(y, [r[0] for r in rows]); ax.set_xlim(0, 0.56); ax.set_xlabel("Recall@5 (95% CI)")
ax.set_title("LoCoMo, held-out conversations 6-10 (776 questions)", fontsize=8.5)
plt.tight_layout(); plt.savefig(os.path.join(F, "fig3_locomo_heldout_recall.png")); plt.close()

# Fig 4: coverage / precision trade-off of stratification modes (dev data used for selection)
C = json.load(open(os.path.join(R, "stratification_selection_dev.json")))
fig, ax = plt.subplots(figsize=(4.8, 3.4))
for c in C["candidates"]:
    lab = c["mode"] + (f" {c['soft_fraction']}" if c["soft_fraction"] is not None else "")
    sel = c == C["selected"]
    ax.scatter(c["locomo_dev_R@5"], c["mllb_dev_TCR"], s=60 if sel else 30, color=ORANGE if sel else BLUE, zorder=3)
    ax.annotate(lab + (" (selected)" if sel else ""), (c["locomo_dev_R@5"], c["mllb_dev_TCR"]), textcoords="offset points", xytext=(5, -3), fontsize=7.5)
off = [c for c in C["candidates"] if c["mode"] == "off"][0]["locomo_dev_R@5"]
ax.axvline(off - 0.01, color=GREY, ls="--", lw=0.8); ax.text(off - 0.0095, 0.87, "max. allowed\nrecall loss", fontsize=6.5, color="#555")
ax.set_xlabel("LoCoMo-dev Recall@5 (fact lookup)"); ax.set_ylabel("MLLB-dev temporal coverage")
ax.set_title("Stratification mode: coverage vs. precision (dev only)", fontsize=8.5); ax.set_xlim(0.29, 0.43)
plt.tight_layout(); plt.savefig(os.path.join(F, "fig4_stratification_tradeoff.png")); plt.close()

# Fig 5: scaling
fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.8))
for tag, col, lab in [("v10", GREY, "v1.0"), ("v11", BLUE, "v1.1")]:
    p = os.path.join(R, f"scale_{tag}.json")
    if not os.path.exists(p): continue
    s = json.load(open(p)); d = [r["docs"] for r in s]
    axs[0].plot(d, [r["ingest_ms_per_doc_last100"] for r in s], "o-", color=col, label=lab)
    axs[1].plot(d, [r["query_p50_ms"] for r in s], "o-", color=col, label=lab)
for ax, yl in zip(axs, ["ingest time per new document (ms)", "retrieval latency p50 (ms)"]):
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("documents in store"); ax.set_ylabel(yl); ax.legend(frameon=False)
fig.suptitle("Scaling, persistence on, idle single-core CPU", fontsize=9); plt.tight_layout()
plt.savefig(os.path.join(F, "fig5_scaling.png")); plt.close()
print("figures written to", F)
