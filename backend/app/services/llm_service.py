"""
LLM Service — calls an OpenAI-compatible LLM (Groq, OpenAI, Ollama, …)
to generate grounded, repo-specific interview questions using RAG context.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Difficulty progression — questions are ordered easy → hard
# ---------------------------------------------------------------------------
DIFFICULTY_LEVELS = ["easy", "medium", "hard"]

TOPIC_DIFFICULTY_MAP = {
    # Easy — foundational understanding
    "variables": "easy",
    "functions": "easy",
    "loops": "easy",
    "lists": "easy",
    "strings": "easy",
    "imports": "easy",
    "data types": "easy",
    # Medium — applied concepts
    "api": "medium",
    "database": "medium",
    "classes": "medium",
    "error handling": "medium",
    "authentication": "medium",
    "http": "medium",
    "json": "medium",
    "async": "medium",
    "frontend": "medium",
    # Hard — design, architecture, reasoning
    "rag": "hard",
    "llm": "hard",
    "vector": "hard",
    "system design": "hard",
    "deployment": "hard",
    "docker": "hard",
    "performance": "hard",
    "trade-offs": "hard",
}


def _map_difficulty(topics: list[str]) -> str:
    """Return the hardest difficulty level present in *topics*."""
    level = 0
    for topic in topics:
        for kw, diff in TOPIC_DIFFICULTY_MAP.items():
            if kw in topic.lower():
                level = max(level, DIFFICULTY_LEVELS.index(diff))
    return DIFFICULTY_LEVELS[level]


# ---------------------------------------------------------------------------
# Build the LLM prompt
# ---------------------------------------------------------------------------
def _build_prompt(
    profile: dict[str, Any],
    context_chunks: list[dict[str, Any]],
    asked_categories: set[str],
    question_number: int,
) -> str:
    repo_name = profile.get("full_name") or profile.get("repo") or "this project"
    language = profile.get("language") or "unknown language"
    description = profile.get("description") or ""
    topics = profile.get("topics") or []

    # Determine target difficulty based on question number (ascending order)
    if question_number <= 1:
        target_difficulty = "easy"
    elif question_number == 2:
        target_difficulty = "medium"
    else:
        target_difficulty = "hard"

    # Format context chunks
    context_text = ""
    if context_chunks:
        parts = []
        for chunk in context_chunks[:6]:
            source = chunk.get("path") or chunk.get("source") or "unknown"
            parts.append(f"[{source}]\n{chunk['text']}")
        context_text = "\n\n---\n\n".join(parts)
    else:
        context_text = f"No code context available. Repo: {repo_name}, Language: {language}, Topics: {', '.join(topics)}"

    already_asked = ", ".join(asked_categories) if asked_categories else "none"

    prompt = f"""You are an expert technical interviewer evaluating a student's understanding of their own project.

## Repository Information
- Name: {repo_name}
- Language: {language}
- Description: {description}
- Topics: {", ".join(topics) if topics else "none"}

## Actual Code / README Context (retrieved from the repository)
{context_text}

## Interview State
- This is question number {question_number} in the interview.
- Categories already asked: {already_asked}
- Target difficulty for this question: **{target_difficulty}**

## Your Task
Generate ONE interview question that:
1. Is **directly based on the code or README context above** — reference specific functions, files, patterns, or design choices you see in the actual code
2. Matches the **{target_difficulty}** difficulty level
3. Tests the student's **genuine understanding** of what they built (not generic textbook knowledge)
4. Asks the student to EXPLAIN their own design decisions, WHY they wrote code a certain way, or HOW a specific part of their project works

Do NOT ask generic questions like "what is a list in Python". Instead ask things like:
- "I see you used X in file Y — why did you choose X instead of Z?"
- "Your README mentions W — explain how you implemented that in the codebase"
- "In your [specific file], you have [specific pattern] — what problem does this solve?"

Respond ONLY with valid JSON in this exact format:
{{
  "category": "a short slug like 'api-design' or 'data-flow'",
  "difficulty": "{target_difficulty}",
  "question": "the question text — must reference specific things from the repo",
  "expected_knowledge": ["keyword1", "keyword2", "keyword3", "keyword4"],
  "file_reference": "path/to/relevant/file or null"
}}"""
    return prompt


# ---------------------------------------------------------------------------
# LLM caller
# ---------------------------------------------------------------------------
async def _call_llm(prompt: str) -> str | None:
    """Call the configured LLM provider and return the raw response text."""
    api_key = settings.llm_api_key
    base_url = settings.llm_base_url or "https://api.groq.com/openai/v1"
    model = settings.llm_model or "llama3-8b-8192"

    if not api_key:
        logger.warning("LLMService: LLM_API_KEY not set — cannot generate question via LLM")
        return None

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a technical interviewer. Always respond with valid JSON only. No markdown, no explanation.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 600,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.error("LLMService: LLM call failed — %s", exc)
        return None


# ---------------------------------------------------------------------------
# Parse LLM output
# ---------------------------------------------------------------------------
def _parse_question(raw: str, question_number: int) -> dict[str, Any] | None:
    """Extract the JSON question dict from the LLM response."""
    # Strip markdown code blocks if present
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON object from partial response
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            logger.error("LLMService: could not parse JSON from LLM response: %s", raw[:200])
            return None
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            logger.error("LLMService: JSON extraction failed")
            return None

    # Validate required keys
    question_text = data.get("question") or data.get("prompt") or ""
    if not question_text:
        logger.error("LLMService: parsed JSON missing 'question' key")
        return None

    return {
        "category": data.get("category") or f"rag-q{question_number}",
        "difficulty": data.get("difficulty") or "medium",
        "question": question_text,
        "expected_knowledge": data.get("expected_knowledge") or [],
        "file_reference": data.get("file_reference"),
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
async def generate_question_with_llm(
    profile: dict[str, Any],
    context_chunks: list[dict[str, Any]],
    asked_categories: set[str],
    question_number: int,
) -> dict[str, Any] | None:
    """
    Generate a single grounded interview question via the LLM.

    Returns a question dict on success, or None if the LLM call fails
    (callers should fall back to template-based questions).
    """
    prompt = _build_prompt(profile, context_chunks, asked_categories, question_number)
    raw = await _call_llm(prompt)
    if raw is None:
        return None
    return _parse_question(raw, question_number)
