from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.schemas import TMUResponse, RelationType, MemoryRelationshipResponse
from app.storage.repository import Repository
from app.reasoning.contradiction_detector import ContradictionDetector

class MemoryGraphBuilder:
    """
    Constructs a temporal knowledge graph connecting memories through
    causal, temporal, and semantic edges (evolves_from, contradicts, supports, follows).
    """

    @staticmethod
    def build_graph(user_id: str = "default_user") -> Dict[str, Any]:
        tmus = Repository.list_tmus(user_id=user_id)
        if not tmus:
            return {"nodes": [], "edges": []}

        # 1. Run contradiction detector to capture contradiction edges
        ContradictionDetector.detect_contradictions(user_id=user_id, tmus=tmus)

        # 2. Add sequential and evolution edges
        tmus_sorted = sorted(tmus, key=lambda x: x.event_date_start or "9999")
        for i in range(len(tmus_sorted) - 1):
            m1 = tmus_sorted[i]
            for j in range(i + 1, min(i + 4, len(tmus_sorted))):
                m2 = tmus_sorted[j]

                # Same document sequential link
                if m1.document_id == m2.document_id and m1.chunk_id == m2.chunk_id:
                    Repository.insert_relationship({
                        "id": f"seq_{m1.id}_{m2.id}",
                        "source_memory_id": m1.id,
                        "target_memory_id": m2.id,
                        "relation_type": RelationType.FOLLOWS.value,
                        "confidence": 0.95,
                        "evidence_rationale": "Sequential thought in same passage"
                    })

                # Cross-temporal evolution link
                common_entities = set(m1.entities).intersection(set(m2.entities))
                if common_entities and (m1.event_date_start or "") != (m2.event_date_start or ""):
                    # Check if progressive
                    if m2.stance_polarity >= m1.stance_polarity >= 0:
                        rel_type = RelationType.EVOLVES_FROM.value
                    elif m1.stance_polarity > 0 and m2.stance_polarity > 0:
                        rel_type = RelationType.SUPPORTS.value
                    else:
                        continue

                    Repository.insert_relationship({
                        "id": f"evo_{m1.id}_{m2.id}",
                        "source_memory_id": m1.id,
                        "target_memory_id": m2.id,
                        "relation_type": rel_type,
                        "confidence": 0.80,
                        "evidence_rationale": f"Shared entity trajectory: {', '.join(common_entities)}"
                    })

        # 3. Assemble nodes and edges for visual rendering
        raw_edges = Repository.list_relationships()

        nodes = [
            {
                "id": t.id,
                "label": t.statement[:45] + ("..." if len(t.statement) > 45 else ""),
                "full_text": t.statement,
                "type": t.memory_type.value,
                "date": t.event_date_start or "Unrecorded",
                "document_title": t.document_title,
                "entities": t.entities,
                "topics": t.topics,
                "polarity": t.stance_polarity
            }
            for t in tmus
        ]

        edges = [
            {
                "id": e.id,
                "source": e.source_memory_id,
                "target": e.target_memory_id,
                "type": e.relation_type.value,
                "confidence": e.confidence,
                "rationale": e.evidence_rationale
            }
            for e in raw_edges
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "summary": f"Graph rendered with {len(nodes)} memory nodes and {len(edges)} longitudinal relations."
        }
