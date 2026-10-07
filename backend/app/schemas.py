from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class StudentCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=3)


class RepositoryCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value:
            raise ValueError("Repository URL is required")
        if "github.com" not in value:
            raise ValueError("Only GitHub URLs are supported")
        return value


class EvaluationCreate(BaseModel):
    student: StudentCreate
    repository: RepositoryCreate


class QuestionPayload(BaseModel):
    id: str
    category: str
    difficulty: str
    question: str
    expected_knowledge: list[str] = Field(default_factory=list)
    file_reference: str | None = None


class AnswerSubmission(BaseModel):
    answer: str = Field(..., min_length=1)


class EvaluationSessionOut(BaseModel):
    id: str
    student_id: str
    repository_id: str
    status: str
    profile: dict[str, Any] = Field(default_factory=dict)
    current_question: QuestionPayload | None = None
    questions: list[QuestionPayload] = Field(default_factory=list)
    answers: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    session_id: str
    profile: dict[str, Any] = Field(default_factory=dict)
    technology_map: list[dict[str, Any]] = Field(default_factory=list)
    repository_url: str


class QuestionResponse(BaseModel):
    session_id: str
    question: QuestionPayload


class AnswerEvaluation(BaseModel):
    session_id: str
    evaluation: str
    score: int
    feedback: str
    next_question: QuestionPayload | None = None


class ReportResponse(BaseModel):
    session_id: str
    report: dict[str, Any]
