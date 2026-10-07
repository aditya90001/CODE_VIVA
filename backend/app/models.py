import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.app.db import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sessions = relationship("EvaluationSession", back_populates="student")


class RepositoryRecord(Base):
    __tablename__ = "repositories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String, nullable=False)
    html_url = Column(String, nullable=False)
    default_branch = Column(String, default="main")
    analysis_summary = Column(Text, nullable=True)
    commit_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sessions = relationship("EvaluationSession", back_populates="repository")


class EvaluationSession(Base):
    __tablename__ = "evaluation_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=False)
    status = Column(String, default="analysis")
    current_question = Column(JSON, nullable=True)
    questions = Column(JSON, default=list)
    answers = Column(JSON, default=list)
    profile = Column(JSON, default=dict)
    technology_map = Column(JSON, default=list)
    report = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="sessions")
    repository = relationship("RepositoryRecord", back_populates="sessions")
