from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

import numpy as np

from app.core.config import settings
from app.models.schemas import ChangePointResponse, MemoryType, TMUResponse
from app.storage.repository import Repository
from app.storage.vector_store import tmu_vector_store

STANCE_TYPES = {MemoryType.BELIEF, MemoryType.GOAL, MemoryType.DECISION, MemoryType.PREFERENCE}


def _mentions(t: TMUResponse, target: str) -> bool:
    tl = target.lower()
    return (tl in t.statement.lower() or tl in [e.lower() for e in t.entities]
            or tl in [x.lower() for x in t.topics])


def _is_stance_bearing(t: TMUResponse) -> bool:
    return abs(t.stance_polarity) > 0 or t.memory_type in STANCE_TYPES


class ChangePointDetector:
    """
    Detects stance reversals and semantic shifts between *consecutive stance-bearing* memories
    about the same topic.

    v1.1 changes:
    * Only stance-bearing memories (non-zero polarity or belief/goal/decision/preference) are
      compared; v1.0 also compared neutral mentions, producing ~6 false changes per true one.
    * Query-focused: when the query names a subject (QueryRouter.topic_terms), that subject is
      tracked directly, so topics absent from the extractor's entity list are still analysed.
    * Read-only during queries unless settings.PERSIST_ANALYSIS_ON_QUERY is set.
    """

    @staticmethod
    def detect_changes_for_topic_or_entity(topic_or_entity: str, tmus: Sequence[TMUResponse],
                                           user_id: str = "default_user", persist: bool = False,
                                           stance_only: bool = True) -> List[ChangePointResponse]:
        relevant = [t for t in tmus if _mentions(t, topic_or_entity)]
        if stance_only:
            relevant = [t for t in relevant if _is_stance_bearing(t)]
        relevant.sort(key=lambda x: x.event_date_start or "9999")
        if len(relevant) < 2:
            return []
        embs = tmu_vector_store.embedder.embed([t.statement for t in relevant])
        out: List[ChangePointResponse] = []
        for i in range(len(relevant) - 1):
            m1, m2 = relevant[i], relevant[i + 1]
            drift = max(0.0, 1.0 - float(np.dot(embs[i], embs[i + 1])))
            pdelta = abs(m2.stance_polarity - m1.stance_polarity)
            flip = m1.stance_polarity * m2.stance_polarity < 0
            is_rev = flip and pdelta >= settings.POLARITY_INVERSION_THRESHOLD
            is_shift = drift >= settings.SEMANTIC_DRIFT_THRESHOLD
            if not (is_rev or is_shift):
                continue
            ctype = "reversal" if is_rev else ("sudden_shift" if drift > 0.65 else "gradual_evolution")
            p1, p2 = m1.event_date_start or "Unknown", m2.event_date_start or "Unknown"
            note = None
            try:
                days = abs((datetime.fromisoformat(p2[:10]) - datetime.fromisoformat(p1[:10])).days)
                if days > settings.SPARSE_EVIDENCE_DAYS:
                    note = (f"Transition occurred between {p1[:7]} and {p2[:7]} ({days} days). "
                            "Exact turning point is unrecorded in the available documents.")
            except ValueError:
                pass
            cp = ChangePointResponse(
                id=f"cp_{m1.id}_{m2.id}", user_id=user_id, topic_or_entity=topic_or_entity,
                from_period=p1, to_period=p2, change_type=ctype, magnitude=round(drift, 3),
                earlier_memory_id=m1.id, later_memory_id=m2.id, earlier_statement=m1.statement,
                later_statement=m2.statement, earlier_date=m1.event_date_start, later_date=m2.event_date_start,
                uncertainty_bounds=note, created_at=datetime.now(timezone.utc).isoformat())
            out.append(cp)
            if persist:
                Repository.insert_change_point(cp.model_dump())
        return out

    @staticmethod
    def detect_all_changes(user_id: str = "default_user", tmus: Optional[Sequence[TMUResponse]] = None,
                           focus_terms: Optional[Sequence[str]] = None,
                           persist: Optional[bool] = None) -> List[ChangePointResponse]:
        whole_archive = tmus is None
        if persist is None:
            persist = whole_archive or settings.PERSIST_ANALYSIS_ON_QUERY
        if tmus is None:
            tmus = Repository.list_tmus(user_id=user_id)

        targets: List[str] = []
        if focus_terms and settings.QUERY_FOCUSED_CHANGES:
            targets = [ft for ft in focus_terms if sum(_mentions(t, ft) for t in tmus) >= 2]
        if not targets:
            seen: Dict[str, None] = {}
            for t in tmus:
                for x in list(t.entities) + list(t.topics):
                    seen.setdefault(x, None)
            targets = list(seen)

        changes: List[ChangePointResponse] = []
        pairs = set()
        for target in targets:
            for c in ChangePointDetector.detect_changes_for_topic_or_entity(target, tmus, user_id, persist):
                key = (c.earlier_memory_id, c.later_memory_id)
                if key not in pairs:
                    pairs.add(key); changes.append(c)
        return changes
