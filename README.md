# ⚡ Adaptive AI Technical Interview Evaluator (RAG-Powered)

An intelligent technical evaluation platform that analyzes GitHub repositories, detects software engineering concepts, and conducts **RAG-powered adaptive Q&A interviews** with automated AI grading.

---

## 🚀 Overview

The **Adaptive AI Technical Interview Evaluator** bridges the gap between static code reviews and interactive technical interviews. When a candidate provides a GitHub repository URL:

1. **Concept Detection**: The system analyzes the codebase (AST analysis, imports, dependencies) to detect utilized concepts (e.g., `Python`, `RAG`, `FastAPI`, `React`, `SQL`, `Machine Learning`).
2. **RAG Retrieval**: Retrieves ground-truth interview Q&As from a ChromaDB vector database indexed from topic-wise JSON files and PDFs in the `knowledge_base/` directory.
3. **Adaptive Interviewing**: Uses an LLM (Gemini / Groq / Ollama) to craft personalized interview questions tailored to the candidate's repository and chosen difficulty level (`Easy` → `Medium` → `Hard`).
4. **Automated Evaluation**: Evaluates candidate answers against granular evaluation points, generating a score (0–100), key takeaways, and constructive feedback.

---

## 🏗️ Architecture & Data Flow

```
┌────────────────────────┐      ┌─────────────────────────┐
│ Candidate GitHub Repo  │ ───► │  Concept Detector AST   │
└────────────────────────┘      └────────────┬────────────┘
                                             │ Detected Concepts
                                             ▼
┌────────────────────────┐      ┌─────────────────────────┐
│ JSON / PDF Knowledge   │ ───► │   ChromaDB Vector Store │
│ Base (knowledge_base/) │      │  (json_question_bank)   │
└────────────────────────┘      └────────────┬────────────┘
                                             │ RAG Context & Key Points
                                             ▼
                                ┌─────────────────────────┐
                                │   LLM Question Engine   │
                                └────────────┬────────────┘
                                             │ Interactive Q&A
                                             ▼
                                ┌─────────────────────────┐
                                │ Candidate Answer & LLM  │
                                │   Evaluation Service    │
                                └─────────────────────────┘
```

---

## ✨ Features

- 🔍 **Automated Concept Detection**: Inspects GitHub repository files to automatically flag frameworks, design patterns, and languages used.
- 📚 **Extensible JSON & PDF Knowledge Base**: Easily add topic-specific `.json` or `.pdf` files to expand the question bank without writing code.
- 🧠 **Vector Search Retrieval (RAG)**: ChromaDB embedding search matches repository concepts directly to relevant interview questions.
- ⚡ **Auto-Ingestion on Startup**: Automatically indexes any new `.json` files in `knowledge_base/` into ChromaDB upon server boot.
- 💯 **Granular Evaluation Engine**: Assesses answers against structured evaluation criteria, scoring completeness, technical depth, and accuracy.
- 🎨 **Modern Glassmorphism UI**: React + Vite frontend with real-time state tracking, score badges, and detailed session reports.

---

## 📁 Repository Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST API Endpoints & Routers
│   │   ├── services/
│   │   │   ├── concept_detector.py        # GitHub AST & concept detector
│   │   │   ├── json_kb_ingestion_service.py # RAG JSON Knowledge Base ingestion & vector search
│   │   │   ├── pdf_ingestion_service.py  # PDF question bank ingestion
│   │   │   ├── evaluation_service.py     # Question generation & grading logic
│   │   │   └── github_analyzer.py        # GitHub repository fetcher & validator
│   │   ├── config.py         # Application configuration & env loader
│   │   ├── db.py             # SQLAlchemy database setup (SQLite / PostgreSQL)
│   │   ├── main.py           # FastAPI entrypoint & startup auto-ingestion
│   │   └── models.py         # DB models for Sessions, Questions & Evaluations
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # React + Vite + Tailwind Single Page Application
│   ├── src/
│   │   ├── components/       # UI components (Evaluation, QuestionCard, Report)
│   │   ├── App.jsx           # Main application view & router
│   │   └── main.jsx          # React app entrypoint
│   ├── package.json
│   └── vite.config.js
│
├── knowledge_base/           # Concept-wise Question Banks (JSON & PDF)
│   ├── python_interview_rag_qa.json   # 45 Python interview Q&As
│   ├── rag_knowledge_base_30_qa.json  # 30 RAG concept Q&As
│   └── README.md                      # Guide for extending the knowledge base
│
├── .env.example              # Environment variables template
├── docker-compose.yml        # Docker compose configuration
└── README.md                 # Project documentation
```

---

## 📚 How to Extend the Knowledge Base (JSON & PDF)

You can add **new topics and concept-wise Q&A datasets** at any time. The system will automatically parse and index them into ChromaDB.

### Adding a New JSON Knowledge Base File

Create a new `.json` file inside the `knowledge_base/` directory (e.g., `knowledge_base/fastapi_interview_qa.json` or `knowledge_base/machine_learning_qa.json`).

#### JSON Schema Specification

Your JSON file should contain an array of question objects using either of the following standard formats:

```json
[
  {
    "id": 1,
    "topic": "FastAPI & Async",
    "question": "What is dependency injection in FastAPI and how does Depends() work?",
    "expected_answer": "Dependency injection allows declaring shared dependencies (DB sessions, authentication, settings) that FastAPI automatically resolves and passes to path operation functions.",
    "evaluation_points": [
      "Mentions code reuse and separation of concerns",
      "Explains usage of Depends() in endpoint signatures",
      "Discusses sub-dependencies and yield for cleanup"
    ],
    "difficulty": "medium"
  },
  {
    "id": 2,
    "topic": "FastAPI & Async",
    "question": "What is the difference between async def and plain def endpoint handlers in FastAPI?",
    "expected_answer": "async def runs on the main event loop for non-blocking awaitable tasks, while def runs on an external thread pool to prevent blocking CPU-heavy or sync I/O tasks.",
    "evaluation_points": [
      "Event loop vs thread pool execution",
      "Async await for non-blocking I/O",
      "Usage scenarios for both"
    ],
    "difficulty": "hard"
  }
]
```

#### Fields Breakdown:

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | String | **Yes** | The interview question text |
| `expected_answer` | String | **Yes** | Standard reference answer used by LLM for grading |
| `topic` or `concept` | String | Optional | Concept category (e.g., `FastAPI`, `Python`, `RAG`, `SQL`) |
| `evaluation_points` | Array[String] | Optional | Bullet points used to evaluate candidate's response |
| `difficulty` | String | Optional | `"easy"`, `"medium"`, or `"hard"` (auto-inferred if omitted) |
| `interview_tip` | String | Optional | Contextual tip for candidate evaluation |

### Triggering Knowledge Base Re-Ingestion

- **Automatic**: Simply restart the backend server (`uvicorn backend.app.main:app --reload`). All `.json` files in `knowledge_base/` are scanned and indexed on startup.
- **Manual (API)**: Make a `POST` request to `/api/v1/admin/ingest-json-kb` or `/api/v1/admin/ingest-knowledge-base`.

---

## 🛠️ Local Development Setup

### Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher & `npm`
- **Git**

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/your-username/adaptive-evaluator.git
cd adaptive-evaluator

# Create and activate Python virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy environment template
cp .env.example .env
```

