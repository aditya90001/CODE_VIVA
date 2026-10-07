# 📚 Knowledge Base — Concept-wise Question Bank

This directory contains the **concept-wise question banks** used by the RAG retrieval engine.
The system automatically discovers, parses, and indexes **all JSON and PDF files** dropped into this directory into ChromaDB (`json_question_bank` collection).

When a candidate submits a GitHub repository, the system detects which concepts were used in their code and pulls the most relevant, ground-truth questions from your bank.

---

## 📁 How to Add New Concept Q&As

### Option 1: Adding JSON Knowledge Base Files (Recommended)

Create a `.json` file inside `knowledge_base/` named after your topic/domain (e.g., `fastapi_qa.json`, `langchain_qa.json`, `sql_qa.json`).

#### Standard JSON Format:

```json
[
  {
    "id": 1,
    "topic": "FastAPI",
    "question": "What is dependency injection in FastAPI and how does Depends() work?",
    "expected_answer": "Dependency injection allows declaring shared dependencies (DB sessions, auth, settings) that FastAPI automatically resolves.",
    "evaluation_points": [
      "Mentions code reuse and separation of concerns",
      "Explains Depends() usage in path parameters",
      "Mentions yield for context managers"
    ],
    "difficulty": "medium"
  },
  {
    "id": 2,
    "topic": "FastAPI",
    "question": "What is the difference between async def and plain def endpoint handlers in FastAPI?",
    "expected_answer": "async def runs on the main event loop, whereas plain def runs on an external thread pool.",
    "evaluation_points": [
      "Event loop vs thread pool execution",
      "Non-blocking I/O explanation"
    ],
    "difficulty": "hard"
  }
]
```

---

### Option 2: Adding PDF Question Files

Drop any PDF file into this folder (e.g., `machine_learning.pdf`, `react.pdf`).
The system extracts text and infers difficulty from `[Easy]`, `[Medium]`, `[Hard]` tags inside the PDF.

---

## 🔄 How Auto-Ingestion Works

1. **On Server Startup**: The FastAPI server automatically scans all `.json` and `.pdf` files in `knowledge_base/` and indexes them into ChromaDB.
2. **Via API Call**: You can manually trigger re-indexing without restarting the server by sending a request to:
   - `POST /api/v1/admin/ingest-json-kb`
   - `POST /api/v1/admin/ingest-knowledge-base`
