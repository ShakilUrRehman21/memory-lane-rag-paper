import time
from typing import List

from app.models.schemas import (ChangePointResponse, GroundedClaim, MemoryRelationshipResponse, QueryRequest,
                                QueryResponse, TimelinePoint, TMUResponse)
from app.reasoning.change_detector import ChangePointDetector
from app.reasoning.contradiction_detector import ContradictionDetector
from app.retrieval.hybrid_retriever import hybrid_retriever
from app.synthesis.llm_provider import LLMProvider

SYSTEM_PROMPT = """You are Memory Lane RAG, an epistemic longitudinal assistant.
Your goal is to explain how a user's thinking, beliefs, goals, decisions, and knowledge evolved over time based strictly on their documented history.

Guiding Principles:
1. Epistemic Honesty: State only what the EVIDENCE explicitly shows or supports. Never extrapolate internal psychology.
2. Quad-Dates: Accurately distinguish event dates from document authoring dates.
3. Uncertainty Bounds: When evidence is separated by significant time gaps, explicitly note that intermediate transitions are unrecorded.
4. Grounded Citations: Every claim must cite the ids of the EVIDENCE items that support it.
5. Neutral Objectivity: Frame stance inversions as "potential revisions or reversals" rather than personal accusations.
"""

PIPELINES = {"baseline", "temporal", "memory_lane"}


class GroundedSynthesizer:
    """
    Retrieval -> (optional) change & reversal analysis -> grounded synthesis.

    baseline    : dense top-k, no temporal processing, no change analysis.
    temporal    : dense top-k + query date filter + chronological ordering, no change analysis
                  (implemented in v1.1; v1.0 silently ran the full Memory Lane pipeline here).
    memory_lane : hybrid retrieval + stratification + change & reversal analysis.
    """

    @staticmethod
    def synthesize(request: QueryRequest) -> QueryResponse:
        t0 = time.perf_counter()
        mode = request.pipeline_mode if request.pipeline_mode in PIPELINES else "memory_lane"

        if mode == "baseline":
            pack = hybrid_retriever.retrieve(request.query, request.user_id, request.top_k, disable_temporal=True,
                                             disable_rerank=True, dense_only=True)
        elif mode == "temporal":
            pack = hybrid_retriever.retrieve(request.query, request.user_id, request.top_k, disable_temporal=False,
                                             disable_rerank=True, dense_only=True, stratification_mode="off",
                                             filter_start_year=request.filter_start_year,
                                             filter_end_year=request.filter_end_year)
        else:
            pack = hybrid_retriever.retrieve(
                request.query, request.user_id, request.top_k,
                disable_temporal=request.ablation_disable_temporal, disable_rerank=request.ablation_disable_rerank,
                filter_start_year=request.filter_start_year, filter_end_year=request.filter_end_year,
                stratification_mode=request.stratification_mode)

        retrieved: List[TMUResponse] = pack["results"]
        analysis = pack["analysis"]
        do_changes = mode == "memory_lane" and not request.ablation_disable_change_detection

        timeline = [TimelinePoint(
            period=(t.event_date_start or t.created_at or "Unrecorded")[:7],
            date_display=(t.event_date_start or t.created_at or "Unrecorded")[:10],
            event_date=t.event_date_start or t.created_at or "Unrecorded",
            headline=t.statement[:60] + ("..." if len(t.statement) > 60 else ""),
            statement=t.statement, memory_type=t.memory_type, document_title=t.document_title or "Document",
            document_id=t.document_id, tmu_id=t.id, confidence=t.date_confidence, stance_polarity=t.stance_polarity)
            for t in sorted(retrieved, key=lambda x: x.event_date_start or "9999")]

        changes: List[ChangePointResponse] = []
        contras: List[MemoryRelationshipResponse] = []
        if do_changes and retrieved:
            focus = analysis.get("topic_terms") or []
            changes = ChangePointDetector.detect_all_changes(user_id=request.user_id, tmus=retrieved, focus_terms=focus)
            contras = ContradictionDetector.detect_contradictions(user_id=request.user_id, tmus=retrieved,
                                                                  focus_terms=focus)

        out = LLMProvider.generate_synthesis(
            prompt=request.query, system_instruction=SYSTEM_PROMPT,
            context_tmus=[t.model_dump() for t in retrieved], detected_changes=[c.model_dump() for c in changes],
            detected_contradictions=[r.model_dump() for r in contras])

        # Provenance check: evidence ids must refer to memories that were actually retrieved.
        valid_ids = {t.id for t in retrieved}
        claims = []
        for c in out.get("claims", []):
            c = dict(c)
            c["evidence_tmu_ids"] = [i for i in (c.get("evidence_tmu_ids") or []) if i in valid_ids]
            claims.append(GroundedClaim(**c))
        notes = list(out.get("uncertainty_notes", []))
        if len(timeline) >= 2:
            years = sorted(int(p.event_date[:4]) for p in timeline if p.event_date[:4].isdigit())
            if years and years[-1] - years[0] >= 3 and len(timeline) <= 3:
                msg = (f"Available evidence spans {years[0]} to {years[-1]} with few documented interim records. "
                       "Trajectory between documented milestones is estimated.")
                if msg not in notes:
                    notes.append(msg)

        return QueryResponse(
            query=request.query, detected_intent=analysis["intent"], pipeline_used=mode,
            answer=out.get("answer", "No answer could be generated."), timeline=timeline,
            detected_changes=changes, potential_contradictions=contras, grounded_claims=claims,
            uncertainty_notes=notes, retrieved_tmus=retrieved,
            execution_time_ms=round((time.perf_counter() - t0) * 1000, 2),
            model_calls=0 if out.get("backend") == "deterministic" else 1,
            ranked_tmu_ids=[t.id for t in pack["ranked_results"]], stratified=pack["stratified"],
            synthesis_backend=out.get("backend", "deterministic"))


grounded_synthesizer = GroundedSynthesizer()
