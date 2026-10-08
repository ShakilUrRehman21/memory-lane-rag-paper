import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8.5, "axes.linewidth": 0.6,
    "ps.fonttype": 42, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "lines.linewidth": 1.2})
MM = 1 / 25.4
BLUE, GREY, DARK = "#1f4e79", "#8c8c8c", "#222222"

def save(fig, name):
    for ext, kw in (("eps", {}), ("png", {"dpi": 600}), ("tif", {"dpi": 600, "pil_kwargs": {"compression": "tiff_lzw"}})):
        fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.{ext}"), bbox_inches="tight", pad_inches=0.03, **kw)
    plt.close(fig)

# ---------------- Fig 1: architecture ----------------
fig, ax = plt.subplots(figsize=(174 * MM, 92 * MM))
ax.set_xlim(0, 174); ax.set_ylim(0, 92); ax.axis("off")
def box(cx, cy, w, h, name, sub, hi=False):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0,rounding_size=2",
                 fc="#dde7f2" if hi else "white", ec=DARK if hi else "#555555", lw=1.8 if hi else 0.7))
    ax.text(cx, cy + 2.4, name, ha="center", va="center", fontsize=8, fontweight="bold", color=DARK)
    ax.text(cx, cy - 2.9, sub, ha="center", va="center", fontsize=7, color="#333333")
def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=8, lw=0.7, color="#444444", shrinkA=0, shrinkB=0))
yA, yB, yC, h = 74, 44, 16, 13
ax.text(1, 86, "Ingestion path", fontsize=8, fontweight="bold", color="#444444")
ax.text(1, 56.5, "Query path", fontsize=8, fontweight="bold", color="#444444")
wa, xs = 32, [17, 52, 87, 122, 157]
for x, (n, s) in zip(xs, [("Documents", "four file formats"), ("Date parsing", "four dates each"), ("Chunking", "semantic chunks"),
                          ("Unit extraction", "rules or LLM"), ("Memory store", "SQLite, per user")]):
    box(x, yA, wa, h, n, s)
for a, b in zip(xs, xs[1:]):
    arrow(a + wa / 2, yA, b - wa / 2, yA)
wb, xb = 39, [21.5, 65, 108.5, 152]
for x, (n, s), hi in zip(xb, [("Question", "natural language"), ("Query router", "intent, topic, years"),
                              ("Hybrid retrieval", "BM25 + dense, RRF"), ("Stratified sampler", "gated by mode")], [0, 0, 0, 1]):
    box(x, yB, wb, h, n, s, bool(hi))
for a, b in zip(xb, xb[1:]):
    arrow(a + wb / 2, yB, b - wb / 2, yB)
ax.plot([157, 157, 108.5], [yA - h / 2, 61, 61], color="#444444", lw=0.7)
arrow(108.5, 61, 108.5, yB + h / 2)
ax.text(114, 62.6, "BM25 index + vectors", fontsize=7.5, color="#333333")
for x, (n, s), hi in zip([152, 108.5, 65], [("Change detection", "query-focused"), ("Grounded synthesis", "citations checked"),
                                         ("Answer", "claims + timeline")], [1, 0, 0]):
    box(x, yC, wb, h, n, s, bool(hi))
arrow(152, yB - h / 2, 152, yC + h / 2)
arrow(152 - wb / 2, yC, 108.5 + wb / 2, yC)
arrow(108.5 - wb / 2, yC, 65 + wb / 2, yC)
ax.add_patch(FancyBboxPatch((2, 4), 6, 4, boxstyle="round,pad=0,rounding_size=1", fc="#dde7f2", ec=DARK, lw=1.8))
ax.text(10, 6, "Components whose design choices are evaluated in Sections 7 and 8", fontsize=7.5, va="center", color="#333333")
save(fig, "Fig1")

# ---------------- Fig 2: temporal coverage ----------------
rows = [("Baseline (dense top-k)", .932, .712, .694, .730), ("Temporal RAG", .932, .712, .694, .730),
        ("Memory Lane (default)", .943, .864, .844, .883), ("Initial design (v1.0)", .975, .887, .868, .906),
        ("Memory Lane, always", .961, .979, .971, .985), ("Memory Lane, always + year bins", 1.0, 1.0, 1.0, 1.0)]
