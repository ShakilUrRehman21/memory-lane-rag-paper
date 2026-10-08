from typing import List, Dict, Any

BENCHMARK_CORPUS_DOCUMENTS = [
    {
        "title": "2022 Journal - Career Reflections",
        "date": "2022-03-15",
        "content": (
            "I am currently working as a backend engineer focusing heavily on Java and Spring Boot. "
            "I honestly don't think AI is relevant to my career right now. The hype seems premature. "
            "My goal for this year is to master distributed systems and MySQL performance optimization."
        )
    },
    {
        "title": "2023 Journal - New Explorations",
        "date": "2023-05-20",
        "content": (
            "Over the past few months, I have started learning machine learning out of curiosity. "
            "I have been coding in Python and training simple PyTorch models on weekends. "
            "My perspective is shifting; machine learning has much more practical potential than I thought in 2022."
        )
    },
    {
        "title": "2024 Journal - Production AI",
        "date": "2024-04-10",
        "content": (
            "I want to build AI applications full time now. "
            "I spent this quarter building retrieval-augmented generation systems and fine-tuning LLMs. "
            "I have completely stopped using Java for new projects and have moved almost entirely to Python and TypeScript."
        )
    },
    {
        "title": "2025 Journal - AI Engineer Transition",
        "date": "2025-06-01",
        "content": (
            "My primary career goal is to work as an AI engineer at a leading laboratory. "
            "I have deployed multi-agent RAG architectures and evaluate models daily. "
            "Looking back to 2022, my career trajectory has completely transformed."
        )
    },
    {
        "title": "2026 Journal - Research Ambitions",
        "date": "2026-02-18",
        "content": (
            "I now want to conduct AI research and publish academic papers in conference venues. "
            "Engineering alone is not satisfying; I want to investigate mechanistic interpretability and temporal reasoning in foundation models."
        )
    }
]

BENCHMARK_QUERIES = [
    {
        "query_id": "q1_ai_evolution",
        "query": "How has my thinking about AI changed from 2022 to 2026?",
        "expected_years": ["2022", "2023", "2024", "2025", "2026"],
        "expected_reversal_topic": "Artificial Intelligence",
        "topic": "AI",
        "ground_truth_transitions": [
            ("2022", "2023", "reversal"),
            ("2023", "2024", "gradual_evolution"),
            ("2024", "2025", "gradual_evolution"),
            ("2025", "2026", "gradual_evolution")
        ]
    },
    {
        "query_id": "q2_java_transition",
        "query": "What happened to my interest in Java?",
        "expected_years": ["2022", "2024"],
        "expected_reversal_topic": "Java",
        "topic": "Java",
        "ground_truth_transitions": [
            ("2022", "2024", "reversal")
        ]
    },
    {
        "query_id": "q3_career_goals",
        "query": "What were my major career goals over the years?",
        "expected_years": ["2022", "2024", "2025", "2026"],
        "expected_reversal_topic": "Career & Goals",
        "topic": None,
        "ground_truth_transitions": []
    }
]
