import os
import re
from typing import List, Dict, Any, Optional
from app.models.schemas import MemoryType, TMUCreate
from app.ingestion.date_extractor import DateExtractor

# Known entities and topics taxonomy for high-precision extraction
KNOWN_TECH_ENTITIES = [
    "Python", "Java", "C++", "Rust", "JavaScript", "TypeScript", "Go", "Golang",
    "Machine Learning", "Artificial Intelligence", "AI", "Deep Learning",
    "PyTorch", "TensorFlow", "Transformers", "LLMs", "RAG", "Retrieval-Augmented Generation",
    "NLP", "Computer Vision", "Docker", "Kubernetes", "PostgreSQL", "React",
    "Next.js", "FastAPI", "Distributed Systems", "Cloud Computing", "AWS", "GCP"
]

KNOWN_CAREER_GOALS = [
    "AI Engineer", "Software Engineer", "Research Scientist", "AI Researcher",
    "Data Scientist", "PhD", "Graduate School", "Engineering Lead", "Tech Lead"
]

TOPIC_KEYWORDS = {
    "Artificial Intelligence": ["ai", "machine learning", "deep learning", "neural", "llm", "transformer", "nlp"],
    "Software Engineering": ["software", "engineering", "backend", "frontend", "architecture", "coding", "developer"],
    "Research & Academia": ["research", "paper", "publish", "conference", "phd", "academic", "experiment", "thesis"],
    "Career & Goals": ["career", "goal", "direction", "role", "promotion", "job", "future", "work as", "aim"],
    "Programming Languages": ["python", "java", "c++", "rust", "javascript", "typescript", "golang"],
    "Infrastructure & Systems": ["distributed", "kubernetes", "docker", "cloud", "database", "infrastructure", "scale"]
}

