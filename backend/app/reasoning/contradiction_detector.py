from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Sequence

from app.core.config import settings
from app.models.schemas import MemoryRelationshipResponse, RelationType, TMUResponse
from app.storage.repository import Repository


def _direction(p: float) -> str:
    return "positive" if p > 0 else "negative"


class ContradictionDetector:
    """
    Finds potential stance reversals: two memories, ordered in time, that share a subject and
    carry opposite stance polarity.

    v1.1 changes: the rationale states the actual direction (v1.0 always printed
    "negative ... became positive"); the subject named in the query counts as a shared subject,
    so topics outside the entity list can be compared; read-only during queries by default.
    """

    @staticmethod
    def detect_contradictions(user_id: str = "default_user", tmus: Optional[Sequence[TMUResponse]] = None,
                              focus_terms: Optional[Sequence[str]] = None,
                              persist: Optional[bool] = None) -> List[MemoryRelationshipResponse]:
        whole_archive = tmus is None
        if persist is None:
            persist = whole_archive or settings.PERSIST_ANALYSIS_ON_QUERY
        if tmus is None:
            tmus = Repository.list_tmus(user_id=user_id)
        focus = [f.lower() for f in (focus_terms or [])]
        ordered = sorted(tmus, key=lambda x: x.event_date_start or "9999")
        out: List[MemoryRelationshipResponse] = []
        seen = set()
        for i, m1 in enumerate(ordered):
            if abs(m1.stance_polarity) < 0.3:
                continue
            for m2 in ordered[i + 1:]:
                if abs(m2.stance_polarity) < 0.3 or m1.stance_polarity * m2.stance_polarity >= 0:
                    continue
                shared = sorted(set(m1.entities) & set(m2.entities)) or sorted(set(m1.topics) & set(m2.topics))
                if not shared:
                    shared = [f for f in focus if f in m1.statement.lower() and f in m2.statement.lower()]
                if not shared:
                    continue
                gap = abs(m2.stance_polarity - m1.stance_polarity)
                if gap < 0.8 or (m1.id, m2.id) in seen:
                    continue
                seen.add((m1.id, m2.id))
                subject = shared[0]
                rationale = (f"Detected potential stance reversal regarding '{subject}'. "
                             f"In {m1.event_date_start or 'an earlier document'}, polarity was "
                             f"{_direction(m1.stance_polarity)} ({m1.stance_polarity:.2f}). "
                             f"In {m2.event_date_start or 'a later document'}, polarity became "
                             f"{_direction(m2.stance_polarity)} ({m2.stance_polarity:.2f}).")
                rel = MemoryRelationshipResponse(
                    id=f"rev_{m1.id}_{m2.id}", source_memory_id=m1.id, target_memory_id=m2.id,
                    relation_type=RelationType.CONTRADICTS, confidence=round(min(1.0, 0.6 + gap * 0.2), 2),
                    evidence_rationale=rationale, source_statement=m1.statement, target_statement=m2.statement,
                    source_date=m1.event_date_start, target_date=m2.event_date_start,
                    created_at=datetime.now(timezone.utc).isoformat())
                out.append(rel)
                if persist:
                    Repository.insert_relationship({
                        "id": rel.id, "source_memory_id": rel.source_memory_id,
                        "target_memory_id": rel.target_memory_id, "relation_type": rel.relation_type.value,
                        "confidence": rel.confidence, "evidence_rationale": rel.evidence_rationale})
        return out
