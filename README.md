# ⏳ Memory Lane RAG

### Temporal Retrieval-Augmented Generation & Longitudinal Reasoning System

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![SQLite FTS5](https://img.shields.io/badge/SQLite-FTS5%20BM25-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)


> **Research version.** This repository holds the exact code, the MLLB-Synth benchmark, the results and the reproduction scripts described in the paper *Remembering Change: Temporal Stratification and Stance-Change Detection for Retrieval over Personal Archives* (submitted to SN Computer Science). See `REPRODUCE.md` to regenerate every table and figure. The live application is maintained separately at https://github.com/ShakilUrRehman21/memory-lane-rag.

---

## 🌟 Overview

Traditional Retrieval-Augmented Generation (RAG) systems assume information exists as **static, time-agnostic knowledge**. When matching queries using dense vector similarity alone, they suffer from two critical flaws:

1. **Recency & Density Clustering**: Search returns documents densely clustered around recent dates or repetitive topics, ignoring the historical progression.
2. **Temporal Blindness**: Vector similarity cannot differentiate between what a person *believed in 2019*, *re-evaluated in 2022*, and *committed to in 2026*.

**Memory Lane RAG** is an open-source, full-stack temporal RAG framework engineered specifically for **longitudinal understanding**. It captures how beliefs, goals, decisions, preferences, and knowledge transform over time, grounding every generated statement in verifiable citations and calibrated epistemic uncertainty.

```
"How has my perspective on AI shifted from 2019 to 2026?"
"When did I abandon Java and what did I replace it with?"
"Did I contradict my earlier career goals?"
"What was the pivotal turning point in my research agenda?"
```

---

## 🔬 Core Innovations

### 1. The Quad-Date Temporal Model
Standard pipelines rely on a single document timestamp. Memory Lane RAG models documents and atomic memories across four independent temporal coordinates:

| Timestamp | Notation | Meaning | Example |
| :--- | :---: | :--- | :--- |
| **Document Date** | $t_{doc}$ | When the document was authored or published | *Written on Oct 14, 2025* |
| **Event Date** | $t_{event}$ | When the described event, decision, or realization occurred in reality | *"Back in spring 2021, I decided..."* $\rightarrow 2021\text{-}04$ |
| **Ingestion Date** | $t_{ingest}$ | System indexing timestamp | *Indexed on Oct 07, 2026* |
| **Version Date** | $t_{ver}$ | Revision timestamp for document iterations | *Resume v1 (2019) vs Resume v3 (2026)* |

### 2. Temporal Memory Units (TMU)
Rather than passing unsegmented text chunks to downstream synthesis, documents are deconstructed into structured **Temporal Memory Units (TMU)**:
- **Proposition Typology**: `belief`, `goal`, `decision`, `preference`, `knowledge`, `observation`, `plan`, `reflection`, `event`
- **Stance Polarity**: Continuous scale from $-1.0$ (rejection/abandonment/skepticism) to $+1.0$ (strong commitment/adoption)
- **Temporal Confidence & Extents**: Explicit interval $[t_{start}, t_{end}]$ with extraction certainty score

### 3. Multi-Period Stratified Retrieval & Reciprocal Rank Fusion (RRF)
To prevent semantic vector retrieval from clustering exclusively in the most verbose epoch, the engine applies **Stratified Epoch Binning**:
1. Candidate memories are partitioned into chronological bins (e.g., 2018–2020, 2021–2022, 2023–2024, 2025–2026).
2. Balanced round-robin sampling selects top representative candidates across each bin.
3. Reranking combines BM25 full-text rank, dense cosine rank, and milestone polarity boosts using Reciprocal Rank Fusion:
   $$RRF(d) = \sum_{m \in \{\text{dense}, \text{sparse}, \text{temporal}\}} \frac{1}{k + \text{rank}_m(d)}$$

### 4. Semantic Drift & Change-Point Detection
- **Semantic Distance**: Pairwise distance $\Delta_{i,j} = 1 - \cos(\mathbf{e}_i, \mathbf{e}_j)$ measures ideological divergence.
- **Polarity Inversions**: Flags stance reversals when $\text{polarity}_i \cdot \text{polarity}_j < 0$.
- **Transition Categorization**: Classifies transitions into `gradual_evolution`, `sudden_shift`, `reversal`, or `goal_abandonment`.
- **Bounded Temporal Uncertainty**: When consecutive evidence is separated by $> 180$ days, the system explicitly reports:
  $$\text{"Shift occurred between June 2021 and May 2023 (exact turning point unrecorded in archive)."}$$

### 5. Grounded Claim Provenance
Generated longitudinal summaries are deconstructed into individual claims:
- **`explicit`**: Direct citations supported by verbatim document text.
- **`empirical_change`**: Transitions verified by mathematical drift or polarity flips.
- **`inferred_relationship`**: Hypothesized connections accompanied by epistemic confidence scores.

---

## 🏗️ System Architecture

```
                            ┌──────────────────────────────────────────┐
                            │    User Ingestion (PDF / DOCX / MD / TXT) │
                            └────────────────────┬─────────────────────┘
                                                 │
                               ┌─────────────────▼─────────────────┐
                               │     Ingestion & Parser Pipeline   │
                               │  - Quad-Date Disambiguation       │
                               │  - Semantic Chunker               │
                               │  - TMU & Stance Polarity Scorer   │
                               └─────────────────┬─────────────────┘
                                                 │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   │                             │                             │
        ┌──────────▼──────────┐       ┌──────────▼──────────┐       ┌──────────▼──────────┐
        │  SQLite FTS5 (BM25) │       │ Vector Cosine Store │       │ Relational TMU DB   │
        │  Lexical Retrieval  │       │ Semantic Retrieval  │       │ Entities & Metadata │
        └──────────┬──────────┘       └──────────┬──────────┘       └──────────┬──────────┘
                   │                             │                             │
                   └─────────────────────────────┼─────────────────────────────┘
                                                 │
                               ┌─────────────────▼─────────────────┐
                               │   Multi-Period Stratified RRF     │
                               │   Hybrid Retrieval & Reranker     │
                               └─────────────────┬─────────────────┘
                                                 │
                   ┌─────────────────────────────┴─────────────────────────────┐
                   │                                                           │
        ┌──────────▼──────────┐                                     ┌──────────▼──────────┐
        │ Reasoning Engine    │                                     │ Grounded Synthesizer│
        │ - Semantic Drift    │                                     │ - Provenance Claims │
        │ - Polarity Flips    │                                     │ - Citation Anchors  │
        │ - Graph Relational  │                                     │ - Epistemic Bounds  │
        └──────────┬──────────┘                                     └──────────┬──────────┘
                   │                                                           │
                   └─────────────────────────────┬─────────────────────────────┘
                                                 │
                               ┌─────────────────▼─────────────────┐
                               │       Modern React 18 Web UI      │
                               │   Timeline · Graph · Benchmarks   │
                               └───────────────────────────────────┘
```

---

## 📊 Empirical Research Benchmark Studio

Memory Lane RAG includes a research studio comparing three retrieval paradigms on longitudinal reasoning tasks:

| Paradigm | Retrieval Mechanism | Temporal Context | Change Detection | Grounding |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline RAG** | Dense Top-K Cosine | Date-ignorant | None | Standard prompt |
| **Temporal RAG** | Vector + Date Filter/Sort | Metadata timestamp filter | None | Standard prompt |
| **Memory Lane RAG** | Hybrid BM25 + Vector + Stratified Bins | Quad-Date Model + TMU | Drift & Polarity Flips | Claim Provenance + Uncertainty Bounds |

### Experimental Results (v1.1, reproducible)

> The results table shipped with v1.0 could not be reproduced and has been removed; see
> `EVALUATION_REPORT.md` (audit of v1.0) and `EVALUATION_REPORT_v1.1.md` (fixes and re-evaluation).
> Every number below is produced by a script in `scripts/` (deterministic, no API key needed).

**MLLB-Synth v1, held-out test split** (128 personas, 512 queries; `scripts/eval_mllb_synth.py`):

| Metric | Baseline RAG | Temporal RAG | Memory Lane v1.0 | **Memory Lane v1.1** |
| :--- | :---: | :---: | :---: | :---: |
| Temporal Coverage Recall, skewed density | 0.71 | 0.71 | 0.89 | **0.86** (0.98 with `ML_STRATIFICATION_MODE=always`) |
| Change-point F1 (topic-matched, exact years) | – | – | 0.12 | **0.35** |
| Reversals detected | – | – | 20% | **44%** |
| False alarms on stable-stance personas | – | – | 50% | **1.6%** |

**LoCoMo evidence retrieval, held-out conversations 6-10** (`scripts/bench_conversations.py`): Recall@5
v1.1 **0.406** vs v1.0 0.334 (p < 0.001), on par with Okapi BM25 (0.425, p = 0.37).

Known limits: stance in paraphrased wording is not detected by the default rule-based extractor
(use `ML_EXTRACTOR=llm`); answer accuracy and hallucination rates require an LLM run
(`scripts/eval_llm_qa.py`, `scripts/eval_llm_grounding.py`).

---

## 📁 Repository Structure

```
memory-lane-rag/
├── backend/
│   ├── app/
│   │   ├── api/                      # FastAPI REST endpoints
│   │   │   ├── routes_auth.py        # User login, registration, token authentication
│   │   │   ├── routes_users.py       # User profile listings & switcher
│   │   │   ├── routes_documents.py   # Multi-format document ingestion & uploads
│   │   │   ├── routes_query.py       # Longitudinal natural language query endpoint
│   │   │   ├── routes_timeline.py    # Chronological memory event stream
│   │   │   ├── routes_changes.py     # Semantic drift & turning point explorer
│   │   │   ├── routes_versions.py    # Document revision diff comparisons
│   │   │   ├── routes_graph.py       # Temporal relationship knowledge graph
│   │   │   └── routes_research.py    # Empirical benchmark runner & evaluation
│   │   ├── core/
│   │   │   ├── config.py             # Settings, storage paths, hyperparameters
│   │   │   ├── database.py           # SQLite connection pool, migrations, FTS5 indices
│   │   │   └── security.py           # Password hashing, PBKDF2 salt, session tokens
│   │   ├── ingestion/
│   │   │   ├── parsers.py            # PDF, DOCX, TXT, MD parsers
│   │   │   ├── date_extractor.py     # Quad-Date parsing & temporal normalization
│   │   │   ├── chunker.py            # Semantic-temporal chunker
│   │   │   ├── tmu_extractor.py      # TMU extraction & stance polarity scoring
│   │   │   └── ingestion_service.py  # Ingestion workflow orchestrator
│   │   ├── storage/
│   │   │   ├── repository.py         # Relational operations with user data isolation
│   │   │   ├── fts_store.py          # SQLite FTS5 BM25 search
│   │   │   └── vector_store.py       # Normalized cosine similarity vector index
│   │   ├── retrieval/
│   │   │   ├── query_router.py       # Query intent classifier & date boundary parser
│   │   │   ├── stratified_sampler.py # Multi-epoch balanced temporal sampler
│   │   │   ├── reranker.py           # Reciprocal Rank Fusion & milestone booster
│   │   │   └── hybrid_retriever.py   # Hybrid sparse + dense + temporal retriever
│   │   ├── reasoning/
│   │   │   ├── change_detector.py    # Semantic drift & turning point detector
│   │   │   ├── contradiction_detector.py # Stance polarity inversion detector
│   │   │   ├── version_diff.py       # Revision comparison engine
│   │   │   └── memory_graph.py       # Directed temporal relationship graph
│   │   ├── synthesis/
│   │   │   ├── llm_provider.py       # LLM provider (Gemini / OpenAI / Deterministic fallback)
│   │   │   └── grounded_synthesizer.py # Claim provenance & citation synthesizer
│   │   ├── evaluation/
│   │   │   ├── benchmark_dataset.py  # Multi-year longitudinal test corpus
│   │   │   ├── metrics.py            # COA, TCR, Change F1, UHCR metrics calculators
│   │   │   └── experiment_runner.py  # Empirical benchmark runner
│   │   ├── main.py                   # FastAPI application initialization & CORS
│   │   └── seed.py                   # Realistic multi-user longitudinal seeder
│   ├── tests/                        # 24 tests, isolated temporary database (conftest.py)
│   │   ├── test_auth_flow.py
│   │   ├── test_phase1_ingestion.py
│   │   ├── test_phase2_retrieval.py
│   │   ├── test_phase3_reasoning.py
│   │   └── test_phase4_and_phase5_api_and_research.py
│   └── run.py                        # Backend server startup launcher
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AskMemoryLaneView.tsx # Natural language longitudinal inquiry
│   │   │   ├── TimelineView.tsx      # Zoomable chronological stream
│   │   │   ├── ChangeExplorerView.tsx# Semantic drift & transition trajectories
│   │   │   ├── ContradictionView.tsx # Stance reversal inspector
│   │   │   ├── VersionDiffView.tsx   # Document revision comparison
│   │   │   ├── MemoryGraphView.tsx   # Knowledge network node-link visualizer
│   │   │   ├── DocumentsView.tsx     # Ingestion & file management studio
│   │   │   ├── ResearchStudioView.tsx# Comparative benchmark workbench
│   │   │   ├── AuthView.tsx          # Login & registration modal
│   │   │   └── MemoryLaneLogo.tsx    # Brand logo component
│   │   ├── api.ts                    # Type-safe API client
│   │   ├── App.tsx                   # Main layout and workspace switcher
│   │   └── index.css                 # Dark-mode design system
│   ├── package.json
│   └── vite.config.ts
├── data/                             # Storage directory (.gitignored)
│   └── storage/
│       ├── uploads/                  # Ingested file storage
│       └── vectors/                  # Vector cache files
├── ARCHITECTURE_PLAN.md              # In-depth architectural design specification
├── DEPLOYMENT.md                     # Production deployment guide (Render, Railway, Docker, VPS)
├── Dockerfile                        # Multi-stage production container definition
├── docker-compose.yml                # Docker Compose with persistent data volume
├── pytest.ini                        # Pytest configuration
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variables template
├── .gitignore                        # Git ignore rules
└── README.md
```

---

## 🐳 One-Line Docker Run

```bash
docker compose up -d --build
```
*Access the unified full-stack application at `http://localhost:8000`.* See [DEPLOYMENT.md](DEPLOYMENT.md) for complete cloud guides (Render, Railway, Vercel, VPS).

---

## 🚀 Local Development Quickstart

### Prerequisites
- **Python 3.10+** (tested on Python 3.13)
- **Node.js 18+** & npm

### 1. Clone & Set Up Backend

```bash
# Clone the repository
git clone https://github.com/ShakilUrRehman21/memory-lane-rag-paper.git
cd memory-lane-rag-paper

# Create and activate Python virtual environment
python -m venv .venv

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
# source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# (Optional) Configure API keys
cp .env.example .env
```

> **Note**: An LLM API key is completely optional! The engine includes a high-fidelity local deterministic synthesizer for offline development and reproducible benchmarking.

### 2. Seed Data & Run Tests

```bash
# Seed realistic multi-year longitudinal archives (2018–2026)
python backend/app/seed.py

# Run automated test suite
pytest
```

### 3. Launch the Backend Server

```bash
python backend/run.py
```
*The FastAPI backend will start at `http://127.0.0.1:8000` (API documentation available at `http://127.0.0.1:8000/docs`).*

### 4. Launch the Frontend

In a separate terminal:

```bash
cd frontend

# Install frontend dependencies
npm install

# Start Vite development server
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 👥 Demo Personas

The database is pre-seeded with three realistic longitudinal personas:

| Persona | Username | Default Password | Horizon | Trajectory Focus |
| :--- | :--- | :--- | :---: | :--- |
| **Alex Chen** | `alex_chen` | `password123` | **2019 – 2026** (7 Years) | Systems Engineer (Java/C++) $\rightarrow$ Frontier AI Researcher |
| **Dr. Sophia Taylor** | `sophia_taylor` | `password123` | **2020 – 2026** (6 Years) | Wet Lab Biologist $\rightarrow$ Computational Genomic AI Lead |
| **Marcus Vance** | `marcus_vance` | `password123` | **2018 – 2026** (8 Years) | B2B SaaS PM $\rightarrow$ Autonomous AI Venture Builder |

*Switch between personas seamlessly in the top-right navigation bar to test longitudinal queries across distinct domains.*

---

## 🖥️ User Interface Views

1. **Ask Memory Lane**: Submit natural language longitudinal questions. Responses include verified claim badges, chronological context tags, and epistemic uncertainty qualifiers.
2. **Chronological Timeline**: An interactive timeline of propositions categorized by type (`belief`, `goal`, `decision`, etc.) with visual polarity indicators.
3. **Change Explorer**: Interactive visual inspection of detected semantic drift, stance shifts, and transition velocity over multi-year periods.
4. **Contradiction Inspector**: Pinpoints exact stance inversions where earlier beliefs or commitments were reversed.
5. **Version Diff**: Side-by-side textual and structural comparison of document iterations (e.g., Resume 2019 vs. Resume 2026).
6. **Temporal Memory Graph**: An interactive node-link graph mapping directional relationships across memories.
7. **Document Studio**: Upload and index documents (PDF, DOCX, TXT, MD) with automatic Quad-Date and TMU extraction.
8. **Research Studio**: Interactive evaluation workbench running real-time comparative benchmarks between Baseline RAG, Temporal RAG, and Memory Lane RAG.

---

## 🔌 API Reference

### Authentication & Users
- `POST /api/auth/register` — Create a new account
- `POST /api/auth/login` — Authenticate and obtain session token
- `GET /api/auth/me` — Get current authenticated profile
- `POST /api/auth/logout` — Revoke session token
- `GET /api/users` — List registered user personas

### Longitudinal Query & Ingestion
- `POST /api/query` — Submit longitudinal question:
  ```json
  {
    "query": "How did Alex's career goals change between 2019 and 2026?",
    "user_id": "user_alex",
    "top_k": 8
  }
  ```
- `POST /api/documents/upload` — Multipart form upload supporting PDF, DOCX, TXT, MD
- `GET /api/documents` — List indexed documents
- `DELETE /api/documents/{id}` — Cascade deletion of document, chunks, vectors, and TMUs

### Temporal Reasoning & Research
- `GET /api/timeline?user_id=user_alex` — Retrieve chronological memory stream
- `GET /api/changes?user_id=user_alex` — Retrieve detected semantic drift and turning points
- `GET /api/contradictions?user_id=user_alex` — Inspect stance polarity inversions
- `GET /api/versions/{doc_id}/diff?target_doc_id={target_id}` — Document version diff
- `GET /api/graph?user_id=user_alex` — Node-edge graph of temporal memories
- `POST /api/research/run-benchmark` (alias `/api/research/benchmark`) — Run the built-in smoke-test benchmark (5 documents, 3 queries; not evidence)

---

## 🔒 Security & Data Isolation

- **User Isolation**: All relational queries, FTS5 BM25 lookups, and vector cosine searches are strictly isolated by `user_id`.
- **Cascade Deletion**: Removing a document automatically purges all associated chunks, TMUs, vector embeddings, and graph edges in an atomic transaction.
- **Untrusted Input Sanitation**: Document contents are parsed with strict memory boundaries and stripped of potential prompt injection vectors.

---

## 📄 License

This project is open-source and licensed under the [MIT License](LICENSE).

---

## ⚙️ Configuration (v1.1)

All settings are environment variables (defaults in `backend/app/core/config.py`):

| Variable | Default | Meaning |
| :--- | :--- | :--- |
| `ML_EMBEDDING_BACKEND` | `wordllama` | `wordllama`, `st:<model>` (sentence-transformers, e.g. `st:BAAI/bge-m3`), `openai:<model>`, or `hash` (v1.0 behaviour, ablation only) |
| `ML_STRATIFICATION_MODE` | `router` | `router` (longitudinal-intent queries only), `always`, `soft`, `off` |
| `ML_EPOCH_MODE` | `adaptive` | `adaptive` (span split into ≤6 bins) or `year` |
| `ML_DRIFT_THRESHOLD` | `0.70` | semantic-drift threshold, calibrated for WordLlama; re-run `scripts/calibrate_drift.py` for other embedders |
| `ML_EXTRACTOR` | `rules` | `rules` (offline lexicons) or `llm` (LLM-labelled memory type, stance, entities) |
| `ML_LLM_BACKEND` | auto | `gemini`, `openai` (any OpenAI-compatible endpoint via `OPENAI_BASE_URL`), or `deterministic` |
| `ML_LLM_MODEL` | provider default | synthesis / extraction model |
| `ML_DATA_DIR` | `./data` | storage location (use a fresh directory per experiment) |
| `ML_PERSIST_ANALYSIS` | `0` | `1` = also store change points detected during queries (v1.0 behaviour) |

Reproducing the paper's experiments: see `REPRODUCE.md`.