class TMUExtractor:
    """
    Extracts structured Temporal Memory Units (TMU) from chunks,
    resolving memory type, quad-dates, stance polarity, entities, and topics.
    """

    @staticmethod
    def extract_from_chunk(
        chunk_content: str,
        chunk_id: str,
        document_id: str,
        document_date: Optional[str] = None,
        user_id: str = "default_user"
    ) -> List[TMUCreate]:
        """
        Extractor backends (env ML_EXTRACTOR):
          "rules" (default, offline): keyword/regex lexicons below. Stance polarity, memory type
                  and entities only generalise to wording and topics covered by the lexicons.
          "llm"  : an LLM labels each statement (type, polarity, entities, topics); falls back
                  to rules if the call fails. Required for paraphrased stance and open-vocabulary topics.
        """
        if os.getenv("ML_EXTRACTOR", "rules").lower() == "llm":
            try:
                return TMUExtractor._extract_llm(chunk_content, chunk_id, document_id, document_date, user_id)
            except Exception as e:  # pragma: no cover - network dependent
                print(f"[TMUExtractor] LLM extraction failed ({e}); using rule-based extraction.")
        return TMUExtractor._extract_rules(chunk_content, chunk_id, document_id, document_date, user_id)

    @staticmethod
    def _split_statements(chunk_content: str) -> List[str]:
        return [s.strip("- *•\t ").strip() for s in re.split(r"(?<=[.!?\n])\s+", chunk_content)
                if len(s.strip()) > 15]

    @staticmethod
    def _extract_llm(chunk_content, chunk_id, document_id, document_date, user_id) -> List[TMUCreate]:
        from app.synthesis.llm_provider import llm_json
        stmts = TMUExtractor._split_statements(chunk_content)
        if not stmts:
            return []
        numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(stmts))
        prompt = (
            "Label each numbered statement written by the author of a personal document.\n"
            f"Document date: {document_date or 'unknown'}\n\n{numbered}\n\n"
            'Return ONLY JSON: {"items": [{"i": <index>, "memory_type": one of '
            f"{[m.value for m in MemoryType]}, "
            '"stance_polarity": <number in [-1,1]: the author\'s attitude towards the main subject; '
            '-1 rejection/dislike/abandonment, 0 neutral or purely factual, +1 adoption/enthusiasm/commitment>, '
            '"entities": [<named tools, technologies, organisations, people, places>], '
            '"topics": [<1-3 short lowercase topic labels>]}]}')
        raw = llm_json(prompt, "You are a precise annotator. Output JSON only.")
        by_i = {int(it.get("i", -1)): it for it in raw.get("items", []) if isinstance(it, dict)}
        valid_types = {m.value for m in MemoryType}
        out = []
        for i, stmt in enumerate(stmts):
            it = by_i.get(i, {})
            mt = it.get("memory_type")
            mem_type = MemoryType(mt) if mt in valid_types else TMUExtractor._classify_memory_type(stmt)
            try:
                pol = max(-1.0, min(1.0, float(it.get("stance_polarity", 0.0))))
            except (TypeError, ValueError):
                pol = TMUExtractor._compute_stance_polarity(stmt)
            ents = [str(e) for e in (it.get("entities") or [])][:10]
            tops = [str(t).lower() for t in (it.get("topics") or [])][:5]
            d = DateExtractor.extract_event_date(stmt, document_date=document_date)
            out.append(TMUCreate(document_id=document_id, chunk_id=chunk_id, user_id=user_id, memory_type=mem_type,
                                 statement=stmt, event_date_start=d["start"], event_date_end=d["end"],
                                 date_granularity=d["granularity"], date_confidence=d["confidence"],
                                 date_source=d["source"], stance_polarity=round(pol, 3),
                                 entities=list(dict.fromkeys(ents)), topics=list(dict.fromkeys(tops))))
        return out

    @staticmethod
    def _extract_rules(chunk_content, chunk_id, document_id, document_date=None, user_id="default_user") -> List[TMUCreate]:
        # Split chunk into statements / propositions (by sentences or bullet items)
        raw_statements = [
            s.strip("- *•\t ").strip()
            for s in re.split(r"(?<=[.!?\n])\s+", chunk_content)
            if len(s.strip()) > 15
        ]

        tmus: List[TMUCreate] = []

        for stmt in raw_statements:
            # 1. Determine Memory Type
            mem_type = TMUExtractor._classify_memory_type(stmt)
            
            # 2. Extract Event Date (t_event) vs Document Date (t_doc)
            date_info = DateExtractor.extract_event_date(stmt, document_date=document_date)
            
            # 3. Compute Stance Polarity (-1.0 rejection to +1.0 adoption)
            polarity = TMUExtractor._compute_stance_polarity(stmt)
            
            # 4. Extract Entities
            entities = TMUExtractor._extract_entities(stmt)
            
            # 5. Extract Topics
            topics = TMUExtractor._extract_topics(stmt, entities)

            tmu = TMUCreate(
                document_id=document_id,
                chunk_id=chunk_id,
                user_id=user_id,
                memory_type=mem_type,
                statement=stmt,
                event_date_start=date_info["start"],
                event_date_end=date_info["end"],
                date_granularity=date_info["granularity"],
                date_confidence=date_info["confidence"],
                date_source=date_info["source"],
                stance_polarity=polarity,
                entities=entities,
                topics=topics
            )
            tmus.append(tmu)

        return tmus

    @staticmethod
    def _classify_memory_type(text: str) -> MemoryType:
        lower = text.lower()
        if any(w in lower for w in ["i want to", "my goal is", "aiming to", "aspire to", "hope to", "target is", "ambition"]):
            return MemoryType.GOAL
        if any(w in lower for w in ["decided to", "i chose to", "i will switch", "agreed to", "made a decision"]):
            return MemoryType.DECISION
        if any(w in lower for w in ["i believe", "i think", "in my opinion", "viewpoint", "convinced that", "i don't think", "skeptical"]):
            return MemoryType.BELIEF
        if any(w in lower for w in ["i prefer", "favorite", "enjoy working with", "dislike", "hate", "strongly favor"]):
            return MemoryType.PREFERENCE
        if any(w in lower for w in ["plan to", "will schedule", "roadmap", "upcoming step", "planning on"]):
            return MemoryType.PLAN
        if any(w in lower for w in ["reflecting on", "looking back", "realized that", "in hindsight", "lesson learned"]):
            return MemoryType.REFLECTION
        if any(w in lower for w in ["observed", "noticed that", "data shows", "metrics indicate"]):
            return MemoryType.OBSERVATION
        if any(w in lower for w in ["learned that", "understood how", "knowledge of", "studied how"]):
            return MemoryType.KNOWLEDGE
        return MemoryType.EVENT

    @staticmethod
    def _compute_stance_polarity(text: str) -> float:
        lower = text.lower()
        # Negative indicators (rejection, skepticism, abandonment)
        neg_patterns = [
            r"don't think", r"do not think", r"not relevant", r"waste of time",
            r"don't want", r"do not want", r"moving away from", r"stopped using",
            r"abandoned", r"dislike", r"skeptical about", r"not interested",
            r"no longer", r"avoiding", r"not something i want", r"unnecessary"
        ]
        # Positive indicators (enthusiasm, commitment, strong adoption)
        pos_patterns = [
            r"want to work as", r"want to build", r"started learning",
            r"my goal is", r"one of my strongest", r"love working with",
            r"fascinated by", r"focusing on", r"deepening my expertise",
            r"committed to", r"excited about", r"publish research",
            r"strongly prefer", r"specialize in", r"passionate about"
        ]

        neg_score = sum(1 for p in neg_patterns if re.search(p, lower))
        pos_score = sum(1 for p in pos_patterns if re.search(p, lower))

        if neg_score > pos_score:
            return max(-1.0, -0.5 - (0.25 * neg_score))
        elif pos_score > neg_score:
            return min(1.0, 0.5 + (0.25 * pos_score))
        return 0.0

    @staticmethod
    def _extract_entities(text: str) -> List[str]:
        entities = []
        for ent in KNOWN_TECH_ENTITIES + KNOWN_CAREER_GOALS:
            pattern = rf"\b{re.escape(ent)}\b"
            if re.search(pattern, text, re.IGNORECASE):
                # Canonical name
                entities.append(ent)
        return list(dict.fromkeys(entities))

    @staticmethod
    def _extract_topics(text: str, entities: List[str]) -> List[str]:
        lower = text.lower()
        topics = []
        for topic, kws in TOPIC_KEYWORDS.items():
            if any(re.search(rf"\b{re.escape(kw)}\b", lower) for kw in kws):
                topics.append(topic)
        # If any entities mapped, add their respective high-level topics
        if any(e in ["Python", "Java", "C++", "Rust", "JavaScript", "TypeScript"] for e in entities):
            topics.append("Programming Languages")
        if any(e in ["AI", "Machine Learning", "PyTorch", "LLMs", "RAG"] for e in entities):
            topics.append("Artificial Intelligence")
        return list(dict.fromkeys(topics))
