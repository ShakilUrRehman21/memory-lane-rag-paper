"""
Builds MLLB-Synth v1 (Memory Lane Longitudinal Benchmark, synthetic part) as static files.

  data/mllb_synth_v1/documents.jsonl   one dated document per line
  data/mllb_synth_v1/queries.jsonl     queries with ground truth
  data/mllb_synth_v1/personas.jsonl    generation metadata per persona

Splits
  dev  : the 2x2x2 design used during development of v1.1 (seed 42, identical to the
         96 personas of the original audit). Results on it may be optimistic.
  test : HELD-OUT. Different topics, different stance templates, different neutral and
         distractor templates, extra query wordings, and "stable" control personas whose
         stance never changes (to measure false alarms). Written after the v1.1 code was
         frozen; must not be used for tuning.

Usage: python scripts/build_mllb_synth.py [--out data/mllb_synth_v1]
"""
import argparse
import json
import os
import random

DEV = dict(
    seed=42,
    in_lex=["Java", "Python", "Rust", "Kubernetes"],
    out_lex=["Haskell", "Elixir", "Terraform", "Kotlin"],
    distract=["gardening", "marathon training", "cooking", "chess"],
    lex_neg=["I honestly don't think {T} is worth my time right now.",
             "I am skeptical about {T} and it feels not relevant to my work.",
             "I do not want to spend effort on {T} this year."],
    lex_pos=["I started learning {T} and I am excited about it.",
             "I am now committed to {T} for all my new projects.",
             "I love working with {T} and want to specialize in it."],
    par_neg=["Frankly, {T} feels like a dead end for someone like me.",
             "I can't see myself ever touching {T} in a serious project.",
             "{T} seems overhyped, so I keep my distance from it."],
    par_pos=["These days {T} is the tool I reach for first.",
             "I've grown to really appreciate {T} after using it daily.",
             "Picking up {T} turned out to be the best call I made."],
    neutral=["I read a long article about {T} on the train today.",
             "A colleague mentioned {T} during our team lunch.",
             "There was a meetup about {T} in the city this month."],
    dist=["I spent the weekend on {D} and it was relaxing.",
          "My routine now includes {D} twice a week.",
          "I bought a new book about {D} at the store."],
    queries={"evolution": "How has my view on {T} changed over the years?",
             "plain": "What do I think about {T}?"},
    stable_per_cell=0,
)

TEST = dict(
    seed=7,
    in_lex=["TypeScript", "Docker", "PostgreSQL", "React"],
    out_lex=["Clojure", "Svelte", "Ansible", "Julia"],
    distract=["birdwatching", "pottery", "salsa dancing", "sourdough baking"],
    lex_neg=["I am not interested in {T} at all right now.",
             "Honestly {T} feels like a waste of time for my team.",
             "I have been avoiding {T} because it seems unnecessary."],
    lex_pos=["I am passionate about {T} and use it for everything now.",
             "I am fascinated by {T} and focusing on it this quarter.",
             "I strongly prefer {T} over the alternatives these days."],
    par_neg=["{T} keeps getting in my way, and I'd rather not deal with it.",
             "Nobody will convince me that {T} is worth the hassle.",
             "Every time I try {T} I end up regretting it."],
    par_pos=["{T} has quietly become a big part of how I work.",
             "I keep recommending {T} to everyone who will listen.",
             "Switching to {T} was one of my better decisions."],
    neutral=["Saw a conference talk on {T} that was mostly about tooling.",
             "Someone in the forum asked a question about {T}.",
             "The newsletter this week had a section on {T}."],
    dist=["Went {D} with friends on Saturday morning.",
          "Spent the evening on {D}, which helped me unwind.",
          "Signed up for a beginner course in {D}."],
    queries={"evolution": "How has my view on {T} changed over the years?",
             "plain": "What do I think about {T}?",
             "when_changed": "When did my opinion of {T} turn around?",
             "history": "Give me the history of my relationship with {T}."},
    stable_per_cell=1,
)


def rdate(rng, y):
    return f"{y}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


def build_split(name, cfg, docs, queries, personas):
    rng = random.Random(cfg["seed"])
    for lex_cond, topics in [("in_lexicon", cfg["in_lex"]), ("out_of_lexicon", cfg["out_lex"])]:
        for phrasing in ["lexicon", "paraphrase"]:
            neg, pos = ((cfg["lex_neg"], cfg["lex_pos"]) if phrasing == "lexicon" else (cfg["par_neg"], cfg["par_pos"]))
            for density in ["uniform", "skewed"]:
                for topic in topics:
                    kinds = ["reversal"] * 3 + ["stable"] * cfg["stable_per_cell"]
                    for s, kind in enumerate(kinds):
                        uid = f"{name}_{lex_cond}_{phrasing}_{density}_{topic}_{s}".replace(" ", "")
                        y0 = rng.choice([2018, 2019, 2020])
                        years = list(range(y0, y0 + 6))
                        flip = y0 + rng.choice([2, 3]) if kind == "reversal" else None
                        stable_sign = rng.choice(["pos", "neg"]) if kind == "stable" else None
                        pdocs = []
                        for y in years:
                            if kind == "reversal":
                                tpl = rng.choice(neg if y < flip else pos)
                            else:
                                tpl = rng.choice(pos if stable_sign == "pos" else neg)
                            pdocs.append(("stance", rdate(rng, y), tpl.format(T=topic)))
                            pdocs.append(("neutral", rdate(rng, y), rng.choice(cfg["neutral"]).format(T=topic)))
                            d = rng.choice(cfg["distract"])
                            pdocs.append(("distractor", rdate(rng, y), rng.choice(cfg["dist"]).format(D=d)))
                        if density == "skewed":
                            late_pool = (pos if (kind == "reversal" or stable_sign == "pos") else neg) + cfg["neutral"]
                            for _ in range(12):
                                tpl = rng.choice(late_pool)
                                pdocs.append(("burst", rdate(rng, years[-1]), tpl.format(T=topic)))
                        for i, (role, date, text) in enumerate(pdocs):
                            docs.append({"split": name, "persona_id": uid, "doc_id": f"{uid}_d{i:02d}", "date": date,
                                         "role": role, "text": text})
                        gt = [[str(flip - 1), str(flip), "reversal"]] if kind == "reversal" else []
                        for qk, qt in cfg["queries"].items():
                            queries.append({"split": name, "query_id": f"{uid}__{qk}", "persona_id": uid,
                                            "query": qt.format(T=topic), "query_style": qk, "topic": topic,
                                            "expected_years": [str(y) for y in years],
                                            "ground_truth_transitions": gt})
                        personas.append({"split": name, "persona_id": uid, "topic": topic, "lexicon": lex_cond,
                                         "phrasing": phrasing, "density": density, "kind": kind,
                                         "flip_year": flip, "stable_sign": stable_sign, "years": years,
                                         "n_documents": len(pdocs)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/mllb_synth_v1")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    docs, queries, personas = [], [], []
    build_split("dev", DEV, docs, queries, personas)
    build_split("test", TEST, docs, queries, personas)
    for fn, rows in [("documents.jsonl", docs), ("queries.jsonl", queries), ("personas.jsonl", personas)]:
        with open(os.path.join(a.out, fn), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
    for sp in ["dev", "test"]:
        print(sp, "personas", sum(p["split"] == sp for p in personas), "documents", sum(d["split"] == sp for d in docs),
              "queries", sum(q["split"] == sp for q in queries))


if __name__ == "__main__":
    main()
