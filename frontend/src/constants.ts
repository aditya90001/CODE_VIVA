import { EvaluationSession, Question } from './types';

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1')
  .replace(/\/$/, '');

export interface PresetRepo {
  name: string;
  url: string;
  tag: string;
  language: string;
  description: string;
}

export const PRESET_REPOSITORIES: PresetRepo[] = [
  {
    name: 'FastAPI REST API',
    url: 'https://github.com/tiangolo/fastapi',
    tag: 'Python / Backend',
    language: 'Python',
    description: 'High performance web framework with automatic OpenAPI docs and async support.',
  },
  {
    name: 'ChromaDB Vector Store',
    url: 'https://github.com/chroma-core/chroma',
    tag: 'RAG / Vector DB',
    language: 'Python',
    description: 'The AI-native open-source embedding database for RAG pipelines.',
  },
  {
    name: 'LangChain AI Orchestration',
    url: 'https://github.com/langchain-ai/langchain',
    tag: 'GenAI / LLMs',
    language: 'Python',
    description: 'Building context-aware reasoning applications with language models.',
  },
  {
    name: 'Next.js React Framework',
    url: 'https://github.com/vercel/next.js',
    tag: 'Fullstack / React',
    language: 'TypeScript',
    description: 'React framework for server-rendered web applications.',
  },
];

export const DEMO_QUESTIONS: Question[] = [
  {
    id: 'demo-q1',
    category: 'python_decorators',
    concept: 'python_decorators',
    concept_label: 'Python Decorators & Middleware',
    difficulty: 'easy',
    question: 'In your repository, route handlers and dependency injectors frequently utilize decorators like `@app.get` and `@router`. Can you explain what a Python decorator is under the hood, how higher-order functions enable it, and why this design pattern is preferred in modern backend frameworks?',
    expected_knowledge: ['decorator', 'higher order function', 'closure', 'wrapper', 'fastapi', 'metadata'],
    topic: 'Python Programming',
  },
  {
    id: 'demo-q2',
    category: 'async_await',
    concept: 'async_await',
    concept_label: 'Asynchronous Concurrency & I/O',
    difficulty: 'medium',
    question: 'Explain the core distinction between synchronous thread blocking and asynchronous non-blocking event loops (`asyncio`). In the context of database queries or LLM API calls, what happens when you accidentally run a synchronous blocking call inside an `async def` route?',
    expected_knowledge: ['event loop', 'async', 'await', 'blocking', 'coroutine', 'gil', 'throughput'],
    topic: 'Backend & APIs',
  },
  {
    id: 'demo-q3',
    category: 'rag_architecture',
    concept: 'rag_architecture',
    concept_label: 'RAG Pipeline & Vector Search Trade-offs',
    difficulty: 'hard',
    question: 'When implementing Retrieval-Augmented Generation (RAG) with vector databases like ChromaDB, how do you handle the trade-off between chunk size and context dilution? What concrete techniques (such as reciprocal rank fusion, hybrid search, or re-ranking) mitigate hallucination when retrieved chunks contain ambiguous data?',
    expected_knowledge: ['chunking', 'embeddings', 'similarity search', 'reranking', 'hallucination', 'dense retrieval'],
    topic: 'Retrieval-Augmented Generation (RAG)',
  },
];

export const DEMO_INITIAL_SESSION: EvaluationSession = {
  id: 'demo-session-8831',
  student_id: 'student-demo',
  repository_id: 'repo-demo',
  status: 'in_progress',
  profile: {
    full_name: 'aditya/code_viva_platform',
    owner: 'aditya',
    repo: 'code_viva_platform',
    language: 'Python',
    description: 'Adaptive AI technical interviewer and GitHub codebase evaluation engine with RAG integration.',
    topics: ['fastapi', 'chromadb', 'rag', 'llm-evaluator', 'react-frontend', 'sqlite'],
    stars: 142,
    forks: 28,
    default_branch: 'main',
    commit_hash: '7a9e14c',
    detected_concepts: ['python', 'backend', 'rag', 'database', 'gen_ai', 'frontend'],
    readme_summary: 'CODE_VIVA analyzes GitHub repositories, extracts programming concepts using AST and dependency signals, indexes topic Q&As into ChromaDB, and conducts 3-stage adaptive difficulty interviews.',
    repository_url: 'https://github.com/aditya/code_viva_platform',
  },
  current_question: DEMO_QUESTIONS[0],
  questions: [DEMO_QUESTIONS[0]],
  answers: [],
  report: {},
};
