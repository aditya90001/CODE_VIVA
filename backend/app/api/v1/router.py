from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend.app.config import settings
from backend.app.db import get_db
from backend.app.schemas import (
    AnswerEvaluation,
    AnswerSubmission,
    AnalysisResponse,
    EvaluationCreate,
    EvaluationSessionOut,
    QuestionResponse,
    ReportResponse,
)
from backend.app.services.evaluation_service import (
    INTERVIEW_QUESTION_COUNT,
    EvaluationService,
)
from backend.app.services.github_analyzer import GitHubRepositoryError, analyze_repository
from backend.app.services.pdf_ingestion_service import (
    get_question_bank_stats,
    ingest_knowledge_base,
)
from backend.app.services.json_kb_ingestion_service import (
    ingest_json_knowledge_base,
    get_json_kb_stats,
)
from backend.app.services.speech_service import (
    SpeechModelUnavailableError,
    SpeechTranscriptionError,
    transcribe_audio,
)

logger = logging.getLogger(__name__)
router = APIRouter()
MAX_VOICE_UPLOAD_BYTES = 20 * 1024 * 1024


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Admin: Knowledge Base Ingestion
# ---------------------------------------------------------------------------
@router.post("/admin/ingest-knowledge-base")
async def ingest_kb(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """
    Trigger re-ingestion of all PDFs + JSON KB files from the knowledge_base/ folder.
    Runs in background so the response is immediate.
    """
    def _run():
        # Ingest PDF files
        pdf_summary = ingest_knowledge_base(
            knowledge_base_dir="./knowledge_base",
            persist_dir=settings.chroma_persist_dir,
        )
        logger.info("PDF KB ingestion complete: %s", pdf_summary)
        # Ingest JSON KB files
        json_summary = ingest_json_knowledge_base(
            knowledge_base_dir="./knowledge_base",
            persist_dir=settings.chroma_persist_dir,
        )
        logger.info("JSON KB ingestion complete: %s", json_summary)

    background_tasks.add_task(_run)
    pdf_stats = get_question_bank_stats(settings.chroma_persist_dir)
    json_stats = get_json_kb_stats(settings.chroma_persist_dir)
    return {
        "message": "Ingestion started in background (PDF + JSON KB)",
        "pdf_stats": pdf_stats,
        "json_kb_stats": json_stats,
        "knowledge_base_dir": "./knowledge_base",
    }


@router.post("/admin/ingest-json-kb")
async def ingest_json_kb(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """
    Trigger ingestion of the JSON knowledge base files only.
    Rebuilds the SQLite FTS5 index from JSON knowledge-base files.
    """
    def _run():
        summary = ingest_json_knowledge_base(
            knowledge_base_dir="./knowledge_base",
            persist_dir=settings.chroma_persist_dir,
        )
        logger.info("JSON KB ingestion complete: %s", summary)

    background_tasks.add_task(_run)
    current_stats = get_json_kb_stats(settings.chroma_persist_dir)
    return {
        "message": "JSON KB ingestion started in background",
        "current_stats": current_stats,
        "files": [
            "knowledge_base/rag_knowledge_base_30_qa.json",
            "knowledge_base/python_interview_rag_qa.json",
        ],
    }


@router.get("/admin/knowledge-base-stats")
def kb_stats() -> dict[str, Any]:
    """Return current question bank statistics (PDF + JSON KB)."""
    pdf_stats = get_question_bank_stats(settings.chroma_persist_dir)
    json_stats = get_json_kb_stats(settings.chroma_persist_dir)
    return {
        "pdf_bank": pdf_stats,
        "json_kb": json_stats,
    }


@router.post("/voice/transcription")
async def voice_transcription(audio: UploadFile = File(...)) -> dict[str, str]:
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=415, detail="Upload an audio recording.")

    recording = await audio.read(MAX_VOICE_UPLOAD_BYTES + 1)
    if len(recording) > MAX_VOICE_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Recording exceeds the 20 MB limit.")
    if not recording:
        raise HTTPException(status_code=400, detail="Audio recording is empty.")

    try:
        transcript = await run_in_threadpool(
            transcribe_audio,
            recording,
            audio.content_type,
        )
    except SpeechModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SpeechTranscriptionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"text": transcript}


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------
@router.post("/evaluations", response_model=EvaluationSessionOut, status_code=status.HTTP_201_CREATED)
async def create_evaluation(payload: EvaluationCreate, db: Session = Depends(get_db)) -> EvaluationSessionOut:
    try:
        profile = await analyze_repository(
            payload.repository.url,
            github_token=settings.github_token,
        )
    except GitHubRepositoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session = EvaluationService.create_session(
        db=db,
        student_name=payload.student.name,
        email=payload.student.email,
        repository_url=payload.repository.url,
        profile=profile,
    )

    first_question = await EvaluationService.generate_question(profile, asked=[])
    session.current_question = first_question
    session.questions = [first_question]
    session.status = "in_progress"
    db.add(session)
    db.commit()
    db.refresh(session)

    return EvaluationSessionOut(
        id=session.id,
        student_id=session.student_id,
        repository_id=session.repository_id,
        status=session.status,
        profile=session.profile or {},
        current_question=first_question,
        questions=session.questions or [],
        answers=session.answers or [],
        report=session.report or {},
    )


