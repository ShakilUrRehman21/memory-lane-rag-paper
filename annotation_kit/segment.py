"""Split documents.csv into one row per sentence -> statements_<annotator>.csv to be labelled.
Usage: python segment.py <dir with documents.csv> <annotator_id>"""
import csv, re, sys, os
d, ann = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(os.path.join(d, "documents.csv"), encoding="utf-8")))
out = os.path.join(d, f"statements_{ann}.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["doc_id", "sent_idx", "sentence", "annotator_id", "memory_type", "polarity", "topic"])
    for r in rows:
        for i, s in enumerate(x.strip() for x in re.split(r"(?<=[.!?])\s+", r["text"]) if x.strip()):
            w.writerow([r["doc_id"], i, s, ann, "", "", ""])
print("wrote", out)
