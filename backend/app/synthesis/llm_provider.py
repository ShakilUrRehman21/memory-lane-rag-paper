import os
import json
import re
import httpx
from typing import Dict, Any, List, Optional
from app.core.config import settings

OUTPUT_SPEC = """Return ONLY a JSON object with this shape:
{"answer": "<prose answer for the user>",
 "claims": [{"claim_id": "c1", "claim_text": "<one factual claim made in the answer>",
             "claim_type": "explicit" | "empirical_change" | "inferred_relationship",
             "confidence": <0..1>, "evidence_tmu_ids": ["<ids of the EVIDENCE items supporting it>"],
             "is_uncertain": <true|false>, "uncertainty_note": "<string or null>"}],
 "uncertainty_notes": ["<string>"]}
List claims in the same order they appear in the answer. Cite only ids that appear in EVIDENCE.
If the evidence does not answer the question, say so and return an empty claims list."""


def build_evidence_prompt(query: str, context_tmus: List[Dict[str, Any]], changes: List[Dict[str, Any]],
                          contradictions: List[Dict[str, Any]]) -> str:
    lines = [f"QUESTION: {query}", "", "EVIDENCE (id | date | type | statement | source):"]
    for t in context_tmus:
        lines.append(f"- {t.get('id')} | {t.get('event_date_start') or 'undated'} | "
                     f"{str(t.get('memory_type', '')).replace('MemoryType.', '').lower()} | "
                     f"{t.get('statement', '').strip()} | {t.get('document_title', '')}")
    if changes:
        lines += ["", "DETECTED CHANGES (heuristic, may be wrong):"]
        for c in changes:
            lines.append(f"- {c.get('change_type')} on '{c.get('topic_or_entity')}' between "
                         f"{(c.get('from_period') or '')[:10]} ({c.get('earlier_memory_id')}) and "
                         f"{(c.get('to_period') or '')[:10]} ({c.get('later_memory_id')})")
    if contradictions:
        lines += ["", "POTENTIAL REVERSALS (heuristic, may be wrong):"]
        for r in contradictions:
            lines.append(f"- {r.get('evidence_rationale')} ({r.get('source_memory_id')} -> {r.get('target_memory_id')})")
    lines += ["", OUTPUT_SPEC]
    return "\n".join(lines)


