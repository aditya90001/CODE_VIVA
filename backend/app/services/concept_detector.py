"""
Concept Detector — scans a student's GitHub repo profile and detects
which programming concepts they actually used.

This is the bridge between "what the student built" and "what to ask them".
Instead of asking about their code, we detect the CONCEPTS behind their code
(e.g., they used @app.route → ask about decorators; they used async def → ask
about async/await) and pull concept-level questions from the question bank.
"""
from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Concept → question bank topic mapping
# ---------------------------------------------------------------------------
# The "concept" key here will match your PDF filename (e.g. python.pdf -> "python")
CONCEPT_MAP: list[dict[str, Any]] = [
    {
        "concept": "python",
        "label": "Python Programming",
        "signals": {
            "code_patterns": [r"@\w+", r"\basync\s+def\b", r"\bclass\s+\w+", r"\bdef\s+\w+\b", r"\bdict\b", r"\btry\s*:"],
            "readme_keywords": ["python", "django", "flask", "fastapi", "script"],
            "topic_keywords": ["python", "oop", "asyncio"],
        },
    },
    {
        "concept": "machine_learning",
        "label": "Machine Learning",
        "signals": {
            "code_patterns": [r"sklearn", r"RandomForest", r"XGBoost", r"pandas", r"numpy", r"fit\(", r"predict\("],
            "readme_keywords": ["machine learning", "ml", "scikit-learn", "regression", "classification", "clustering"],
            "topic_keywords": ["machine-learning", "ml", "data-science"],
        },
    },
    {
        "concept": "deep_learning",
        "label": "Deep Learning",
        "signals": {
            "code_patterns": [r"import torch", r"import tensorflow", r"nn\.Module", r"keras", r"Sequential"],
            "readme_keywords": ["deep learning", "neural network", "pytorch", "tensorflow", "keras", "cnn", "rnn"],
            "topic_keywords": ["deep-learning", "dl", "pytorch", "tensorflow", "neural-network"],
        },
    },
    {
        "concept": "rag",
        "label": "Retrieval-Augmented Generation (RAG)",
        "signals": {
            "code_patterns": [r"\bchroma\b", r"\bfaiss\b", r"\bpinecone\b", r"vector", r"embedding", r"retriev"],
            "readme_keywords": ["rag", "retrieval", "vector database", "semantic search"],
            "topic_keywords": ["rag", "vector-database", "embeddings"],
        },
    },
    {
        "concept": "gen_ai",
        "label": "Generative AI & LLMs",
        "signals": {
            "code_patterns": [r"openai", r"groq", r"ollama", r"langchain", r"chat\.completions", r"LLM"],
            "readme_keywords": ["llm", "generative ai", "gpt", "prompt engineering", "chatbot"],
            "topic_keywords": ["llm", "genai", "generative-ai", "openai", "langchain"],
        },
    },
    {
        "concept": "backend",
        "label": "Backend & APIs",
        "signals": {
            "code_patterns": [r"FastAPI", r"APIRouter", r"@app\.(get|post)", r"express", r"app\.listen"],
            "readme_keywords": ["api", "backend", "rest", "endpoint", "server", "microservice"],
            "topic_keywords": ["api", "backend", "rest-api", "fastapi", "express"],
        },
    },
    {
        "concept": "database",
        "label": "Databases",
        "signals": {
            "code_patterns": [r"SELECT", r"INSERT", r"JOIN", r"relationship\(", r"mongoose", r"pymongo"],
            "readme_keywords": ["sql", "database", "postgres", "mysql", "mongodb", "nosql"],
            "topic_keywords": ["sql", "database", "postgres", "mongodb"],
        },
    },
    {
        "concept": "frontend",
        "label": "Frontend Development",
        "signals": {
            "code_patterns": [r"useState", r"useEffect", r"React\.", r"document\.getElementById", r"\.jsx", r"\.tsx"],
            "readme_keywords": ["react", "frontend", "ui", "css", "html", "javascript"],
            "topic_keywords": ["react", "frontend", "javascript", "typescript", "html", "css"],
        },
    },
    {
        "concept": "devops",
        "label": "DevOps & Deployment",
        "signals": {
            "code_patterns": [r"FROM\s+\w+", r"docker-compose", r"github/workflows"],
            "readme_keywords": ["docker", "ci/cd", "deployment", "kubernetes", "aws"],
            "topic_keywords": ["docker", "devops", "ci-cd", "deployment"],
        },
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _search_code(code_files: list[dict], patterns: list[str]) -> bool:
    """Return True if any pattern matches any code file."""
    if not patterns or not code_files:
        return False
    combined = "\n".join(
        (f.get("content") or "")[:3000] for f in code_files[:20]
    )
    for pattern in patterns:
        if re.search(pattern, combined, re.IGNORECASE):
            return True
    return False


def _search_text(text: str, keywords: list[str]) -> bool:
    if not text or not keywords:
        return False
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


def _search_topics(repo_topics: list[str], keywords: list[str]) -> bool:
    if not repo_topics or not keywords:
        return False
    flat = " ".join(repo_topics).lower()
    return any(kw.lower() in flat for kw in keywords)


# ---------------------------------------------------------------------------
# Main detection function
# ---------------------------------------------------------------------------
def detect_concepts(profile: dict[str, Any]) -> list[str]:
    """
    Scan the repo profile and return a list of concept keys detected,
    ordered by relevance (most specific / advanced first).

    Returns concept keys like ["python_decorators", "fastapi_basics", "rag_basics"]
    """
    readme = profile.get("readme_summary") or ""
    description = profile.get("description") or ""
    repo_topics: list[str] = profile.get("topics") or []
    code_files: list[dict] = profile.get("code_files") or []

    # Combine readme + description for text search
    full_text = f"{readme} {description}"

    detected: list[str] = []

    for entry in CONCEPT_MAP:
        signals = entry["signals"]
        code_patterns = signals.get("code_patterns", [])
        readme_keywords = signals.get("readme_keywords", [])
        topic_keywords = signals.get("topic_keywords", [])

        matched = (
            _search_code(code_files, code_patterns)
            or _search_text(full_text, readme_keywords)
            or _search_topics(repo_topics, topic_keywords)
        )

        if matched:
            detected.append(entry["concept"])

    # Fallback: if nothing detected, return basic Python and Backend concepts
    if not detected:
        detected = ["python", "backend"]

    return detected


def get_concept_label(concept_key: str) -> str:
    """Return a human-readable label for a concept key."""
    for entry in CONCEPT_MAP:
        if entry["concept"] == concept_key:
            return entry["label"]
    return concept_key.replace("_", " ").title()
