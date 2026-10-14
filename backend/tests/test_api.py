import os
import asyncio
from pathlib import Path
import shutil

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_evaluator.db")
os.environ.setdefault("APP_ENV", "test")

from fastapi.testclient import TestClient

from backend.app.db import Base, engine
from backend.app.main import app
from backend.app.services.evaluation_service import EvaluationService
from backend.app.services.json_kb_ingestion_service import ingest_json_knowledge_base

Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_machine_learning_knowledge_base_dataset_is_indexed(tmp_path, monkeypatch):
    source_file = (
        Path(__file__).resolve().parents[2]
        / "knowledge_base"
        / "machine_learning_interview_qa(1).json"
    )
    shutil.copyfile(source_file, tmp_path / source_file.name)

    class FakeCollection:
        def __init__(self):
            self.metadata = []

        def upsert(self, documents, metadatas, ids):
            self.metadata.extend(metadatas)

    class FakeClient:
        def __init__(self):
            self.collection = FakeCollection()

        def get_or_create_collection(self, **kwargs):
            return self.collection

    client = FakeClient()
    monkeypatch.setattr(
        "backend.app.services.json_kb_ingestion_service._get_chroma_client",
        lambda _: client,
    )

    summary = ingest_json_knowledge_base(str(tmp_path), "unused")

    assert summary[source_file.name] == 61
    assert summary["total_indexed"] == 61
    assert len(client.collection.metadata) == 61
    assert all(item["domain"] == "machine_learning" for item in client.collection.metadata)


def test_interview_fallback_questions_are_distinct_for_ten_turns(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.evaluation_service.retrieve_json_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "backend.app.services.evaluation_service.retrieve_questions_for_concept",
        lambda **kwargs: [],
    )
    profile = {"detected_concepts": ["machine_learning"]}
    asked = []

    for _ in range(10):
        question = asyncio.run(EvaluationService.generate_question(profile, asked))
        asked.append(question)

    assert len(asked) == 10
    assert len({question["question"] for question in asked}) == 10
    assert asked[0]["difficulty"] == "easy"
    assert asked[2]["difficulty"] == "medium"
    assert asked[-1]["difficulty"] == "hard"
    assert all("your project" not in question["question"].lower() for question in asked)


def test_strong_answer_deepens_same_topic_at_higher_difficulty(monkeypatch):
    retrievals = []

    def retrieve_questions(**kwargs):
        retrievals.append(kwargs)
        if kwargs["concept"] != "machine_learning":
            return []
        if kwargs["difficulty"] == "easy" and kwargs["topic"] is None:
            return [{
                "question": "What is overfitting?",
                "topic": "Model Generalization",
                "difficulty": "easy",
                "evaluation_points": ["training data", "unseen data"],
            }]
        if (
            kwargs["difficulty"] == "medium"
            and kwargs["topic"] == "Model Generalization"
        ):
            return [{
                "question": "How does regularization reduce overfitting?",
                "topic": "Model Generalization",
                "difficulty": "medium",
                "evaluation_points": ["model complexity", "generalization"],
            }]
        return []

    monkeypatch.setattr(
        "backend.app.services.evaluation_service.retrieve_json_questions",
        retrieve_questions,
    )
    monkeypatch.setattr(
        "backend.app.services.evaluation_service.retrieve_questions_for_concept",
        lambda **kwargs: [],
    )
    profile = {"detected_concepts": ["machine_learning"]}

    first = asyncio.run(EvaluationService.generate_question(profile, []))
    deeper = asyncio.run(
        EvaluationService.generate_question(
            profile,
            [first],
            answers=[{"score": 85}],
        )
    )

    assert first["difficulty"] == "easy"
    assert deeper["difficulty"] == "medium"
    assert deeper["topic"] == first["topic"] == "Model Generalization"
    assert deeper["question"] == "How does regularization reduce overfitting?"
    assert any(item["difficulty"] == "medium" and item["topic"] == "Model Generalization" for item in retrievals)
    assert "project" not in deeper["question"].lower()


