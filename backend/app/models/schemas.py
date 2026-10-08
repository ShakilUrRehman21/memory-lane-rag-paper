from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class MemoryType(str, Enum):
    EVENT = "event"
    BELIEF = "belief"
    GOAL = "goal"
    DECISION = "decision"
    PREFERENCE = "preference"
    KNOWLEDGE = "knowledge"
    OBSERVATION = "observation"
    PLAN = "plan"
    REFLECTION = "reflection"

class DateGranularity(str, Enum):
    DAY = "day"
    MONTH = "month"
    SEASON = "season"
    YEAR = "year"
    DECADE = "decade"
    UNRECORDED = "unrecorded"

class DateSource(str, Enum):
    EXPLICIT_IN_TEXT = "explicit_in_text"
    DOC_METADATA = "doc_metadata"
    RELATIVE_INFERRED = "relative_inferred"
    USER_OVERRIDE = "user_override"

class RelationType(str, Enum):
    EVOLVES_FROM = "evolves_from"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    REVISES = "revises"
    FOLLOWS = "follows"
    REPLACES = "replaces"
    RELATED_TO = "related_to"

class QueryIntent(str, Enum):
    FACT_LOOKUP = "FACT_LOOKUP"
    TEMPORAL_LOOKUP = "TEMPORAL_LOOKUP"
    EVOLUTION_ANALYSIS = "EVOLUTION_ANALYSIS"
    TIMELINE_REQUEST = "TIMELINE_REQUEST"
    CHANGE_POINT_ANALYSIS = "CHANGE_POINT_ANALYSIS"
    CONTRADICTION_ANALYSIS = "CONTRADICTION_ANALYSIS"
    VERSION_COMPARISON = "VERSION_COMPARISON"
    STABLE_PATTERN_ANALYSIS = "STABLE_PATTERN_ANALYSIS"
    EVIDENCE_REQUEST = "EVIDENCE_REQUEST"

# User Models
class UserCreate(BaseModel):
    username: str
    display_name: str
    email: Optional[str] = None
    password: Optional[str] = None
    avatar_color: str = "#38bdf8"
    bio: Optional[str] = None

class UserRegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    display_name: str
    bio: Optional[str] = None
    avatar_color: str = "#38bdf8"

class UserLoginRequest(BaseModel):
    username_or_email: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    email: Optional[str] = None
    avatar_color: str
    bio: Optional[str] = None
    created_at: str
    document_count: int = 0
    tmu_count: int = 0
    earliest_memory_date: Optional[str] = None
    latest_memory_date: Optional[str] = None

class AuthResponse(BaseModel):
    token: str
    user: UserResponse

# Thought Lodging (Time Capsule)
class LodgeThoughtRequest(BaseModel):
    statement: str
    memory_type: MemoryType = MemoryType.BELIEF
    event_date: Optional[str] = None  # ISO8601 (e.g. today or custom historical date)
    stance_polarity: Optional[float] = None  # None for auto-detection
    entities: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    context_note: Optional[str] = None

# Document Models
class DocumentBase(BaseModel):
    title: str
    file_type: str
    document_date: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DocumentCreate(DocumentBase):
    user_id: str = "default_user"
    content: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: str
    user_id: str
    file_path: str
    file_size: int
    hash_sha256: str
    created_at: str
    chunk_count: int = 0
    tmu_count: int = 0

# Chunk Models
class ChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    page_number: Optional[int] = None
    start_char: int
    end_char: int
    created_at: str

# Temporal Memory Unit (TMU)
class TMUBase(BaseModel):
    memory_type: MemoryType
    statement: str
    event_date_start: Optional[str] = None
    event_date_end: Optional[str] = None
    date_granularity: DateGranularity = DateGranularity.UNRECORDED
    date_confidence: float = 1.0
    date_source: DateSource = DateSource.DOC_METADATA
    stance_polarity: float = 0.0  # -1.0 to 1.0
    entities: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)

class TMUCreate(TMUBase):
    document_id: str
    chunk_id: str
    user_id: str = "default_user"

class TMUResponse(TMUBase):
    id: str
    document_id: str
    chunk_id: str
    user_id: str
    document_title: Optional[str] = None
    created_at: str

