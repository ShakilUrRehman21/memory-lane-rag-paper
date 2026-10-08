import re
from typing import Dict, Any, Optional, Tuple, List
from app.models.schemas import QueryIntent

class QueryRouter:
    """
    Analyzes natural-language queries to determine:
    1. Temporal/retrieval intent (QueryIntent)
    2. Explicit/implicit temporal boundaries (start_year, end_year)
    3. Target entities and topics
    """

    @staticmethod
    def analyze_query(query: str) -> Dict[str, Any]:
        text = query.strip()
        lower = text.lower()

        # 1. Intent Classification
        intent = QueryRouter._classify_intent(lower)

        # 2. Extract Temporal Constraints
        start_year, end_year = QueryRouter._extract_year_boundaries(lower)

        # 3. Extract Target Entities/Keywords
        keywords = QueryRouter._extract_keywords(text)

        return {
            "query": query,
            "intent": intent,
            "start_year": start_year,
            "end_year": end_year,
            "keywords": keywords,
            "topic_terms": QueryRouter.topic_terms(text),
            "is_evolution_query": intent in [
                QueryIntent.EVOLUTION_ANALYSIS,
                QueryIntent.TIMELINE_REQUEST,
                QueryIntent.CHANGE_POINT_ANALYSIS
            ]
        }

    @staticmethod
    def _classify_intent(lower: str) -> QueryIntent:
        # Contradiction / Reversal
        if any(w in lower for w in ["contradict", "revers", "opposite", "conflicting", "change my mind", "flip"]):
            return QueryIntent.CONTRADICTION_ANALYSIS

        # Change-point detection
        if any(w in lower for w in ["turning point", "inflection point", "suddenly", "gradually", "when did i stop", "when did i start", "shift"]):
            return QueryIntent.CHANGE_POINT_ANALYSIS

        # Timeline request
        if any(w in lower for w in ["timeline", "chronolog", "milestones", "history of", "order of"]):
            return QueryIntent.TIMELINE_REQUEST

        # Version comparison
        if any(w in lower for w in ["version", "resume v", "diff", "between versions", "v1 and v2", "revision"]):
            return QueryIntent.VERSION_COMPARISON

        # Stable patterns
        if any(w in lower for w in ["stable", "consistent", "never change", "always thought", "constant"]):
            return QueryIntent.STABLE_PATTERN_ANALYSIS

        # Evidence request
        if any(w in lower for w in ["what evidence", "proof", "source passage", "grounded in"]):
            return QueryIntent.EVIDENCE_REQUEST

        # Evolution / Change analysis
        if any(w in lower for w in ["how has my", "how did my", "evolv", "change over time", "over the years", "from 20", "progression"]):
            return QueryIntent.EVOLUTION_ANALYSIS

        # Temporal lookup (specific point in time)
        if re.search(r"\b(in|during|at|around)\s+(20\d{2})\b", lower) or "what did i think in" in lower:
            return QueryIntent.TEMPORAL_LOOKUP

        return QueryIntent.FACT_LOOKUP

    @staticmethod
    def _extract_year_boundaries(lower: str) -> Tuple[Optional[int], Optional[int]]:
        # "between 2023 and 2026"
        between_match = re.search(r"\bbetween\s+(20\d{2})\s+and\s+(20\d{2})\b", lower)
        if between_match:
            y1, y2 = map(int, between_match.groups())
            return min(y1, y2), max(y1, y2)

        # "from 2022 to 2025"
        from_to_match = re.search(r"\bfrom\s+(20\d{2})\s+to\s+(20\d{2})\b", lower)
        if from_to_match:
            y1, y2 = map(int, from_to_match.groups())
            return min(y1, y2), max(y1, y2)

        # "before 2024"
        before_match = re.search(r"\bbefore\s+(20\d{2})\b", lower)
        if before_match:
            return None, int(before_match.group(1))

        # "after 2023" / "since 2023"
        after_match = re.search(r"\b(?:after|since)\s+(20\d{2})\b", lower)
        if after_match:
            return int(after_match.group(1)), None

        # Standalone "in 2023"
        in_match = re.search(r"\b(?:in|during)\s+(20\d{2})\b", lower)
        if in_match:
            y = int(in_match.group(1))
            return y, y

        return None, None

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        # Filter out common stop words
        stops = {
            "what", "did", "i", "think", "about", "how", "has", "my", "opinion", "changed",
            "over", "the", "years", "time", "was", "were", "when", "show", "me", "a", "an",
            "is", "are", "and", "or", "to", "in", "of", "for", "with", "on", "at", "between"
        }
        words = re.findall(r"\b[A-Za-z0-9+#.-]+\b", text)
        return [w for w in words if w.lower() not in stops and len(w) > 1]

    # Words that describe the *act* of asking about change rather than its subject.
    _META_WORDS = {
        "what", "did", "does", "do", "i", "think", "thinking", "thought", "go", "went", "about", "how", "has", "have", "had", "my", "me",
        "opinion", "opinions", "view", "views", "viewpoint", "perspective", "stance", "feel", "feelings", "feeling",
        "changed", "change", "changes", "changing", "evolve", "evolved", "evolution", "shift", "shifted", "over",
        "the", "years", "year", "time", "times", "was", "were", "when", "show", "a", "an", "is", "are", "and",
        "or", "to", "in", "of", "for", "with", "on", "at", "between", "from", "since", "after", "before", "it",
        "interest", "interested", "attitude", "toward", "towards", "regarding", "relationship", "happened",
        "become", "became", "still", "now", "then", "ever", "used", "use", "using", "like", "liked", "any",
        "s", "t", "much", "many", "more", "less", "really", "timeline", "history", "progression", "start",
        "started", "stop", "stopped", "turning", "point", "points", "why", "which", "who", "where", "there"}

    @staticmethod
    def topic_terms(query: str) -> List[str]:
        """Content words naming the subject of the question (used for query-focused change detection)."""
        words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]*", query)
        out = []
        for w in words:
            lw = w.lower().strip(".")
            if lw in QueryRouter._META_WORDS or len(lw) < 2 or re.fullmatch(r"(19|20)\d{2}", lw):
                continue
            if lw not in out:
                out.append(lw)
        return out
