"""
Convert adjudicated MLLB-Human annotations into the MLLB file format used by
scripts/eval_mllb_synth.py (split name "human"). Transitions with annotator_id == "gold" are used.
Usage: python convert_to_mllb.py <annotation dir> <output dir>
"""
import csv, json, os, sys
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
R = lambda fn: list(csv.DictReader(open(os.path.join(src, fn), encoding="utf-8")))
docs, trans, qs, pers = R("documents.csv"), R("transitions.csv"), R("queries.csv"), R("personas.csv")
date_of = {d["doc_id"]: d["date"] for d in docs}
with open(os.path.join(out, "documents.jsonl"), "w") as f:
    for d in docs:
        f.write(json.dumps({"split": "human", "persona_id": d["persona_id"], "doc_id": d["doc_id"], "date": d["date"],
                            "role": "document", "text": d["text"]}) + "\n")
gold = [t for t in trans if t["annotator_id"] == "gold"]
# Years covered by a topic = documents containing a sentence labelled with that topic
# (adjudicated statements_gold.csv if present, otherwise the union of all annotators).
import glob
stmt_files = [os.path.join(src, "statements_gold.csv")] if os.path.exists(os.path.join(src, "statements_gold.csv")) \
    else glob.glob(os.path.join(src, "statements_*.csv"))
topic_docs = {}
for fn in stmt_files:
    for r in csv.DictReader(open(fn, encoding="utf-8")):
        if r.get("topic"):
            topic_docs.setdefault(r["topic"].lower(), set()).add(r["doc_id"])
kinds = {}
with open(os.path.join(out, "queries.jsonl"), "w") as f:
    for q in qs:
        topic = q["topic"]
        tt = [t for t in gold if t["persona_id"] == q["persona_id"] and t["topic"].lower() == topic.lower()]
        gt = [[date_of[t["from_doc_id"]][:4], date_of[t["to_doc_id"]][:4], t["change_type"]] for t in tt]
        years = sorted({date_of[did][:4] for did in topic_docs.get(topic.lower(), set())
                        if did.startswith(q["persona_id"]) or any(d["doc_id"] == did and d["persona_id"] == q["persona_id"] for d in docs)})
        kinds[q["persona_id"]] = "reversal" if any(t["change_type"] == "reversal" for t in tt) else ("stable" if not tt else "change")
        f.write(json.dumps({"split": "human", "query_id": q["query_id"], "persona_id": q["persona_id"], "query": q["query"],
                            "query_style": q["query_style"], "topic": topic, "expected_years": years,
                            "ground_truth_transitions": gt, "gold_answer": q.get("gold_answer", "")}) + "\n")
with open(os.path.join(out, "personas.jsonl"), "w") as f:
    for p in pers:
        f.write(json.dumps({"split": "human", "persona_id": p["persona_id"], "topic": p["topic"], "source": p["source"],
                            "lexicon": "n/a", "phrasing": "human", "density": "natural",
                            "kind": kinds.get(p["persona_id"], "stable")}) + "\n")
print("wrote", out, len(docs), "documents,", len(qs), "queries")
