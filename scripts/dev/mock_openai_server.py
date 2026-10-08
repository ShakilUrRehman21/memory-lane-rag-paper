"""
Deterministic mock of an OpenAI-compatible API (/v1/chat/completions, /v1/embeddings).

FOR PLUMBING TESTS ONLY. Responses are produced by simple rules, not by a language model, so
any accuracy numbers obtained against this server are meaningless. It exists so that the LLM
evaluation scripts can be exercised end-to-end without an API key.

Run: uvicorn scripts.dev.mock_openai_server:app --port 8765
     export OPENAI_BASE_URL=http://127.0.0.1:8765/v1 OPENAI_API_KEY=mock
"""
import hashlib
import json
import re

import numpy as np
from fastapi import FastAPI, Request

app = FastAPI()
NEG = ["dead end", "not interested", "waste of time", "avoid", "regret", "hassle", "don't", "not ", "skeptical",
       "in my way", "rather not", "overhyped", "distance"]
POS = ["excited", "love", "appreciate", "best", "passionate", "fascinated", "prefer", "recommend", "big part",
       "better decisions", "reach for first", "committed", "started learning"]


def words(s):
    return set(w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2)


def vec(text, dim):
    v = np.zeros(dim)
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % dim] += 1
    n = np.linalg.norm(v)
    return (v / n if n else v).tolist()


def respond(system, user):
    if "Label each numbered statement" in user:
        items = []
        for m in re.finditer(r"^(\d+)\. (.+)$", user, re.M):
            s = m.group(2).lower()
            pol = -0.8 if any(n in s for n in NEG) else (0.8 if any(p in s for p in POS) else 0.0)
            ents = re.findall(r"\b[A-Z][a-zA-Z+#]+\b", m.group(2))[1:]
            items.append({"i": int(m.group(1)), "memory_type": "belief" if pol else "event", "stance_polarity": pol,
                          "entities": ents, "topics": [e.lower() for e in ents][:2]})
        return {"items": items}
    if "EVIDENCE (id" in user:
        ev = re.findall(r"^- (\S+) \| (\S+) \| \S* \| (.+?) \|", user, re.M)
        claims = [{"claim_id": f"c{i}", "claim_text": f"On {d}, you wrote: {s}", "claim_type": "explicit",
                   "confidence": 0.9, "evidence_tmu_ids": [tid]} for i, (tid, d, s) in enumerate(ev[:3])]
        claims.append({"claim_id": "cx", "claim_text": "You also founded a company.", "evidence_tmu_ids": ["bogus_id"]})
        return {"answer": " ".join(c["claim_text"] for c in claims) + " Your stance appears to have changed.",
                "claims": claims, "uncertainty_notes": []}
    if user.startswith("MEMORIES:"):
        q = re.search(r"QUESTION: (.+)", user).group(1)
        mem = re.findall(r"^\[[^\]]*\] (.+)$", user, re.M)
        if not mem:
            return "I don't know."
        best = max(mem, key=lambda m: len(words(m) & words(q)))
        return best.split(": ", 1)[-1][:120]
    if "Label the generated answer" in user or "Gold answer / rubric" in user:
        gold = re.search(r"Gold answer(?: / rubric)?: (.+)", user).group(1)
        gen = re.search(r"(?:Generated answer|Model response): (.+)", user).group(1)
        ok = bool(words(gold) & words(gen))
        lab = ("CORRECT" if ok else "WRONG") if "Label the generated" in user else ("yes" if ok else "no")
        return {"reasoning": "token overlap rule", "label": lab}
    if "Is the claim fully supported" in user:
        claim = re.search(r"CLAIM: (.+)", user).group(1)
        ev = user.split("CLAIM:")[0]
        return {"label": "supported" if len(words(claim) & words(ev)) >= 0.5 * max(1, len(words(claim))) else "unsupported"}
    if "Does this answer state" in user:
        return {"label": "yes" if re.search(r"chang|revers", user.split("Does this")[0], re.I) else "no"}
    if "Memory Extractor" in system:  # mem0 >= 2.x single-call additive extraction
        sec = user.split("## New Messages", 1)[-1].split("##", 1)[0]
        lines = [l.split(": ", 1)[-1].strip() for l in sec.strip().splitlines() if l.strip()]
        return {"memory": [{"text": l} for l in lines[:10]]}
    low = (system + user).lower()
    if "fact" in low and ("extract" in low or "retrieve" in low):  # mem0 fact extraction
        lines = [l.split(": ", 1)[-1] for l in re.findall(r"user: (.+)", user)] or [user[-200:]]
        return {"facts": lines[:5]}
    if '"event"' in low or "add" in low and "update" in low and "delete" in low:  # mem0 memory update
        facts = re.findall(r'"([^"]{15,})"', user)
        return {"memory": [{"id": str(i), "text": f, "event": "ADD"} for i, f in enumerate(facts[:5])]}
    return {"answer": "ok"}


@app.post("/v1/chat/completions")
async def chat(req: Request):
    body = await req.json()
    msgs = body.get("messages", [])
    system = " ".join(m.get("content", "") for m in msgs if m.get("role") == "system")
    user = "\n".join(m.get("content", "") for m in msgs if m.get("role") != "system")
    out = respond(system, user)
    content = out if isinstance(out, str) else json.dumps(out)
    return {"id": "mock", "object": "chat.completion", "model": body.get("model", "mock"),
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": len(user) // 4, "completion_tokens": len(content) // 4,
                      "total_tokens": (len(user) + len(content)) // 4}}


@app.post("/v1/embeddings")
async def embeddings(req: Request):
    body = await req.json()
    inp = body["input"] if isinstance(body["input"], list) else [body["input"]]
    dim = int(body.get("dimensions") or 64)
    return {"object": "list", "model": body.get("model", "mock"),
            "data": [{"object": "embedding", "index": i, "embedding": vec(str(t), dim)} for i, t in enumerate(inp)],
            "usage": {"prompt_tokens": 0, "total_tokens": 0}}