def test_weak_answer_revisits_same_topic_at_foundational_level(monkeypatch):
    requested = []

    def retrieve_questions(**kwargs):
        requested.append(kwargs)
        if (
            kwargs["concept"] == "machine_learning"
            and kwargs["difficulty"] == "easy"
            and kwargs["topic"] == "Model Generalization"
        ):
            return [{
                "question": "What is a training set?",
                "topic": "Model Generalization",
                "difficulty": "easy",
                "evaluation_points": ["examples", "learning"],
            }]
        return []

    monkeypatch.setattr(
        "backend.app.services.evaluation_service.retrieve_json_questions",
        retrieve_questions,
    )
    monkeypatch.setattr(
        "backend.app.services.evaluation_service.retrieve_questions_for_concept",
        lambda **kwargs: [],
    )
    prior_question = {
        "question": "What is overfitting?",
        "concept": "machine_learning",
        "difficulty": "medium",
        "topic": "Model Generalization",
    }

    follow_up = asyncio.run(
        EvaluationService.generate_question(
            {"detected_concepts": ["machine_learning"]},
            [prior_question],
            answers=[{"score": 25}],
        )
    )

    assert follow_up["difficulty"] == "easy"
    assert follow_up["topic"] == "Model Generalization"
    assert any(item["topic"] == "Model Generalization" for item in requested)


def test_detected_concepts_are_covered_before_adaptive_repeats(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.evaluation_service.retrieve_json_questions",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "backend.app.services.evaluation_service.retrieve_questions_for_concept",
        lambda **kwargs: [],
    )
    concepts = ["python", "rag", "database"]
    profile = {"detected_concepts": concepts}
    questions = []
    answers = []

    for _ in concepts:
        question = asyncio.run(
            EvaluationService.generate_question(profile, questions, answers)
        )
        questions.append(question)
        answers.append({"score": 95})

    assert [question["concept"] for question in questions] == concepts

    adaptive_question = asyncio.run(
        EvaluationService.generate_question(profile, questions, answers)
    )
    assert adaptive_question["concept"] == "database"
    assert adaptive_question["difficulty"] == "hard"


def test_report_distinguishes_detected_from_actually_tested_concepts():
    report = EvaluationService.build_report(
        {"detected_concepts": ["python", "rag", "database"]},
        [
            {"concept": "python", "score": 80},
            {"concept": "rag", "score": 45},
            {"concept": "python", "score": 90},
        ],
    )

    assert report["concepts_detected"] == ["python", "rag", "database"]
    assert report["concepts_tested"] == ["python", "rag"]
    assert report["strong_areas"] == ["python"]
    assert report["weak_areas"] == ["rag"]


def test_json_question_retrieval_filters_by_concept_difficulty_and_topic(monkeypatch):
    from backend.app.services import json_kb_ingestion_service

    class FakeCollection:
        def count(self):
            return 2

        def query(self, **kwargs):
            assert kwargs["where"] == {
                "$and": [
                    {"domain": {"$eq": "machine_learning"}},
                    {"difficulty": {"$eq": "hard"}},
                    {"topic": {"$eq": "Generalization"}},
                ]
            }
            return {
                "documents": [["Question A", "Question B"]],
                "metadatas": [[
                    {
                        "question": "Question A",
                        "topic": "Generalization",
                        "domain": "machine_learning",
                        "difficulty": "hard",
                    },
                    {
                        "question": "Question B",
                        "topic": "Other",
                        "domain": "machine_learning",
                        "difficulty": "medium",
                    },
                ]],
            }

    class FakeClient:
        def get_collection(self, _):
            return FakeCollection()

    monkeypatch.setattr(
        json_kb_ingestion_service,
        "_get_chroma_client",
        lambda _: FakeClient(),
    )

    questions = json_kb_ingestion_service.retrieve_json_questions(
        concept="machine_learning",
        difficulty="hard",
        persist_dir="unused",
        topic="Generalization",
    )

    assert [question["question"] for question in questions] == ["Question A"]


def test_related_knowledge_questions_are_combined_into_one_prompt(monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.evaluation_service.retrieve_json_questions",
        lambda **kwargs: [
            {"question": "Explain regularization.", "topic": "Machine Learning", "evaluation_points": ["overfitting"]},
            {"question": "Compare L1 and L2 penalties.", "topic": "Machine Learning", "evaluation_points": []},
        ],
    )
    monkeypatch.setattr(
        "backend.app.services.evaluation_service.retrieve_questions_for_concept",
        lambda **kwargs: [],
    )

    question = asyncio.run(
        EvaluationService.generate_question({"detected_concepts": ["machine_learning"]}, [])
    )

    assert "Explain regularization." in question["question"]
    assert "Compare L1 and L2 penalties." in question["question"]
    assert len(question["source_questions"]) == 2
    assert "overfitting" in question["expected_knowledge"]


