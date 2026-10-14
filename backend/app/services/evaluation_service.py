"""
Evaluation Service — orchestrates the interview session.

NEW APPROACH (Concept-first, real-interview style):
  1. Detect which concepts the student used in their repo
     (e.g., decorators, async/await, SQL joins, RAG, etc.)
  2. Pull concept-level questions from the PDF question bank
     indexed into ChromaDB — NOT about their code, but about
     the CONCEPTS behind their code (like a real interview)
  3. Ask questions in ascending difficulty: easy → medium → hard
  4. Fall back to built-in question templates if no PDFs uploaded yet

Example:
  Student used @router.get() → detect "python_decorators"
  → Ask: "What is a decorator in Python and why do we use them?"
  (Not: "What does line 12 of your routes.py do?")
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import EvaluationSession, RepositoryRecord, Student
from backend.app.services.concept_detector import detect_concepts, get_concept_label
from backend.app.services.pdf_ingestion_service import retrieve_questions_for_concept
from backend.app.services.json_kb_ingestion_service import retrieve_json_questions

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Built-in fallback question bank
# Used when no PDFs have been uploaded to knowledge_base/ yet.
# Concept-level questions — NOT code-specific.
# ---------------------------------------------------------------------------
BUILTIN_QUESTIONS: dict[str, list[dict[str, Any]]] = {
    "python": [
        {"difficulty": "easy", "question": "What is a decorator in Python? Explain in simple terms what it does and give one real-world example of where you've seen or used a decorator."},
        {"difficulty": "medium", "question": "What is the difference between synchronous and asynchronous code? Why would you use async/await in a Python web server?"},
        {"difficulty": "hard", "question": "What is the difference between composition and inheritance? When would you prefer composition over inheritance and why?"},
    ],
    "machine_learning": [
        {"difficulty": "easy", "question": "What is the difference between supervised and unsupervised learning? Provide a simple real-world example of each."},
        {"difficulty": "medium", "question": "Explain how a Random Forest classifier works. Why is it generally more robust than a single Decision Tree?"},
        {"difficulty": "hard", "question": "What is overfitting and what are three concrete techniques you would use to prevent it in a machine learning model?"},
    ],
    "deep_learning": [
        {"difficulty": "easy", "question": "What is a neural network? Explain the concepts of layers, weights, and biases in simple terms."},
        {"difficulty": "medium", "question": "What is the purpose of an activation function like ReLU or Sigmoid? What happens if you build a deep neural network without any non-linear activation functions?"},
        {"difficulty": "hard", "question": "Explain the concept of backpropagation. How does the network use the loss function to update its weights during training?"},
    ],
    "backend": [
        {"difficulty": "easy", "question": "Explain what HTTP is and how a browser communicates with a server. What is the difference between a GET request and a POST request?"},
        {"difficulty": "medium", "question": "What are RESTful APIs? Explain the standard conventions for structuring endpoints and using HTTP status codes."},
        {"difficulty": "hard", "question": "What is the Depends() system in FastAPI (or dependency injection in general)? How does dependency injection help you write cleaner, more testable code?"},
    ],
    "database": [
        {"difficulty": "easy", "question": "What is the difference between a database and a file for storing data? When would you prefer a SQL database over a plain JSON file?"},
        {"difficulty": "medium", "question": "Explain what a PRIMARY KEY and a FOREIGN KEY are in a relational database. Why do they matter for data integrity?"},
        {"difficulty": "hard", "question": "What does a JOIN do in SQL? Explain the difference between INNER JOIN and LEFT JOIN using a simple example with two tables."},
    ],
    "rag": [
        {"difficulty": "easy", "question": "What is RAG (Retrieval-Augmented Generation)? In simple terms, why do we need retrieval — can't the LLM just answer from memory?"},
        {"difficulty": "medium", "question": "What is chunking in a RAG pipeline? How do you decide on chunk size, and what problems occur if chunks are too large or too small?"},
        {"difficulty": "hard", "question": "What is the difference between dense retrieval (vector search) and sparse retrieval (BM25/keyword search)? When would you combine both, and what is this called?"},
    ],
    "gen_ai": [
        {"difficulty": "easy", "question": "What is a Large Language Model (LLM)? Explain what 'temperature' controls in an LLM and when you'd set it high vs low."},
        {"difficulty": "medium", "question": "What is prompt engineering? Explain the difference between zero-shot, one-shot, and few-shot prompting with examples."},
        {"difficulty": "hard", "question": "What is hallucination in LLMs? What are three concrete techniques you can use to reduce hallucinations in a production system?"},
    ],
    "frontend": [
        {"difficulty": "easy", "question": "What is the difference between props and state in React? When would a component use one vs the other?"},
        {"difficulty": "medium", "question": "What does the useEffect hook do? Explain the dependency array — what happens when it is empty, when it has values, and when it is omitted?"},
        {"difficulty": "hard", "question": "What is the virtual DOM in React and why does it exist? How does React's reconciliation algorithm decide what to re-render?"},
    ],
    "devops": [
        {"difficulty": "easy", "question": "What is Docker and what problem does it solve? Explain the difference between a Docker image and a Docker container."},
        {"difficulty": "medium", "question": "What is docker-compose and when would you use it instead of running a single container? Explain with an example of a web app + database setup."},
        {"difficulty": "hard", "question": "What is the difference between CMD and ENTRYPOINT in a Dockerfile? How would you write a multi-stage Dockerfile to reduce the final image size?"},
    ],
}

# Planned progression; answer quality can accelerate or revisit these levels.
DIFFICULTY_ORDER = ["easy", "medium", "hard"]
INTERVIEW_QUESTION_COUNT = 10
FALLBACK_QUESTION_PROMPTS = {
    "easy": [
        "In your own words, what is {concept}, and what basic problem does it address?",
        "Explain the central idea behind {concept} as if you were introducing it to a beginner.",
        "What are the most important terms or building blocks someone should understand before studying {concept}?",
    ],
    "medium": [
        "How do the main principles of {concept} relate to one another, and why does that relationship matter?",
        "How is {concept} different from a closely related idea? When is each idea useful?",
        "What assumptions does {concept} rely on, and what changes when those assumptions do not hold?",
    ],
    "hard": [
        "What are the fundamental trade-offs and limitations of {concept}, and how do they affect when it is appropriate?",
        "Under what conditions can the central idea of {concept} fail or produce misleading results? Explain why.",
        "Compare two important approaches within {concept}. What principles explain their different strengths and weaknesses?",
        "What deeper principle connects {concept} to another area of computer science, and where does that connection break down?",
    ],
}


class EvaluationService:

    @staticmethod
    def extract_tech_stack(profile: dict[str, Any]) -> list[str]:
        """Legacy helper — kept for compatibility with existing code."""
        source = " ".join(
            [
                str(profile.get("language") or ""),
                " ".join(profile.get("topics") or []),
                str(profile.get("description") or ""),
                str(profile.get("readme_summary") or ""),
            ]
        ).lower()

        signals = {
            "python": ["python"], "javascript": ["javascript", "js"],
            "react": ["react"], "fastapi": ["fastapi"],
            "database": ["postgres", "mysql", "sql"], "llm": ["llm", "openai", "groq"],
            "rag": ["rag", "vector", "embedding"], "docker": ["docker"],
        }
        detected = [label for label, matches in signals.items() if any(m in source for m in matches)]
        return detected[:8] if detected else ["api", "backend"]

    @staticmethod
    def create_session(
        db: Session,
        student_name: str,
        email: str,
        repository_url: str,
        profile: dict[str, Any],
    ) -> EvaluationSession:
        student = db.query(Student).filter(Student.email == email).first()
        if not student:
            student = Student(name=student_name, email=email)
            db.add(student)
            db.flush()

        repository = db.query(RepositoryRecord).filter(RepositoryRecord.html_url == repository_url).first()
        if not repository:
            repository = RepositoryRecord(
                full_name=profile.get("full_name", repository_url),
                html_url=repository_url,
                default_branch=profile.get("default_branch", "main"),
                analysis_summary=profile.get("description", ""),
                commit_hash=profile.get("commit_hash"),
            )
            db.add(repository)
            db.flush()

        # Detect concepts at session creation time and store in profile
        detected = detect_concepts(profile)
        profile["detected_concepts"] = detected
        logger.info("Session created — detected concepts: %s", detected)

        session = EvaluationSession(
            student_id=student.id,
            repository_id=repository.id,
            status="analysis",
            profile=profile,
            technology_map=[
                {
                    "name": get_concept_label(c),
                    "concept_key": c,
                    "importance": 5,
                    "concepts": ["understanding", "application", "trade-offs"],
                }
                for c in detected[:6]
            ],
            questions=[],
            answers=[],
            report={},
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_session(db: Session, session_id: str) -> EvaluationSession:
        session = db.query(EvaluationSession).filter(EvaluationSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Evaluation session not found")
        return session

    @staticmethod
    async def generate_question(
        profile: dict[str, Any],
        asked: list[dict[str, Any]] | None = None,
        answers: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Select a fundamental question from the knowledge base and adapt its
        concept and difficulty using the previous answer's score.
        """
        asked_list = asked or []
        answer_list = answers or []
        asked_questions = {
            source_question
            for item in asked_list
            for source_question in [item.get("question", ""), *item.get("source_questions", [])]
            if source_question
        }
        question_number = len(asked_list) + 1

        planned_difficulty = (
            "easy" if question_number <= 2 else
            "medium" if question_number <= 6 else
            "hard"
        )
        planned_level = DIFFICULTY_ORDER.index(planned_difficulty)

        # Use repo analysis only to choose a subject area, never to ask about its code.
        detected_concepts: list[str] = profile.get("detected_concepts") or detect_concepts(profile)
        if not detected_concepts:
            detected_concepts = ["python"]

        asked_concepts = {
            item.get("concept", item.get("category"))
            for item in asked_list
            if item.get("concept", item.get("category"))
        }
        uncovered_concepts = [
            concept for concept in detected_concepts if concept not in asked_concepts
        ]

        target_topic: str | None = None
        if uncovered_concepts:
            target_concept = uncovered_concepts[0]
            target_level = planned_level
        elif asked_list and answer_list:
            previous_question = asked_list[-1]
            previous_answer = answer_list[-1]
            previous_level = DIFFICULTY_ORDER.index(
                previous_question.get("difficulty", "easy")
                if previous_question.get("difficulty") in DIFFICULTY_ORDER
                else "easy"
            )
            previous_score = previous_answer.get("score", 0)
            previous_concept = previous_question.get(
                "concept", previous_question.get("category", "")
            )

            if previous_score >= 70:
                target_concept = previous_concept or detected_concepts[
                    (question_number - 1) % len(detected_concepts)
                ]
                target_topic = previous_question.get("topic")
                target_level = max(planned_level, min(previous_level + 1, len(DIFFICULTY_ORDER) - 1))
            elif previous_score < 40:
                target_concept = previous_concept or detected_concepts[
                    (question_number - 1) % len(detected_concepts)
                ]
                target_topic = previous_question.get("topic")
                target_level = max(0, min(planned_level, previous_level - 1))
            else:
                target_concept = detected_concepts[
                    (question_number - 1) % len(detected_concepts)
                ]
                target_level = planned_level
        else:
            target_concept = detected_concepts[(question_number - 1) % len(detected_concepts)]
            target_level = planned_level

        target_difficulty = DIFFICULTY_ORDER[target_level]

        concept_label = get_concept_label(target_concept)
        logger.info(
            "Generating Q%d — concept: %s (%s), difficulty: %s",
            question_number,
            target_concept,
            concept_label,
            target_difficulty,
        )

        # 1. Try questions from the supplied JSON knowledge base at the target
        # topic and level, then broaden only when that subset is exhausted.
        json_questions: list[dict[str, Any]] = []
        topic_filters = [target_topic, None] if target_topic else [None]
        for topic_filter in topic_filters:
            json_questions = retrieve_json_questions(
                concept=target_concept,
                difficulty=target_difficulty,
                persist_dir=settings.chroma_persist_dir,
                exclude_questions=list(asked_questions),
                n=5,
                topic=topic_filter,
            )
            if json_questions:
                break

        if json_questions:
            chosen = json_questions[0]
            related = next(
                (
                    candidate
                    for candidate in json_questions[1:]
                    if candidate.get("topic") == chosen.get("topic")
                    and candidate.get("question") not in asked_questions
                ),
                None,
            )
            source_questions = [chosen["question"]]
            question_text = chosen["question"]
            if related:
                source_questions.append(related["question"])
                question_text = (
                    "Answer both fundamental parts:\n"
                    f"1. {chosen['question']}\n"
                    f"2. {related['question']}\n"
                    "Then explain how the ideas relate, using a simple example."
                )
            logger.info("Using JSON KB question: %s...", chosen["question"][:60])
            return {
                "id": str(uuid.uuid4()),
                "category": target_concept,
                "concept": target_concept,
                "concept_label": concept_label,
                "difficulty": chosen.get("difficulty", target_difficulty),
                "question": question_text,
                "source_questions": source_questions,
                "expected_knowledge": [
                    target_concept.replace("_", " "),
                    *chosen.get("evaluation_points", []),
                ],
                "file_reference": None,
                "source": "json_kb",
                "topic": chosen.get("topic", ""),
            }

        # 2. Try the PDF question bank, preserving the selected topic when possible.
        pdf_questions: list[dict[str, Any]] = []
        for topic_filter in ([target_topic, None] if target_topic else [None]):
            pdf_questions = retrieve_questions_for_concept(
                concept=topic_filter or target_concept,
                difficulty=target_difficulty,
                persist_dir=settings.chroma_persist_dir,
                exclude_questions=list(asked_questions),
                n=3,
            )
            if pdf_questions:
                break

        if pdf_questions:
            chosen = pdf_questions[0]
            related = next(
                (
                    candidate
                    for candidate in pdf_questions[1:]
                    if candidate.get("topic") == chosen.get("topic")
                    and candidate.get("question") not in asked_questions
                ),
                None,
            )
            source_questions = [chosen["question"]]
            question_text = chosen["question"]
            if related:
                source_questions.append(related["question"])
                question_text = (
                    "Answer both fundamental parts:\n"
                    f"1. {chosen['question']}\n"
                    f"2. {related['question']}\n"
                    "Then explain how the ideas relate, using a simple example."
                )
            logger.info("Using PDF bank question: %s...", chosen["question"][:60])
            return {
                "id": str(uuid.uuid4()),
                "category": target_concept,
                "concept": target_concept,
                "concept_label": concept_label,
                "difficulty": chosen.get("difficulty", target_difficulty),
                "question": question_text,
                "source_questions": source_questions,
                "expected_knowledge": [target_concept.replace("_", " ")],
                "file_reference": None,
                "source": "pdf_bank",
                "topic": chosen.get("topic", ""),
            }

        # 3. Fall back to built-in fundamental questions for this concept.
        builtin = BUILTIN_QUESTIONS.get(target_concept, [])
        candidates = [
            question for question in builtin
            if question["difficulty"] == target_difficulty
            and question["question"] not in asked_questions
        ]
        if candidates:
            chosen = candidates[0]
            logger.info("Using built-in fundamental question for %s", target_concept)
            return {
                "id": str(uuid.uuid4()),
                "category": target_concept,
                "concept": target_concept,
                "concept_label": concept_label,
                "difficulty": chosen["difficulty"],
                "question": chosen["question"],
                "source_questions": [chosen["question"]],
                "expected_knowledge": [target_concept.replace("_", " ")],
                "file_reference": None,
                "source": "builtin",
            }

        # 4. Last resort: ask about the fundamentals of the detected concept,
        # not how the candidate implemented it in their repository.
        fallback_candidates = [
            prompt.format(concept=concept_label)
            for prompt in FALLBACK_QUESTION_PROMPTS[target_difficulty]
        ]
        fallback_question = next(
            (prompt for prompt in fallback_candidates if prompt not in asked_questions),
            fallback_candidates[0],
        )
        return {
            "id": str(uuid.uuid4()),
            "category": target_concept,
            "concept": target_concept,
            "concept_label": concept_label,
            "difficulty": target_difficulty,
            "question": fallback_question,
            "source_questions": [fallback_question],
            "expected_knowledge": [target_concept.replace("_", " "), "fundamentals"],
            "file_reference": None,
            "source": "fallback",
            "topic": target_topic or "",
        }

    @staticmethod
    def score_answer(answer: str, question: dict[str, Any]) -> tuple[str, int, str]:
        clean = answer.lower()
        concept_keywords = []
        for concept in question.get("expected_knowledge", []):
            concept_keywords.extend([concept.lower(), concept.lower().replace(" ", "")])

        matched = sum(1 for keyword in concept_keywords if keyword in clean)

        reasoning_markers = [
            "because", "therefore", "trade", "if", "when", "first",
            "then", "instead", "without", "this helps", "fallback",
            "design", "example", "means", "allows", "prevents",
        ]
        reasoning_hits = sum(1 for marker in reasoning_markers if marker in clean)

        score = min(100, 20 + matched * 16 + reasoning_hits * 6)

        if len(clean.split()) < 15:
            score = min(score, 35)

        concept_label = question.get("concept_label") or question.get("category") or "this concept"

        if score < 40:
            return (
                "weak",
                score,
                f"The answer doesn't yet show enough understanding of {concept_label}. "
                "Focus on explaining what it is, why it exists, and how it works with a concrete example.",
            )
        if score < 70:
            return (
                "partial",
                score,
                f"You have some understanding of {concept_label}, but the explanation needs more depth. "
                "Try to explain the why, not just the what — add trade-offs or a concrete example.",
            )
        if score < 90:
            return (
                "correct",
                score,
                f"Good understanding of {concept_label}. To strengthen your answer further, "
                "discuss edge cases, trade-offs, or how you've applied it in practice.",
            )
        return (
            "strong",
            score,
            f"Excellent! You demonstrated strong conceptual understanding of {concept_label} "
            "with clear reasoning and practical insight.",
        )

    @staticmethod
    def build_report(profile: dict[str, Any], answers: list[dict[str, Any]]) -> dict[str, Any]:
        scores = [item.get("score", 0) for item in answers]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

        # Identify strong and weak concepts
        strong = [
            a.get("concept_label") or a.get("concept") or a.get("category", "")
            for a in answers
            if a.get("score", 0) >= 70
        ]
        weak = [
            a.get("concept_label") or a.get("concept") or a.get("category", "")
            for a in answers
            if a.get("score", 0) < 70
        ]

        detected_concepts: list[str] = profile.get("detected_concepts") or []
        tested_concepts = list(dict.fromkeys(
            answer.get("concept") or answer.get("category") or ""
            for answer in answers
            if answer.get("concept") or answer.get("category")
        ))

        if avg_score >= 80:
            readiness = "Ready for technical interview"
            mentor_note = "Strong conceptual foundation. The student demonstrates genuine understanding of the technologies they used."
        elif avg_score >= 60:
            readiness = "Needs some preparation"
            mentor_note = "The student knows the basics but needs to deepen understanding of core concepts. Focus on the weak areas before the next interview."
        else:
            readiness = "Needs significant preparation"
            mentor_note = "The student needs to revisit fundamental concepts before attempting a technical interview. Recommend focused study on the weak areas."

        return {
            "overall_score": avg_score,
            "readiness": readiness,
            "concepts_detected": detected_concepts,
            "concepts_tested": tested_concepts,
            "strong_areas": list(dict.fromkeys(strong)),
            "weak_areas": list(dict.fromkeys(weak)),
            "mentor_note": mentor_note,
            "notable_answers": answers,
        }
