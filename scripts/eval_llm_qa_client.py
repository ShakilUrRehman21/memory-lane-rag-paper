"""OpenAI-compatible chat client shared by the LLM evaluation scripts (reader + judge)."""
import json
import os
import random
import re
import threading
import time

import httpx


class Chat:
    def __init__(self, base, key, model):
        self.base, self.key, self.model = base.rstrip("/"), key or "not-needed", model
        self.json_mode = os.getenv("ML_LLM_JSON_MODE", "1") == "1"
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self._lock = threading.Lock()

    def __call__(self, system, user, json_out=False, max_tokens=400):
        payload = {"model": self.model, "temperature": 0.0, "max_tokens": max_tokens,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_out and self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        for attempt in range(6):
            try:
                with httpx.Client(timeout=180.0) as c:
                    r = c.post(f"{self.base}/chat/completions", json=payload,
                               headers={"Authorization": f"Bearer {self.key}"})
                if r.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError("retryable", request=r.request, response=r)
                r.raise_for_status()
                d = r.json()
                with self._lock:
                    self.calls += 1
                    u = d.get("usage") or {}
                    self.prompt_tokens += u.get("prompt_tokens", 0)
                    self.completion_tokens += u.get("completion_tokens", 0)
                return d["choices"][0]["message"]["content"] or ""
            except (httpx.HTTPError, KeyError) as e:
                if attempt == 5:
                    raise
                time.sleep(min(60, 2 ** attempt + random.random()))


reader = Chat(os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), os.getenv("OPENAI_API_KEY", ""),
              os.getenv("ML_READER_MODEL", "gpt-4o-mini"))
judge = Chat(os.getenv("ML_JUDGE_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")),
             os.getenv("ML_JUDGE_API_KEY", os.getenv("OPENAI_API_KEY", "")), os.getenv("ML_JUDGE_MODEL", "gpt-4o-mini"))


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else {}


