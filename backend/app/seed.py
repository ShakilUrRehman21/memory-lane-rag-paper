import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from datetime import datetime, timezone
from app.core.database import init_db
from app.ingestion.ingestion_service import ingestion_service
from app.reasoning.change_detector import ChangePointDetector
from app.reasoning.contradiction_detector import ContradictionDetector
from app.reasoning.memory_graph import MemoryGraphBuilder
from app.evaluation.experiment_runner import ExperimentRunner
from app.storage.repository import Repository
from app.core.security import hash_password


def seed_data():
    init_db()
    print("[*] Seeding realistic multi-user longitudinal archives...")

    demo_pw_hash, demo_pw_salt = hash_password("password123")
    
    from app.core.database import get_db
    with get_db() as conn:
        for uid in ["user_alex", "user_sophia", "user_marcus"]:
            conn.execute("DELETE FROM change_points WHERE user_id = ?;", (uid,))
            conn.execute("DELETE FROM memory_relationships WHERE source_memory_id IN (SELECT id FROM temporal_memories WHERE user_id = ?);", (uid,))
            conn.execute("DELETE FROM temporal_memories WHERE user_id = ?;", (uid,))
            conn.execute("DELETE FROM document_versions WHERE document_id IN (SELECT id FROM documents WHERE user_id = ?);", (uid,))
            conn.execute("DELETE FROM chunks WHERE document_id IN (SELECT id FROM documents WHERE user_id = ?);", (uid,))
            conn.execute("DELETE FROM documents WHERE user_id = ?;", (uid,))


    # 1. User 1: Alex Chen (Software Engineer -> AI Researcher, 2019-2026, 7-year horizon)
    u1 = Repository.get_user("user_alex")
    if not u1:
        Repository.create_user(
            user_id="user_alex",
            username="alex_chen",
            email="alex@memorylane.ai",
            password_hash=demo_pw_hash,
            password_salt=demo_pw_salt,
            display_name="Alex Chen",
            avatar_color="#38bdf8",
            bio="Software Engineer -> Frontier AI Researcher (7-Year Horizon: 2019-2026)"
        )
    else:
        # Ensure auth credentials exist
        from app.core.database import get_db
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET email = ?, password_hash = ?, password_salt = ? WHERE id = ?;",
                ("alex@memorylane.ai", demo_pw_hash, demo_pw_salt, "user_alex")
            )
    
    alex_corpus = [
        {
            "title": "2019 Journal - Systems Engineering & Early AI Doubts",
            "date": "2019-04-10",
            "content": (
                "I am focused purely on high-performance Java and C++ distributed database kernels. "
                "I don't think AI is relevant to my career. The neural network claims seem overhyped and impractical for mission-critical software engineering."
            )
        },
        {
            "title": "2021 Journal - First Python & PyTorch Experiments",
            "date": "2021-08-15",
            "content": (
                "Over the past few months, I have started learning machine learning out of curiosity. "
                "I have been coding in Python and training transformers on weekends. "
                "My perspective is shifting; deep learning has far more real-world power than I gave it credit for in 2019."
            )
        },
        {
            "title": "2023 Journal - Full Commitment to AI Applications",
            "date": "2023-05-20",
            "content": (
                "I decided to build AI applications full time. "
                "I have moved away from Java completely and work exclusively in Python, TypeScript, and FastAPI building retrieval systems."
            )
        },
        {
            "title": "2025 Journal - Senior AI Engineer at Foundation Lab",
            "date": "2025-06-01",
            "content": (
                "My primary career goal is to work as a senior AI engineer building multi-agent architectures and longitudinal memory. "
                "Looking back at my 2019 self, my career trajectory has completely transformed."
            )
        },
        {
            "title": "2026 Journal - Academic Publishing & Research Agenda",
            "date": "2026-02-14",
            "content": (
                "My new goal is to publish AI research papers at top machine learning conferences. "
                "I want to solve mechanistic interpretability and continuous temporal reasoning in foundation models."
            )
        },
        {
            "title": "Resume 2019",
            "date": "2019-01-10",
            "content": "Summary: Backend Systems Engineer. Skills: Java, C++, MySQL, Linux, Distributed Systems."
        },
        {
            "title": "Resume 2026",
            "date": "2026-01-10",
            "content": "Summary: AI Research Engineer. Skills: Python, PyTorch, Transformers, LLMs, RAG, Interpretability, FastAPI."
        }
    ]

    for item in alex_corpus:
        ingestion_service.ingest_text_content(
            content=item["content"],
            title=item["title"],
            user_id="user_alex",
            document_date=item["date"]
        )

    ChangePointDetector.detect_all_changes(user_id="user_alex")
    ContradictionDetector.detect_contradictions(user_id="user_alex")
    MemoryGraphBuilder.build_graph(user_id="user_alex")

    # 2. User 2: Sophia Taylor (Bioinformatics & Genomic AI, 2020-2026, 6-year horizon)
    u2 = Repository.get_user("user_sophia")
    if not u2:
        Repository.create_user(
            user_id="user_sophia",
            username="sophia_taylor",
            email="sophia@genomic-ai.org",
            password_hash=demo_pw_hash,
            password_salt=demo_pw_salt,
            display_name="Dr. Sophia Taylor",
            avatar_color="#34d399",
            bio="Molecular Biologist -> Computational Genomic AI Lead (6-Year Horizon: 2020-2026)"
        )
    else:
        from app.core.database import get_db
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET email = ?, password_hash = ?, password_salt = ? WHERE id = ?;",
                ("sophia@genomic-ai.org", demo_pw_hash, demo_pw_salt, "user_sophia")
            )

    sophia_corpus = [
        {
            "title": "2020 Lab Notebook - Wet Lab Focus",
            "date": "2020-05-18",
            "content": (
                "I believe wet lab pipetting and in-vitro assays are the only reliable way to understand protein folding. "
                "I don't trust computational predictions or machine learning for drug discovery. The algorithms produce hallucinations."
            )
        },
        {
            "title": "2022 Lab Notebook - Testing AlphaFold & Structural Modeling",
            "date": "2022-09-12",
            "content": (
                "I have started using AlphaFold and computational structural modeling in our lab daily. "
                "The accuracy of deep learning in predicting protein backbones has shocked me. I am now learning Python to automate genomic screening."
            )
        },
        {
            "title": "2024 Lab Notebook - Generative Molecular Design",
            "date": "2024-03-30",
            "content": (
                "I have transitioned to generative diffusion models for molecular candidate generation. "
                "I no longer spend long hours in the physical wet lab; my primary role is now directing machine learning for drug discovery."
            )
        },
        {
            "title": "2026 Lab Notebook - AI Biological Institute",
            "date": "2026-01-20",
            "content": (
                "My goal is to lead an autonomous AI-driven biological discovery platform. "
                "I completely reversed my 2020 skepticism. Computational biological intelligence is now the foundation of my life's work."
            )
        }
    ]

    for item in sophia_corpus:
        ingestion_service.ingest_text_content(
            content=item["content"],
            title=item["title"],
            user_id="user_sophia",
            document_date=item["date"]
        )

    ChangePointDetector.detect_all_changes(user_id="user_sophia")
    ContradictionDetector.detect_contradictions(user_id="user_sophia")
    MemoryGraphBuilder.build_graph(user_id="user_sophia")

    # 3. User 3: Marcus Vance (Product Manager -> AI Venture Builder, 2018-2026, 8-year horizon)
    u3 = Repository.get_user("user_marcus")
    if not u3:
        Repository.create_user(
            user_id="user_marcus",
            username="marcus_vance",
            email="marcus@aiventures.io",
            password_hash=demo_pw_hash,
            password_salt=demo_pw_salt,
            display_name="Marcus Vance",
            avatar_color="#c084fc",
            bio="B2B SaaS PM -> AI Venture Founder (8-Year Horizon: 2018-2026)"
        )
    else:
        from app.core.database import get_db
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET email = ?, password_hash = ?, password_salt = ? WHERE id = ?;",
                ("marcus@aiventures.io", demo_pw_hash, demo_pw_salt, "user_marcus")
            )

    marcus_corpus = [
        {
            "title": "2018 Founder Journal - B2B SaaS Dogma",
            "date": "2018-06-10",
            "content": (
                "I believe standard B2B workflow SaaS is the only scalable business model. "
                "I don't think foundational AI or deep tech is investable for early stage founders. Focus purely on seat-based software."
            )
        },
        {
            "title": "2023 Founder Journal - The Generative Shift",
            "date": "2023-11-05",
            "content": (
                "Traditional seat-based workflow software is dead. "
                "Outcome-based AI agents are replacing human workflows. I decided to pivot my entire company to building vertical AI workers."
            )
        },
        {
            "title": "2026 Founder Journal - Autonomous AI Enterprises",
            "date": "2026-03-01",
            "content": (
                "Our company operates entirely on autonomous multi-agent pipelines. "
                "My goal is to fund and build next-generation physical and cognitive AI ventures."
            )
        }
    ]

    for item in marcus_corpus:
        ingestion_service.ingest_text_content(
            content=item["content"],
            title=item["title"],
            user_id="user_marcus",
            document_date=item["date"]
        )

    ChangePointDetector.detect_all_changes(user_id="user_marcus")
    ContradictionDetector.detect_contradictions(user_id="user_marcus")
    MemoryGraphBuilder.build_graph(user_id="user_marcus")

    print("[*] Running benchmark suite...")
    ExperimentRunner.run_benchmark(run_name="Multi-User Temporal Benchmark Run")
    print("[+] Multi-user seeding complete successfully!")

if __name__ == "__main__":
    seed_data()