@router.get("/evaluations/{session_id}/analysis", response_model=AnalysisResponse)
async def get_analysis(session_id: str, db: Session = Depends(get_db)) -> AnalysisResponse:
    session = EvaluationService.get_session(db, session_id)
    profile = session.profile or {}
    return AnalysisResponse(
        session_id=session.id,
        profile=profile,
        technology_map=session.technology_map or [],
        repository_url=(session.profile or {}).get("repository_url", ""),
    )


@router.post("/evaluations/{session_id}/next-question", response_model=QuestionResponse)
async def next_question(session_id: str, db: Session = Depends(get_db)) -> QuestionResponse:
    session = EvaluationService.get_session(db, session_id)
    if session.status == "completed":
        return QuestionResponse(session_id=session.id, question=session.current_question)

    if not session.current_question:
        question = await EvaluationService.generate_question(
            session.profile or {},
            session.questions or [],
            answers=session.answers or [],
        )
        session.current_question = question
        session.questions = list(session.questions or []) + [question]
        db.add(session)
        db.commit()
        db.refresh(session)

    return QuestionResponse(session_id=session.id, question=session.current_question)


@router.post("/evaluations/{session_id}/answer", response_model=AnswerEvaluation)
async def submit_answer(session_id: str, payload: AnswerSubmission, db: Session = Depends(get_db)) -> AnswerEvaluation:
    session = EvaluationService.get_session(db, session_id)
    if not session.current_question:
        raise HTTPException(status_code=400, detail="No active question for this evaluation session")

    question = session.current_question
    evaluation, score, feedback = EvaluationService.score_answer(payload.answer, question)

    answer_record = {
        "question_id": question["id"],
        "question": question["question"],
        "concept": question.get("concept", question.get("category", "")),
        "concept_label": question.get("concept_label", question.get("category", "")),
        "difficulty": question.get("difficulty", "medium"),
        "answer": payload.answer,
        "evaluation": evaluation,
        "score": score,
        "feedback": feedback,
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }

    existing_answers = list(session.answers or [])
    session.answers = existing_answers + [answer_record]
    session.questions = list(session.questions or [])

    if len(session.answers or []) >= INTERVIEW_QUESTION_COUNT:
        next_q = None
        session.status = "completed"
        session.report = EvaluationService.build_report(session.profile or {}, session.answers or [])
    else:
        next_q = await EvaluationService.generate_question(
            session.profile or {},
            session.questions or [],
            answers=session.answers or [],
        )
        session.current_question = next_q
        session.questions = list(session.questions or []) + [next_q]
        session.status = "in_progress"

    db.add(session)
    db.commit()
    db.refresh(session)

    return AnswerEvaluation(
        session_id=session.id,
        evaluation=evaluation,
        score=score,
        feedback=feedback,
        next_question=next_q,
    )


@router.get("/evaluations/{session_id}", response_model=EvaluationSessionOut)
async def get_session(session_id: str, db: Session = Depends(get_db)) -> EvaluationSessionOut:
    session = EvaluationService.get_session(db, session_id)
    return EvaluationSessionOut(
        id=session.id,
        student_id=session.student_id,
        repository_id=session.repository_id,
        status=session.status,
        profile=session.profile or {},
        current_question=session.current_question,
        questions=session.questions or [],
        answers=session.answers or [],
        report=session.report or {},
    )


@router.get("/evaluations/{session_id}/report", response_model=ReportResponse)
async def get_report(session_id: str, db: Session = Depends(get_db)) -> ReportResponse:
    session = EvaluationService.get_session(db, session_id)
    if not session.report:
        session.report = EvaluationService.build_report(session.profile or {}, session.answers or [])
        db.add(session)
        db.commit()
    return ReportResponse(session_id=session.id, report=session.report or {})