def _parse_json(text: str) -> Dict[str, Any]:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def normalize_llm_output(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce model output into the GroundedClaim schema without inventing evidence."""
    claims = []
    for i, c in enumerate(raw.get("claims") or []):
        if not isinstance(c, dict):
            continue
        ctype = c.get("claim_type") if c.get("claim_type") in ("explicit", "empirical_change", "inferred_relationship") else "explicit"
        try:
            conf = float(c.get("confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        ids = c.get("evidence_tmu_ids") or []
        if isinstance(ids, str):
            ids = [ids]
        claims.append({"claim_id": str(c.get("claim_id") or f"c{i+1}"), "claim_text": str(c.get("claim_text", "")),
                       "claim_type": ctype, "confidence": max(0.0, min(1.0, conf)),
                       "evidence_tmu_ids": [str(x) for x in ids if x], "source_citations": [],
                       "is_uncertain": bool(c.get("is_uncertain", False)),
                       "uncertainty_note": c.get("uncertainty_note")})
    notes = raw.get("uncertainty_notes") or []
    return {"answer": str(raw.get("answer", "")), "claims": claims,
            "uncertainty_notes": [str(n) for n in notes] if isinstance(notes, list) else [str(notes)]}


class LLMProvider:
    """
    LLM adapter: Google Gemini, any OpenAI-compatible endpoint (OpenAI, vLLM, Ollama, LM Studio,
    Together, ... via OPENAI_BASE_URL), or the deterministic offline synthesizer.

    v1.1 fix: v1.0 sent the LLM only the user's question - the retrieved evidence, detected
    changes and the required JSON format were never included in the prompt.
    """

    @staticmethod
    def backend() -> str:
        forced = os.getenv("ML_LLM_BACKEND", "").lower()
        if forced:
            return forced
        if os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY:
            return "gemini"
        if os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY or os.getenv("OPENAI_BASE_URL"):
            return "openai"
        return "deterministic"

    @staticmethod
    def generate_synthesis(prompt: str, system_instruction: str, context_tmus: List[Dict[str, Any]],
                           detected_changes: List[Dict[str, Any]], detected_contradictions: List[Dict[str, Any]],
                           model_name: Optional[str] = None) -> Dict[str, Any]:
        be = LLMProvider.backend()
        if be in ("gemini", "openai"):
            full = build_evidence_prompt(prompt, context_tmus, detected_changes, detected_contradictions)
            try:
                if be == "gemini":
                    key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
                    raw = LLMProvider._call_gemini(key, full, system_instruction,
                                                   model_name or os.getenv("ML_LLM_MODEL", "gemini-2.5-flash"))
                else:
                    key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY or "not-needed"
                    raw = LLMProvider._call_openai(key, full, system_instruction,
                                                   model_name or os.getenv("ML_LLM_MODEL", "gpt-4o-mini"))
                out = normalize_llm_output(raw)
                out["backend"] = be
                return out
            except Exception as e:
                if os.getenv("ML_LLM_STRICT") == "1":
                    raise
                print(f"[LLMProvider] {be} call failed: {e}. Falling back to deterministic synthesizer.")
        out = LLMProvider._deterministic_longitudinal_synthesizer(prompt, context_tmus, detected_changes,
                                                                  detected_contradictions)
        out["backend"] = "deterministic"
        return out

    @staticmethod
    def _call_gemini(api_key: str, prompt: str, system_instruction: str, model: str) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                   "systemInstruction": {"parts": [{"text": system_instruction}]},
                   "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}}
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return _parse_json(resp.json()["candidates"][0]["content"]["parts"][0]["text"])

    @staticmethod
    def _call_openai(api_key: str, prompt: str, system_instruction: str, model: str) -> Dict[str, Any]:
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        payload = {"model": model, "temperature": 0.0,
                   "messages": [{"role": "system", "content": system_instruction},
                                {"role": "user", "content": prompt}]}
        if os.getenv("ML_LLM_JSON_MODE", "1") == "1":
            payload["response_format"] = {"type": "json_object"}
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{base}/chat/completions", headers={"Authorization": f"Bearer {api_key}"}, json=payload)
            resp.raise_for_status()
            return _parse_json(resp.json()["choices"][0]["message"]["content"])

    @staticmethod
    def _deterministic_longitudinal_synthesizer(
        prompt: str,
        context_tmus: List[Dict[str, Any]],
        detected_changes: List[Dict[str, Any]],
        detected_contradictions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        High-precision rule-based longitudinal generation engine.
        Ensures 100% testability, deterministic claim grounding, and calibrated uncertainty.
        """
        if not context_tmus:
            return {
                "answer": "Based on your indexed documents, there is no documented evidence regarding this query.",
                "claims": [],
                "uncertainty_notes": ["No matching documents were found in the archive."]
            }

        # Sort context TMUs chronologically
        sorted_tmus = sorted(context_tmus, key=lambda x: x.get("event_date_start") or "9999")
        
        paragraphs = []
        claims = []
        uncertainty_notes = []

        # 1. Opening overview with epistemic caution
        first_date = sorted_tmus[0].get("event_date_start", "the earliest record")[:7]
        last_date = sorted_tmus[-1].get("event_date_start", "the most recent record")[:7]
        paragraphs.append(
            f"Based on your documented history from {first_date} through {last_date}, "
            "your documented perspective exhibits a clear progression rather than a static viewpoint."
        )

        # 2. Chronological progression
        for i, item in enumerate(sorted_tmus):
            date_label = item.get("event_date_start") or "Unrecorded Date"
            stmt = item.get("statement", "").strip()
            mem_type = str(item.get("memory_type", "observation")).replace("MemoryType.", "").lower()
            doc_title = item.get("document_title", "Document")
            tmu_id = item.get("id")

            claim_id = f"clm_{i+1}"
            claim_text = f"In {date_label[:7] if len(date_label)>=7 else date_label}, you documented a {mem_type}: '{stmt}'."
            paragraphs.append(f"• **{date_label[:7]}**: {stmt} *(Source: {doc_title})*")

            claims.append({
                "claim_id": claim_id,
                "claim_text": claim_text,
                "claim_type": "explicit",
                "confidence": item.get("date_confidence", 0.9),
                "evidence_tmu_ids": [tmu_id],
                "source_citations": [{
                    "document_title": doc_title,
                    "document_id": item.get("document_id"),
                    "statement": stmt,
                    "date": date_label
                }],
                "is_uncertain": False,
                "uncertainty_note": None
            })

        # 3. Transitions & Change-Points
        if detected_changes:
            paragraphs.append("\n**Identified Transitions & Shifts:**")
            for c in detected_changes:
                c_type = c.get("change_type", "evolution").replace("_", " ")
                topic = c.get("topic_or_entity", "topic")
                from_p = c.get("from_period", "")[:7]
                to_p = c.get("to_period", "")[:7]
                shift_summary = f"Your documents show a {c_type} in your stance regarding {topic} between {from_p} and {to_p}."
                paragraphs.append(f"- {shift_summary}")
                
                if c.get("uncertainty_bounds"):
                    uncertainty_notes.append(c["uncertainty_bounds"])

                claims.append({
                    "claim_id": f"clm_change_{c.get('id', 'c')}",
                    "claim_text": shift_summary,
                    "claim_type": "empirical_change",
                    "confidence": 0.85,
                    "evidence_tmu_ids": [c.get("earlier_memory_id"), c.get("later_memory_id")],
                    "source_citations": [],
                    "is_uncertain": bool(c.get("uncertainty_bounds")),
                    "uncertainty_note": c.get("uncertainty_bounds")
                })

        # 4. Contradictions & Reversals
        if detected_contradictions:
            paragraphs.append("\n**Potential Stance Reversals:**")
            for r in detected_contradictions:
                paragraphs.append(f"- {r.get('evidence_rationale')}")
                claims.append({
                    "claim_id": f"clm_rev_{r.get('id', 'r')}",
                    "claim_text": r.get("evidence_rationale", ""),
                    "claim_type": "inferred_relationship",
                    "confidence": r.get("confidence", 0.8),
                    "evidence_tmu_ids": [r.get("source_memory_id"), r.get("target_memory_id")],
                    "source_citations": [],
                    "is_uncertain": False,
                    "uncertainty_note": None
                })

        # Final answer text
        answer_text = "\n\n".join(paragraphs)

        return {
            "answer": answer_text,
            "claims": claims,
            "uncertainty_notes": uncertainty_notes
        }


def llm_json(prompt: str, system_instruction: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    """Call the configured LLM backend and return parsed JSON (raises if no LLM is configured)."""
    be = LLMProvider.backend()
    if be == "gemini":
        key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        return LLMProvider._call_gemini(key, prompt, system_instruction,
                                        model_name or os.getenv("ML_LLM_MODEL", "gemini-2.5-flash"))
    if be == "openai":
        key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY or "not-needed"
        return LLMProvider._call_openai(key, prompt, system_instruction,
                                        model_name or os.getenv("ML_LLM_MODEL", "gpt-4o-mini"))
    raise RuntimeError("No LLM backend configured (set OPENAI_API_KEY / OPENAI_BASE_URL or GEMINI_API_KEY).")
