# ⚡ CODE_VIVA

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react" alt="React" />
  <img src="https://img.shields.io/badge/RAG-ChromaDB-FF6B6B?style=for-the-badge" alt="RAG + ChromaDB" />
  <img src="https://img.shields.io/badge/AI-Interview-Evaluator-8A2BE2?style=for-the-badge" alt="AI Interview Evaluator" />
</p>

An intelligent technical evaluation platform that analyzes GitHub repositories, detects software engineering concepts, and conducts adaptive RAG-powered technical interviews with automated AI grading.

## Overview

CODE_VIVA bridges the gap between static code reviews and live technical interviews. When a candidate submits a GitHub repository URL, the system:

1. Detects the technologies and engineering concepts used in the codebase.
2. Retrieves relevant interview questions from a vectorized knowledge base.
3. Generates adaptive questions based on repository context and selected difficulty.
4. Evaluates candidate responses using LLM-based scoring and structured feedback.

This makes it ideal for hiring pipelines, hackathon screening, technical assessments, and AI-powered learning environments.

---

## How It Works

```text
Candidate GitHub Repo
        │
        ▼
Concept Detection Engine
  ├─ AST analysis
  ├─ Imports and dependencies
  └─ Language / framework detection
        │
        ▼
RAG Knowledge Retrieval
  ├─ ChromaDB vector store
  ├─ JSON / PDF question banks
  └─ Topic-aware retrieval
        │
        ▼
Adaptive Interview Generator
  ├─ Difficulty selection
  ├─ Personalized question flow
  └─ LLM-driven questioning
        │
        ▼
Answer Evaluation Engine
  ├─ Structured grading criteria
  ├─ Score (0–100)
  └─ Feedback + takeaways
```

---

## Architecture & Data Flow

```text
┌─────────────────────────┐      ┌────────────────────────────┐
│ Candidate GitHub Repo   │ ──► │ Concept Detector AST       │
└─────────────────────────┘      └────────────┬───────────────┘
                                              │ detected concepts
                                              ▼
┌─────────────────────────┐      ┌────────────────────────────┐
│ JSON / PDF Knowledge   │ ──► │ ChromaDB Vector Store      │
│ Base (knowledge_base/) │      │ (topic-wise Q&A index)     │
└─────────────────────────┘      └────────────┬───────────────┘
                                              │ RAG context
                                              ▼
                                  ┌────────────────────────────┐
                                  │ LLM Question Engine        │
                                  └────────────┬───────────────┘
                                               │ interactive Q&A
                                               ▼
                                  ┌────────────────────────────┐
                                  │ Evaluation Service         │
                                  │ Score + Feedback           │
                                  └────────────────────────────┘
```

---

## Key Features

- 🔍 Automated concept detection from repositories
- 📚 Extensible JSON and PDF knowledge base
- 🧠 RAG-powered retrieval using ChromaDB
- ⚡ Auto-indexing of knowledge files on startup
- 💯 Granular evaluation with actionable feedback
- 🎨 Modern frontend experience for interview sessions
- 🛠️ Support for multiple LLM providers like Gemini, Groq, and Ollama

---

## Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── services/
│   │   │   ├── concept_detector.py
│   │   │   ├── json_kb_ingestion_service.py
│   │   │   ├── pdf_ingestion_service.py
│   │   │   ├── evaluation_service.py
│   │   │   └── github_analyzer.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── main.py
│   │   └── models.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
│
├── knowledge_base/
│   ├── README.md
│   ├── python_interview_rag_qa.json
│   ├── rag_knowledge_base_30_qa.json
│   └── ...
│
├── .env.example
├── docker-compose.yml
├── LICENSE
├── README.md
└── .gitignore
```

---

## Knowledge Base Extension

You can extend the system by adding new concept-wise Q&A datasets to the `knowledge_base/` directory. The application automatically scans and indexes these files at startup.

### Example JSON Schema

```json
[
  {
    "id": 1,
    "topic": "FastAPI & Async",
    "question": "How does dependency injection work in FastAPI?",
    "expected_answer": "FastAPI resolves dependencies declared in endpoint signatures using the Depends function, helping with shared logic, authentication, and clean architecture.",
    "evaluation_points": [
      "Explains dependency injection",
      "Mentions Depends() usage",
      "Discusses separation of concerns and reusability"
    ],
    "difficulty": "medium"
  }
]
```

### Supported Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | String | Yes | Interview question text |
| `expected_answer` | String | Yes | Reference answer for grading |
| `topic` or `concept` | String | Optional | Topic category |
| `evaluation_points` | Array | Optional | Evaluation criteria |
| `difficulty` | String | Optional | `easy`, `medium`, or `hard` |
| `interview_tip` | String | Optional | Extra guidance for the interview |

---

## Local Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- Git

### 1) Backend Setup

```bash
git clone https://github.com/your-username/CODE_VIVA.git
cd CODE_VIVA

python -m venv venv

# Windows PowerShell
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r backend/requirements.txt
cp .env.example .env
```

Run the backend:

```bash
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The app will be available at:

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

### 2) Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

- Web app: `http://localhost:5173`

---

## Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=sqlite:///./evaluator.db
APP_ENV=development
CORS_ORIGINS=http://localhost:5173
GITHUB_TOKEN=your_github_personal_access_token
LLM_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash
LLM_API_KEY=your_gemini_api_key
CHROMA_ENABLED=true
CHROMA_PERSIST_DIR=./.chroma
```

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/evaluations` | Start an interview evaluation session |
| `GET` | `/api/v1/evaluations/{session_id}/analysis` | Get detected repository concepts |
| `POST` | `/api/v1/evaluations/{session_id}/next-question` | Generate the next adaptive question |
| `POST` | `/api/v1/evaluations/{session_id}/answer` | Submit an answer and get scored feedback |
| `GET` | `/api/v1/evaluations/{session_id}` | View session status |
| `GET` | `/api/v1/evaluations/{session_id}/report` | Fetch final report and scorecard |
| `POST` | `/api/v1/admin/ingest-json-kb` | Re-index knowledge files |
| `GET` | `/health` | Health check |

---

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Add or update knowledge data, backend logic, or frontend features.
4. Test the workflow end-to-end.
5. Open a pull request with a clear description.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