fig, ax = plt.subplots(figsize=(174 * MM, 74 * MM))
for i, (n, u, s, lo, hi) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.plot([u, s], [y, y], color="#b0b0b0", lw=1.0, zorder=1)
    ax.plot([lo, hi], [y, y], color=BLUE, lw=2.0, zorder=2)
    ax.scatter([u], [y], s=34, facecolors="white", edgecolors=DARK, linewidths=1.0, zorder=3, marker="o")
    ax.scatter([s], [y], s=38, color=BLUE, zorder=4, marker="D")
    if s == u:
        ax.text(lo - 0.006, y, f"{s:.2f} (both)", ha="right", va="center", fontsize=7.5, fontweight="bold")
    elif s < u:
        ax.text(lo - 0.006, y, f"{s:.2f}", ha="right", va="center", fontsize=7.5, fontweight="bold")
        ax.text(u + 0.007, y, f"{u:.2f}", ha="left", va="center", fontsize=7.5, color="#444444")
    else:
        ax.text(hi + 0.006, y, f"{s:.2f}", ha="left", va="center", fontsize=7.5, fontweight="bold")
        ax.text(u - 0.007, y, f"{u:.2f}", ha="right", va="center", fontsize=7.5, color="#444444")
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows][::-1])
ax.set_xlim(0.6, 1.035); ax.set_ylim(-0.6, len(rows) - 0.4)
ax.set_xlabel("Temporal coverage recall (share of the persona's years among the 8 retrieved units)")
ax.grid(axis="x", color="#e3e3e3", lw=0.5); ax.set_axisbelow(True)
ax.tick_params(axis="y", length=0)
ax.scatter([], [], s=34, facecolors="white", edgecolors=DARK, label="Uniform density")
ax.scatter([], [], s=38, color=BLUE, marker="D", label="Skewed density (with 95% bootstrap interval)")
ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2, frameon=False, fontsize=7.5, handletextpad=0.3, columnspacing=1.5)
save(fig, "Fig2")

# ---------------- Fig 3: scaling ----------------
v10 = json.load(open(os.path.join(R, "scale_v10.json"))); v11 = json.load(open(os.path.join(R, "scale_v11.json")))
fig, ax = plt.subplots(figsize=(120 * MM, 72 * MM))
ax.plot([r["docs"] for r in v10], [r["ingest_ms_per_doc_last100"] for r in v10], "s--", color=GREY, ms=4, label="Initial design (v1.0)")
ax.plot([r["docs"] for r in v11], [r["ingest_ms_per_doc_last100"] for r in v11], "o-", color=BLUE, ms=4, label="Current design")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xticks([250, 500, 1000, 2000, 5000, 10000]); ax.set_xticklabels(["250", "500", "1,000", "2,000", "5,000", "10,000"])
ax.set_yticks([10, 30, 100, 300, 1000]); ax.set_yticklabels(["10", "30", "100", "300", "1,000"])
ax.minorticks_off(); ax.set_ylim(8, 1600); ax.set_xlim(200, 13000)
ax.set_xlabel("Documents already in the store (log scale)"); ax.set_ylabel("Ingestion time per new document, ms (log scale)")
a = next(r for r in v10 if r["docs"] == 1000)["ingest_ms_per_doc_last100"]; b = next(r for r in v11 if r["docs"] == 1000)["ingest_ms_per_doc_last100"]
ax.plot([1000, 1000], [b * 1.15, a * 0.87], ":", color="#555555", lw=0.8)
ax.text(1080, (a * b) ** 0.5, f"{a / b:.0f}× less time\nper document", fontsize=7.5, va="center")
ax.text(1080, a, f"{a:.0f} ms", fontsize=7.5, va="center")
ax.text(1000, b * 0.72, f"{b:.0f} ms", fontsize=7.5, ha="center", va="top")
last = v11[-1]; ax.text(last["docs"], last["ingest_ms_per_doc_last100"] * 1.25, f"{last['ingest_ms_per_doc_last100']:.0f} ms", fontsize=7.5, ha="center")
ax.grid(color="#e8e8e8", lw=0.5); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=7.5, loc="upper right")
save(fig, "Fig3")
print("Figs. 1-3 written as EPS, PNG and TIFF")
