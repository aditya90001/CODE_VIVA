import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_evaluator.db")
os.environ.setdefault("APP_ENV", "test")

from fastapi.testclient import TestClient

from backend.app.db import Base, engine
from backend.app.main import app
from backend.app.services.evaluation_service import EvaluationService

Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_question_generation_uses_repo_tech_stack():
    profile = {
        "language": "Python",
        "topics": ["api", "llm", "rag", "postgres"],
        "description": "A Python RAG chatbot with FastAPI, Postgres, and LLM services.",
        "readme_summary": "FastAPI backend and React frontend with vector search and LLM orchestration.",
    }

    question = EvaluationService.generate_question(profile, [])
    question_text = question["question"].lower()
    assert any(token in question_text for token in ["fastapi", "async", "sql", "join", "rag", "chunk", "hallucination", "react", "llm"])


def test_question_generation_stays_aligned_with_repo_stack():
    profile = {
        "language": "HTML",
        "topics": ["frontend", "css", "javascript", "web"],
        "description": "A static portfolio website built with HTML, CSS, and JavaScript.",
        "readme_summary": "Responsive landing page built with semantic HTML and browser-side interactivity.",
    }

    question = EvaluationService.generate_question(profile, [])
    question_text = question["question"].lower()
    assert any(token in question_text for token in ["html", "dom", "css", "javascript", "fetch", "browser", "semantic"])
    assert "python" not in question_text


def test_evaluation_flow(monkeypatch):
    async def fake_analyze_repository(url: str):
        return {
            "repository_url": url,
            "owner": "demo",
            "repo": "demo-app",
            "full_name": "demo/demo-app",
            "description": "A demo app",
            "default_branch": "main",
            "language": "Python",
            "topics": ["api"],
            "stars": 10,
            "forks": 2,
            "visibility": "public",
            "readme_summary": "Sample project",
            "commit_hash": "abc123",
        }

    monkeypatch.setattr("backend.app.api.v1.router.analyze_repository", fake_analyze_repository)

    response = client.post(
        "/api/v1/evaluations",
        json={
            "student": {"name": "Test Student", "email": "student@example.com"},
            "repository": {"url": "https://github.com/demo/demo-app"},
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["id"]
    assert payload["current_question"]["category"]

    session_id = payload["id"]
    next_response = client.post(f"/api/v1/evaluations/{session_id}/next-question")
    assert next_response.status_code == 200, next_response.text
    next_payload = next_response.json()
    assert next_payload["question"]["question"]

    answer_response = client.post(
        f"/api/v1/evaluations/{session_id}/answer",
        json={
            "answer": "This project is organized around modules, service boundaries, request flow, and validation checks. The key components communicate through clear interfaces and the app is designed to be maintainable with stable data paths."
        },
    )
    assert answer_response.status_code == 200, answer_response.text
    answer_payload = answer_response.json()
    assert answer_payload["score"] >= 0
    assert "next_question" in answer_payload

    report_response = client.get(f"/api/v1/evaluations/{session_id}/report")
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()
    assert "report" in report
    assert "foundation_score" in report["report"]
    assert "system_understanding_score" in report["report"]