#### Running the Backend Server

```bash
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
> The server will start on **`http://localhost:8000`**. Interactive Swagger API docs are available at **`http://localhost:8000/docs`**.

---

### 2. Frontend Setup

Open a second terminal window:

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
> The frontend app will start on **`http://localhost:5173`**.

---

## ⚙️ Environment Variables Configuration (`.env`)

Create a `.env` file in the root directory:

```env
# Database configuration
DATABASE_URL=sqlite:///./evaluator.db

# Environment mode
APP_ENV=development

# CORS settings
CORS_ORIGINS=http://localhost:5173

# GitHub API Token (Optional, increases rate limits for repo analysis)
GITHUB_TOKEN=your_github_personal_access_token

# LLM Provider Configuration (gemini, groq, or ollama)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash
LLM_API_KEY=your_gemini_api_key

# ChromaDB Vector Store Persistence Directory
CHROMA_ENABLED=true
CHROMA_PERSIST_DIR=./.chroma
```

---

## 🔌 API Endpoints Reference

### Evaluation Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/evaluations` | Initialize evaluation session with a GitHub repo URL |
| `GET` | `/api/v1/evaluations/{session_id}/analysis` | Fetch repository concept analysis & detected tech stack |
| `POST` | `/api/v1/evaluations/{session_id}/next-question` | Generate next RAG-grounded adaptive question |
| `POST` | `/api/v1/evaluations/{session_id}/answer` | Submit answer for current question & receive instant evaluation |
| `GET` | `/api/v1/evaluations/{session_id}` | Retrieve session state and current progress |
| `GET` | `/api/v1/evaluations/{session_id}/report` | Generate final session evaluation report & scorecard |

### Admin & Knowledge Base Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/admin/ingest-json-kb` | Trigger ingestion of all JSON KB files in `knowledge_base/` |
| `POST` | `/api/v1/admin/ingest-knowledge-base` | Ingest both JSON & PDF knowledge bases into ChromaDB |
| `GET` | `/api/v1/admin/knowledge-base-stats` | View current question bank index statistics & collection counts |
| `GET` | `/health` | Server health check endpoint |

---

## 💻 Guide for Frontend Developers

1. **Base API URL**: Set `VITE_API_BASE_URL` in your frontend environment to `http://localhost:8000/api/v1`.
2. **Session Workflow**:
   - **Step 1**: Send `POST /api/v1/evaluations` with `{ "github_url": "https://github.com/user/repo" }`. Receive `session_id`.
   - **Step 2**: Call `GET /api/v1/evaluations/{session_id}/analysis` to render detected concept badges.
   - **Step 3**: Call `POST /api/v1/evaluations/{session_id}/next-question` to display the active question.
   - **Step 4**: Call `POST /api/v1/evaluations/{session_id}/answer` with `{ "question_id": "...", "candidate_answer": "..." }` to display score & feedback.
   - **Step 5**: After 3–5 questions, call `GET /api/v1/evaluations/{session_id}/report` to present the final evaluation scorecard.

---

## 🤝 Contributing & Extending

1. Fork the repository & create your feature branch (`git checkout -b feature/new-concept-kb`).
2. Add your concept JSON files to `knowledge_base/`.
3. Verify server startup logs to confirm your new dataset is indexed into ChromaDB.
4. Open a Pull Request!

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
#   C O D E _ V I V A  
 