def test_voice_transcription_endpoint_uses_backend_whisper(monkeypatch):
    monkeypatch.setattr(
        "backend.app.api.v1.router.transcribe_audio",
        lambda audio, content_type: "Transcribed interview answer",
    )

    response = client.post(
        "/api/v1/voice/transcription",
        files={"audio": ("answer.webm", b"recorded audio", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "Transcribed interview answer"}


def test_whisper_transcription_reads_audio_and_returns_text(monkeypatch):
    from backend.app.services import speech_service

    class FakeSegment:
        text = " Spoken words "

    class FakeModel:
        def transcribe(self, filename, **kwargs):
            assert Path(filename).read_bytes() == b"fake audio"
            assert kwargs["vad_filter"] is True
            return [FakeSegment()], None

    monkeypatch.setattr(speech_service, "_model", FakeModel())

    assert speech_service.transcribe_audio(b"fake audio", "audio/webm") == "Spoken words"


def test_interview_completes_after_ten_submitted_answers(monkeypatch):
    async def fake_analyze_repository(url: str):
        return {
            "repository_url": url,
            "owner": "demo",
            "repo": "ten-question-app",
            "full_name": "demo/ten-question-app",
            "description": "An interview test project",
            "default_branch": "main",
            "language": "Python",
            "topics": ["python"],
            "stars": 0,
            "forks": 0,
            "visibility": "public",
            "readme_summary": "A test project",
            "commit_hash": "abc123",
        }

    async def fake_generate_question(profile, asked, answers=None):
        question_number = len(asked) + 1
        return {
            "id": f"question-{question_number}",
            "category": "python",
            "concept": "python",
            "concept_label": "Python",
            "difficulty": (
                "easy" if question_number <= 2 else
                "medium" if question_number <= 6 else
                "hard"
            ),
            "question": f"Explain question {question_number} with an example and trade-offs.",
            "expected_knowledge": ["python", "example", "trade-offs"],
            "file_reference": None,
        }

    monkeypatch.setattr("backend.app.api.v1.router.analyze_repository", fake_analyze_repository)
    monkeypatch.setattr(EvaluationService, "generate_question", staticmethod(fake_generate_question))

    response = client.post(
        "/api/v1/evaluations",
        json={
            "student": {"name": "Ten Question Student", "email": "ten-question@example.com"},
            "repository": {"url": "https://github.com/demo/ten-question-app"},
        },
    )
    assert response.status_code == 201, response.text
    session_id = response.json()["id"]

    for question_number in range(1, 11):
        answer_response = client.post(
            f"/api/v1/evaluations/{session_id}/answer",
            json={"answer": f"Python question {question_number} works because it has a clear example and trade-offs."},
        )
        assert answer_response.status_code == 200, answer_response.text
        next_question = answer_response.json()["next_question"]
        if question_number < 10:
            assert next_question is not None
            assert next_question["question"].startswith(
                f"Explain question {question_number + 1}"
            )
        else:
            assert next_question is None

    session_response = client.get(f"/api/v1/evaluations/{session_id}")
    assert session_response.status_code == 200
    assert session_response.json()["status"] == "completed"
    assert len(session_response.json()["answers"]) == 10


def test_question_generation_uses_repo_tech_stack():
    profile = {
        "language": "Python",
        "topics": ["api", "llm", "rag", "postgres"],
        "description": "A Python RAG chatbot with FastAPI, Postgres, and LLM services.",
        "readme_summary": "FastAPI backend and React frontend with vector search and LLM orchestration.",
        "detected_concepts": ["rag", "gen_ai", "backend", "database", "frontend"],
    }

    question = asyncio.run(EvaluationService.generate_question(profile, []))
    question_text = question["question"].lower()
    assert question["concept"] == "rag"
    assert "in your project" not in question_text


def test_question_generation_stays_aligned_with_repo_stack():
    profile = {
        "language": "HTML",
        "topics": ["frontend", "css", "javascript", "web"],
        "description": "A static portfolio website built with HTML, CSS, and JavaScript.",
        "readme_summary": "Responsive landing page built with semantic HTML and browser-side interactivity.",
        "detected_concepts": ["frontend"],
    }

    question = asyncio.run(EvaluationService.generate_question(profile, []))
    question_text = question["question"].lower()
    assert question["concept"] == "frontend"
    assert "in your project" not in question_text


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
    assert "overall_score" in report["report"]
    assert "readiness" in report["report"]
    assert "strong_areas" in report["report"]
    assert "weak_areas" in report["report"]
