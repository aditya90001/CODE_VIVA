import { FormEvent, useEffect, useState } from 'react';

type Question = {
  id: string;
  category: string;
  difficulty: string;
  question: string;
  expected_knowledge: string[];
  file_reference?: string | null;
};

type Session = {
  id: string;
  student_id: string;
  repository_id: string;
  status: string;
  profile: Record<string, unknown>;
  current_question?: Question | null;
  questions: Question[];
  answers: Record<string, unknown>[];
  report: Record<string, unknown>;
};

const API_BASE = 'http://localhost:8000/api/v1';

export default function App() {
  const [name, setName] = useState('Ada Student');
  const [email, setEmail] = useState('ada@example.com');
  const [repoUrl, setRepoUrl] = useState('https://github.com/microsoft/vscode');
  const [session, setSession] = useState<Session | null>(null);
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [answer, setAnswer] = useState('');
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const startEvaluation = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE}/evaluations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student: { name, email },
          repository: { url: repoUrl },
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? 'Unable to create evaluation');
      }

      setSession(data);
      setCurrentQuestion(data.current_question ?? null);
      setAnalysis(data.profile ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!session?.id) {
      return;
    }

    const loadAnalysis = async () => {
      const response = await fetch(`${API_BASE}/evaluations/${session.id}/analysis`);
      const data = await response.json();
      setAnalysis(data.profile ?? null);
    };

    void loadAnalysis();
  }, [session?.id]);

  const submitAnswer = async () => {
    if (!session?.id || !answer.trim()) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE}/evaluations/${session.id}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? 'Answer submission failed');
      }

      setCurrentQuestion(data.next_question ?? null);
      setAnswer('');
      if (data.next_question) {
        setSession((prev) => prev ? { ...prev, current_question: data.next_question } : prev);
      } else {
        const reportResponse = await fetch(`${API_BASE}/evaluations/${session.id}/report`);
        const reportData = await reportResponse.json();
        setReport(reportData.report ?? {});
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>Adaptive GitHub Project Evaluator</h1>
        <p>Repository-based adaptive technical interviews</p>
      </header>

      {!session && (
        <form className="panel" onSubmit={startEvaluation}>
          <h2>Start Evaluation</h2>
          <label>
            Student name
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            GitHub repository URL
            <input value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} />
          </label>
          <button disabled={loading} type="submit">
            {loading ? 'Analyzing...' : 'Start interview'}
          </button>
        </form>
      )}

      {error && <div className="error-box">{error}</div>}

      {session && (
        <div className="layout">
          <aside className="panel">
            <h2>Analysis</h2>
            <p>
              <strong>Session:</strong> {session.id}
            </p>
            <p>
              <strong>Status:</strong> {session.status}
            </p>
            <div>
              <h3>Repository profile</h3>
              <pre>{JSON.stringify(analysis ?? session.profile ?? {}, null, 2)}</pre>
            </div>
          </aside>

          <main className="panel">
            <h2>Interview</h2>
            {report ? (
              <div className="report-box">
                <h3>Final report</h3>
                <pre>{JSON.stringify(report, null, 2)}</pre>
              </div>
            ) : currentQuestion ? (
              <>
                <div className="question-meta">
                  <span>{currentQuestion.category}</span>
                  <span>{currentQuestion.difficulty}</span>
                </div>
                <h3>{currentQuestion.question}</h3>
                {currentQuestion.file_reference && <p>Reference: {currentQuestion.file_reference}</p>}
                <textarea
                  rows={7}
                  value={answer}
                  onChange={(event) => setAnswer(event.target.value)}
                  placeholder="Type your answer here..."
                />
                <button onClick={submitAnswer} disabled={loading || !answer.trim()}>
                  {loading ? 'Submitting...' : 'Submit answer'}
                </button>
              </>
            ) : (
              <p>Interview complete.</p>
            )}
          </main>
        </div>
      )}
    </div>
  );
}
