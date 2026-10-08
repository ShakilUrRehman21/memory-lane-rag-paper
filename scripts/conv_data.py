"""Shared loaders for LoCoMo and LongMemEval (used by bench_conversations.py and eval_llm_qa.py)."""
import json
import re
from datetime import datetime

LOCOMO_CATS = {1: "multi_hop", 2: "temporal", 3: "open_domain", 4: "single_hop"}


def locomo_items(path):
    """users: {sample_id: [turn,...]}; turn = {unit: dia_id, session, date, speaker, text}."""
    data = json.load(open(path))
    users, questions = {}, []
    for conv in data:
        sid, c = conv["sample_id"], conv["conversation"]
        turns = []
        for s in sorted({int(k.split("_")[1]) for k in c if re.fullmatch(r"session_\d+", k)}):
            m = re.search(r"on (\d{1,2}) (\w+),? (\d{4})", c[f"session_{s}_date_time"])
            date = datetime.strptime(" ".join(m.groups()), "%d %B %Y").strftime("%Y-%m-%d")
            for t in c[f"session_{s}"]:
                turns.append({"unit": t["dia_id"], "session": f"S{s}", "date": date, "speaker": t["speaker"],
                              "text": f"{t['speaker']}: {t['text']}"})
        users[sid] = turns
        for i, q in enumerate(conv["qa"]):
            if q["category"] == 5:  # adversarial, excluded as in Mem0 / Zep evaluations
                continue
            ev = set(re.findall(r"D\d+:\d+", " ".join(q["evidence"])))
            questions.append({"qid": f"{sid}_q{i}", "user": sid, "q": q["question"], "gold": ev,
                              "cat": LOCOMO_CATS[q["category"]], "answer": str(q.get("answer", "")),
                              "question_date": None})
    return users, questions


def lme_date(s):
    m = re.match(r"(\d{4})/(\d{2})/(\d{2})", s or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def longmemeval_items(path, limit=0, include_abstention=False):
    """One user per question (each question has its own haystack). unit = session id."""
    data = json.load(open(path))
    if not include_abstention:
        data = [d for d in data if not str(d["question_id"]).endswith("_abs")]
    if limit:
        data = data[:limit]
    users, questions = {}, []
    for d in data:
        uid = f"lme_{d['question_id']}"
        turns = []
        for sid, date, sess in zip(d["haystack_session_ids"], d["haystack_dates"], d["haystack_sessions"]):
            for t in sess:
                turns.append({"unit": sid, "session": sid, "date": lme_date(date), "speaker": t["role"],
                              "text": f"{t['role']}: {t['content']}"})
        users[uid] = turns
        questions.append({"qid": str(d["question_id"]), "user": uid, "q": d["question"],
                          "gold": set(d["answer_session_ids"]), "cat": d["question_type"],
                          "answer": str(d.get("answer", "")), "question_date": lme_date(d.get("question_date")),
                          "abstention": str(d["question_id"]).endswith("_abs")})
    return users, questions


def load(dataset, path, limit=0, include_abstention=False):
    if dataset == "locomo":
        users, qs = locomo_items(path)
        return users, (qs[:limit] if limit else qs)
    return longmemeval_items(path, limit, include_abstention)