# Memory Graph Edges
class MemoryRelationshipResponse(BaseModel):
    id: str
    source_memory_id: str
    target_memory_id: str
    relation_type: RelationType
    confidence: float
    evidence_rationale: Optional[str] = None
    source_statement: Optional[str] = None
    target_statement: Optional[str] = None
    source_date: Optional[str] = None
    target_date: Optional[str] = None
    created_at: str

# Change Points
class ChangePointResponse(BaseModel):
    id: str
    user_id: str
    topic_or_entity: str
    from_period: str
    to_period: str
    change_type: str  # gradual_evolution, sudden_shift, reversal, goal_abandonment
    magnitude: float
    earlier_memory_id: str
    later_memory_id: str
    earlier_statement: Optional[str] = None
    later_statement: Optional[str] = None
    earlier_date: Optional[str] = None
    later_date: Optional[str] = None
    uncertainty_bounds: Optional[str] = None
    created_at: str

# Version Snapshots
class DocumentVersionResponse(BaseModel):
    id: str
    series_name: str
    version_label: str
    document_id: str
    version_order: int
    version_date: str

class VersionDiffResponse(BaseModel):
    series_name: str
    earlier_version: str
    later_version: str
    added_skills_or_topics: List[str]
    removed_skills_or_topics: List[str]
    retained_skills_or_topics: List[str]
    semantic_changes: List[Dict[str, Any]]
    summary: str

# Retrieval & Provenance
class GroundedClaim(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: str  # explicit, empirical_change, inferred_relationship
    confidence: float
    evidence_tmu_ids: List[str]
    source_citations: List[Dict[str, Any]]
    is_uncertain: bool = False
    uncertainty_note: Optional[str] = None

class TimelinePoint(BaseModel):
    period: str
    date_display: str
    event_date: str
    headline: str
    statement: str
    memory_type: MemoryType
    document_title: str
    document_id: str
    tmu_id: str
    confidence: float
    stance_polarity: float

# Query & Generation
class QueryRequest(BaseModel):
    query: str
    user_id: str = "default_user"
    pipeline_mode: str = "memory_lane"  # "baseline", "temporal", "memory_lane"
    filter_start_year: Optional[int] = None
    filter_end_year: Optional[int] = None
    filter_topics: Optional[List[str]] = None
    filter_memory_types: Optional[List[MemoryType]] = None
    top_k: int = 10
    ablation_disable_temporal: bool = False
    ablation_disable_rerank: bool = False
    ablation_disable_change_detection: bool = False
    stratification_mode: Optional[str] = None  # "always" | "router" | "off" (default: settings)

class QueryResponse(BaseModel):
    query: str
    detected_intent: QueryIntent
    pipeline_used: str
    answer: str
    timeline: List[TimelinePoint]
    detected_changes: List[ChangePointResponse]
    potential_contradictions: List[MemoryRelationshipResponse]
    grounded_claims: List[GroundedClaim]
    uncertainty_notes: List[str]
    retrieved_tmus: List[TMUResponse]
    execution_time_ms: float
    model_calls: int = 1
    ranked_tmu_ids: List[str] = []       # retrieval order (relevance), before chronological presentation
    stratified: bool = False
    synthesis_backend: str = "deterministic"

# Evaluation & Benchmark
class EvaluationBenchmarkRequest(BaseModel):
    run_name: str = "Benchmark Run"
    test_suite: str = "temporal_longitudinal_v1"
    pipelines: List[str] = ["baseline", "temporal", "memory_lane"]

class PipelineMetric(BaseModel):
    pipeline: str
    chronological_ordering_accuracy: Optional[float] = None  # None = not measurable (deterministic synthesizer)
    temporal_coverage_recall: Optional[float] = None
    change_point_f1: Optional[float] = None
    change_point_precision: Optional[float] = None
    change_point_recall: Optional[float] = None
    unsupported_claim_rate: Optional[float] = None
    average_latency_ms: float
    total_token_usage: int = 0  # v1.1: 0 unless measured; v1.0 reported an invented estimate
    synthesis_backend: str = "deterministic"
    n_queries: int = 0

class EvaluationRunResponse(BaseModel):
    id: str
    run_name: str
    created_at: str
    metrics: Dict[str, PipelineMetric]
    summary_findings: str
