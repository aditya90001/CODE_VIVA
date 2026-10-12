import React, { useState, useEffect, FormEvent } from 'react';
import { Navbar } from './components/Navbar';
import { SetupCard } from './components/SetupCard';
import { AnalysisPanel } from './components/AnalysisPanel';
import { InterviewRoom } from './components/InterviewRoom';
import { ScorecardView } from './components/ScorecardView';
import { KBStatsModal } from './components/KBStatsModal';
import {
  API_BASE,
  PRESET_REPOSITORIES,
  DEMO_QUESTIONS,
  DEMO_INITIAL_SESSION,
  PresetRepo,
} from './constants';
import {
  EvaluationSession,
  Question,
  AnswerRecord,
  FinalReport,
  RepoProfile,
  TechnologyMapItem,
} from './types';
import { AlertTriangle, Sparkles } from 'lucide-react';

export default function App() {
  const [name, setName] = useState('Alex Rivera');
  const [email, setEmail] = useState('alex.rivera@dev.io');
  const [repoUrl, setRepoUrl] = useState('https://github.com/tiangolo/fastapi');

  const [session, setSession] = useState<EvaluationSession | null>(null);
  const [analysis, setAnalysis] = useState<RepoProfile | null>(null);
  const [technologyMap, setTechnologyMap] = useState<TechnologyMapItem[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [answers, setAnswers] = useState<AnswerRecord[]>([]);
  const [report, setReport] = useState<FinalReport | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [demoMode, setDemoMode] = useState<boolean>(false);
  const [kbModalOpen, setKbModalOpen] = useState(false);
  const [demoStep, setDemoStep] = useState(0);

  // Check backend health on initial mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('http://localhost:8000/health', {
          signal: AbortSignal.timeout(2500),
        });
        if (res.ok) {
          setBackendOnline(true);
        } else {
          setBackendOnline(false);
        }
      } catch (err) {
        setBackendOnline(false);
      }
    };

    void checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectPreset = (preset: PresetRepo) => {
    setRepoUrl(preset.url);
  };

  const handleToggleDemoMode = () => {
    setDemoMode((prev) => !prev);
    setError('');
  };

  const handleResetSession = () => {
    setSession(null);
    setAnalysis(null);
    setTechnologyMap([]);
    setCurrentQuestion(null);
    setAnswers([]);
    setReport(null);
    setError('');
    setDemoStep(0);
  };

  // Start Evaluation Flow
  const startEvaluation = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !repoUrl.trim()) return;

    setLoading(true);
    setError('');

    // --- Demo Mode Simulation ---
    if (demoMode) {
      setTimeout(() => {
        const repoSlug = repoUrl.replace('https://github.com/', '');
        const [owner, repoName] = repoSlug.split('/');

        const demoSession: EvaluationSession = {
          ...DEMO_INITIAL_SESSION,
          id: `demo-${Math.random().toString(36).slice(2, 8)}`,
          profile: {
            ...DEMO_INITIAL_SESSION.profile,
            full_name: repoSlug || 'custom/project',
            owner: owner || 'developer',
            repo: repoName || 'project',
            repository_url: repoUrl,
          },
        };

        setSession(demoSession);
        setAnalysis(demoSession.profile);
        setCurrentQuestion(DEMO_QUESTIONS[0]);
        setAnswers([]);
        setReport(null);
        setDemoStep(0);
        setLoading(false);
      }, 900);
      return;
    }

    // --- Live Backend Flow ---
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
        throw new Error(data.detail || 'Unable to analyze repository and initiate evaluation');
      }

      setSession(data);
      setCurrentQuestion(data.current_question || null);
      setAnalysis(data.profile || null);
      setAnswers(data.answers || []);
      setReport(data.report && Object.keys(data.report).length > 0 ? (data.report as FinalReport) : null);

      // Load technology map & analysis details
      try {
        const analysisRes = await fetch(`${API_BASE}/evaluations/${data.id}/analysis`);
        if (analysisRes.ok) {
          const analysisData = await analysisRes.json();
          if (analysisData.technology_map) {
            setTechnologyMap(analysisData.technology_map);
          }
        }
      } catch (e) {
        // Non-blocking
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unexpected network error';
      setError(msg);
      // If backend was unreachable, offer one-click demo
      if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || !backendOnline) {
        setError(
          'Could not connect to FastAPI server at http://localhost:8000. Start the backend with `uvicorn backend.app.main:app` or switch to Sandbox Demo Mode above!'
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // Submit Answer Flow
  const submitAnswer = async (answerText: string) => {
    if (!answerText.trim() || !session) return;

    setLoading(true);
    setError('');

    // --- Demo Mode Submission ---
    if (demoMode) {
      setTimeout(() => {
        const clean = answerText.toLowerCase();
        const expected = currentQuestion?.expected_knowledge || [];
        const matches = expected.filter((k) => clean.includes(k.toLowerCase())).length;

        const reasoningMarkers = [
          'because', 'therefore', 'trade', 'if', 'when', 'first',
          'instead', 'without', 'design', 'example', 'throughput',
        ];
        const reasoningHits = reasoningMarkers.filter((m) => clean.includes(m)).length;

        let score = Math.min(96, Math.max(45, 30 + matches * 14 + reasoningHits * 6));
        if (clean.split(/\s+/).length < 15) {
          score = Math.min(score, 45);
        }

        const evaluation = score >= 85 ? 'strong' : score >= 70 ? 'correct' : score >= 50 ? 'partial' : 'weak';
        const feedback =
          evaluation === 'strong'
            ? `Superb conceptual clarity on ${currentQuestion?.concept_label || 'this architecture'}. You articulated trade-offs and underlying mechanics cleanly.`
            : evaluation === 'correct'
            ? `Solid understanding of ${currentQuestion?.concept_label || 'the concept'}. Mentioning specific edge cases or real-world failure modes would elevate this to an architectural answer.`
            : `Partial conceptual grasp. Strengthen your explanation by discussing why this pattern was chosen over alternatives and how it handles concurrency/scaling.`;

        const newAnswerRecord: AnswerRecord = {
          question_id: currentQuestion?.id || `q-${demoStep}`,
          question: currentQuestion?.question || '',
          concept: currentQuestion?.concept,
          concept_label: currentQuestion?.concept_label,
          difficulty: currentQuestion?.difficulty || 'medium',
          answer: answerText,
          evaluation,
          score,
          feedback,
          answered_at: new Date().toISOString(),
        };

        const updatedAnswers = [...answers, newAnswerRecord];
        setAnswers(updatedAnswers);

        const nextStep = demoStep + 1;
        if (nextStep < DEMO_QUESTIONS.length) {
          setDemoStep(nextStep);
          setCurrentQuestion(DEMO_QUESTIONS[nextStep]);
        } else {
          // Final Report
          const totalScore = Math.round(
            updatedAnswers.reduce((sum, a) => sum + a.score, 0) / updatedAnswers.length
          );
          const finalReportData: FinalReport = {
            overall_score: totalScore,
            readiness:
              totalScore >= 75
                ? 'Ready for Senior Technical Interview'
                : totalScore >= 60
                ? 'Needs Moderate Preparation'
                : 'Needs Fundamental Preparation',
            concepts_tested: [
              'Python Decorators & Higher Order Functions',
              'Asynchronous Concurrency & Event Loops',
              'Vector Retrieval & RAG Pipeline Trade-offs',
            ],
            strong_areas:
              totalScore >= 70
                ? ['Framework Architecture', 'Event Loop Understanding', 'Modular Design']
                : ['Foundational Syntax', 'Code Structure'],
            weak_areas:
              totalScore >= 80
                ? ['Vector Distance Edge Cases']
                : ['Context Dilution & Retrieval Re-ranking', 'Async Thread Safety'],
            mentor_note:
              totalScore >= 75
                ? 'Strong candidate. Demonstrates genuine insight into both design trade-offs and concrete implementation details of their codebase.'
                : 'Good initial footing, but needs deeper familiarity with distributed trade-offs and non-blocking I/O implications.',
            notable_answers: updatedAnswers,
          };
          setReport(finalReportData);
          setCurrentQuestion(null);
        }
        setLoading(false);
      }, 850);
      return;
    }

    // --- Live Backend Answer Submission ---
    try {
      const response = await fetch(`${API_BASE}/evaluations/${session.id}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer: answerText }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Answer submission failed');
      }

      // Add to local answers record
      const submittedRecord: AnswerRecord = {
        question_id: currentQuestion?.id || '',
        question: currentQuestion?.question || '',
        concept: currentQuestion?.concept,
        concept_label: currentQuestion?.concept_label,
        difficulty: currentQuestion?.difficulty || 'medium',
        answer: answerText,
        evaluation: data.evaluation,
        score: data.score,
        feedback: data.feedback,
        answered_at: new Date().toISOString(),
      };

      const updatedAnswers = [...answers, submittedRecord];
      setAnswers(updatedAnswers);

      if (data.next_question) {
        setCurrentQuestion(data.next_question);
        setSession((prev) =>
          prev ? { ...prev, current_question: data.next_question } : prev
        );
      } else {
        // Completed - fetch full report
        setCurrentQuestion(null);
        const reportRes = await fetch(`${API_BASE}/evaluations/${session.id}/report`);
        if (reportRes.ok) {
          const reportData = await reportRes.json();
          setReport(reportData.report);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error during answer grading');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      {/* Top Navigation */}
      <Navbar
        backendOnline={backendOnline}
        demoMode={demoMode}
        onToggleDemoMode={handleToggleDemoMode}
        onOpenKBModal={() => setKbModalOpen(true)}
        onResetSession={session ? handleResetSession : undefined}
        hasActiveSession={Boolean(session)}
      />

      {/* Main View Container */}
      <main className="main-content-area">
        {/* Error Notification Banner */}
        {error && (
          <div className="error-banner">
            <AlertTriangle className="error-icon" size={20} />
            <div className="error-text-group">
              <span className="error-title">Evaluation Error</span>
              <p className="error-desc">{error}</p>
            </div>
            {!demoMode && !backendOnline && (
              <button
                type="button"
                className="btn-accent-sm"
                onClick={() => {
                  setDemoMode(true);
                  setError('');
                }}
              >
                <Sparkles size={14} /> Try Sandbox Demo Mode
              </button>
            )}
          </div>
        )}

        {/* Phase 1: Intake / Setup Form */}
        {!session && (
          <SetupCard
            name={name}
            setName={setName}
            email={email}
            setEmail={setEmail}
            repoUrl={repoUrl}
            setRepoUrl={setRepoUrl}
            loading={loading}
            demoMode={demoMode}
            onSubmit={startEvaluation}
            onSelectPreset={handleSelectPreset}
          />
        )}

        {/* Phase 2 & 3: Active Viva Interview / Scorecard View */}
        {session && (
          <div className="viva-workspace-layout">
            {/* Left Sidebar: Repository Profile & Detected AST Concepts */}
            <AnalysisPanel
              sessionId={session.id}
              status={report ? 'completed' : 'in_progress'}
              profile={analysis || session.profile || {}}
              technologyMap={technologyMap}
            />

            {/* Right Main Stage: Q&A Viva Room OR Final Scorecard */}
            <div className="viva-stage-content">
              {report ? (
                <ScorecardView
                  report={report}
                  answers={answers}
                  profile={analysis || session.profile || {}}
                  onReset={handleResetSession}
                />
              ) : currentQuestion ? (
                <InterviewRoom
                  currentQuestion={currentQuestion}
                  answers={answers}
                  questionIndex={answers.length}
                  totalQuestions={3}
                  loading={loading}
                  onSubmitAnswer={submitAnswer}
                />
              ) : (
                <div className="panel empty-state-panel">
                  <p>All interview questions completed. Generating final report...</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Knowledge Base Modal */}
      <KBStatsModal
        isOpen={kbModalOpen}
        onClose={() => setKbModalOpen(false)}
        demoMode={demoMode}
      />
    </div>
  );
}
