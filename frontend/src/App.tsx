import { useEffect, useRef, useState, type FormEvent } from 'react';
import { API_BASE } from './constants';
import type {
  AnswerRecord,
  EvaluationSession,
  FinalReport,
  Question,
  RepoProfile,
  TechnologyMapItem,
} from './types';

const INTERVIEW_QUESTION_COUNT = 10;

interface AnalysisResponse {
  session_id: string;
  profile: RepoProfile;
  technology_map: TechnologyMapItem[];
  repository_url: string;
}

interface AnswerEvaluationResponse {
  evaluation: string;
  score: number;
  feedback: string;
  next_question: Question | null;
}

interface ReportResponse {
  report: FinalReport;
}

async function responseError(response: Response, fallback: string): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (
      typeof body === 'object' &&
      body !== null &&
      'detail' in body &&
      typeof body.detail === 'string'
    ) {
      return body.detail;
    }
  } catch {
    // Use the HTTP status fallback when the response is not JSON.
  }

  return `${fallback} (HTTP ${response.status})`;
}

export default function App() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [session, setSession] = useState<EvaluationSession | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [report, setReport] = useState<FinalReport | null>(null);
  const [answerText, setAnswerText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [voiceMessage, setVoiceMessage] = useState('');
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const currentQuestion = session?.current_question ?? null;
  const answers = session?.answers ?? [];
  const questionNumber = Math.min(answers.length + 1, INTERVIEW_QUESTION_COUNT);

  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== 'inactive') {
        recorder.onstop = null;
        recorder.stop();
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const startEvaluation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    const candidateName = name.trim();
    const candidateEmail =
      email.trim() ||
      `${candidateName.toLowerCase().replace(/[^a-z0-9]+/g, '.') || 'candidate'}@candidate.local`;

    try {
      const response = await fetch(`${API_BASE}/evaluations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student: { name: candidateName, email: candidateEmail },
          repository: { url: repoUrl.trim() },
        }),
      });

      if (!response.ok) {
        throw new Error(await responseError(response, 'Could not start the interview'));
      }

      const createdSession = (await response.json()) as EvaluationSession;
      setSession(createdSession);
      setReport(null);
      setAnalysis(null);
      setAnswerText('');

      try {
        const analysisResponse = await fetch(
          `${API_BASE}/evaluations/${createdSession.id}/analysis`,
        );
        if (!analysisResponse.ok) {
          throw new Error(
            await responseError(analysisResponse, 'Could not load repository analysis'),
          );
        }
        setAnalysis((await analysisResponse.json()) as AnalysisResponse);
      } catch (analysisError) {
        setError(
          analysisError instanceof Error
            ? `Interview started, but repository analysis could not be loaded: ${analysisError.message}`
            : 'Interview started, but repository analysis could not be loaded.',
        );
      }
    } catch (startError) {
      setError(
        startError instanceof Error
          ? startError.message
          : 'Could not start the interview. Check the backend connection and try again.',
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!answerText.trim() || !session || !currentQuestion) return;

    setError('');
    setLoading(true);
    window.speechSynthesis?.cancel();
    setSpeaking(false);

    const submittedAnswer = answerText.trim();
    try {
      const response = await fetch(`${API_BASE}/evaluations/${session.id}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer: submittedAnswer }),
      });
      if (!response.ok) {
        throw new Error(await responseError(response, 'Could not submit your answer'));
      }

      const result = (await response.json()) as AnswerEvaluationResponse;
      const answerRecord: AnswerRecord = {
        question_id: currentQuestion.id,
        question: currentQuestion.question,
        concept: currentQuestion.concept,
        concept_label: currentQuestion.concept_label ?? currentQuestion.category,
        difficulty: currentQuestion.difficulty,
        answer: submittedAnswer,
        evaluation: result.evaluation,
        score: result.score,
        feedback: result.feedback,
      };
      const updatedAnswers = [...answers, answerRecord];
      setSession({
        ...session,
        answers: updatedAnswers,
        current_question: result.next_question,
        status: result.next_question ? 'in_progress' : 'completed',
      });
      setAnswerText('');

      if (!result.next_question) {
        const reportResponse = await fetch(`${API_BASE}/evaluations/${session.id}/report`);
        if (!reportResponse.ok) {
          throw new Error(await responseError(reportResponse, 'Could not load the final report'));
        }
        const reportData = (await reportResponse.json()) as ReportResponse;
        setReport(reportData.report);
      }
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'Could not submit the answer. Please try again.',
      );
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    setError('');
    setVoiceMessage('');

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError('Audio recording is not supported by this browser. You can type your answer instead.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      audioChunksRef.current = [];
      const preferredMimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(
        (mimeType) => MediaRecorder.isTypeSupported(mimeType),
      );
      const recorder = preferredMimeType
        ? new MediaRecorder(stream, { mimeType: preferredMimeType })
        : new MediaRecorder(stream);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        setError('The recording failed. Check microphone permissions and try again.');
      };
      recorder.onstop = async () => {
        const audioType = recorder.mimeType || audioChunksRef.current[0]?.type || 'audio/webm';
        const audio = new Blob(audioChunksRef.current, { type: audioType });
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        recorderRef.current = null;

        if (!audio.size) {
          setError('No audio was recorded. Please try recording your answer again.');
          setRecording(false);
          return;
        }

        setTranscribing(true);
        setVoiceMessage('Transcribing your answer…');
        try {
          const formData = new FormData();
          formData.append('audio', audio, 'answer.webm');
          const response = await fetch(`${API_BASE}/voice/transcription`, {
            method: 'POST',
            body: formData,
          });
          if (!response.ok) {
            throw new Error(await responseError(response, 'Speech transcription failed'));
          }

          const result = (await response.json()) as { text: string };
          if (!result.text.trim()) {
            throw new Error('No speech was recognized. Try again or type your answer.');
          }
          setAnswerText((current) =>
            current.trim() ? `${current.trim()} ${result.text.trim()}` : result.text.trim(),
          );
          setVoiceMessage('Transcription added. Review it, then submit your answer.');
        } catch (transcriptionError) {
          setError(
            transcriptionError instanceof Error
              ? transcriptionError.message
              : 'Speech transcription failed. You can type your answer instead.',
          );
          setVoiceMessage('');
        } finally {
          setRecording(false);
          setTranscribing(false);
        }
      };

      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
      setVoiceMessage('Recording… Select “Stop and transcribe” when you are done.');
    } catch (recordingError) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setError(
        recordingError instanceof Error
          ? `Could not access the microphone: ${recordingError.message}`
          : 'Could not access the microphone. Check browser permissions.',
      );
    }
  };

  const stopRecording = () => {
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
    }
  };

  const toggleQuestionSpeech = () => {
    if (!currentQuestion || !('speechSynthesis' in window)) {
      setError('Question playback is not supported by this browser.');
      return;
    }

    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(currentQuestion.question);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  };

  const handleReset = () => {
    window.speechSynthesis?.cancel();
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    recorderRef.current = null;
    streamRef.current = null;
    setSession(null);
    setAnalysis(null);
    setReport(null);
    setAnswerText('');
    setError('');
    setVoiceMessage('');
    setRecording(false);
    setTranscribing(false);
    setSpeaking(false);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <p className="eyebrow">CODE_VIVA</p>
        <h1>Adaptive GitHub Project Evaluator</h1>
        <p>Repository-based technical interviews, grounded in your project and knowledge base.</p>
      </header>

      {!session && (
        <form className="panel setup-panel" onSubmit={startEvaluation}>
          <h2>Start an interview</h2>
          <label htmlFor="candidate-name">Your name</label>
          <input
            id="candidate-name"
            autoComplete="name"
            required
            minLength={2}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Alex Morgan"
          />
          <label htmlFor="candidate-email">Email (optional)</label>
          <input
            id="candidate-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
          <label htmlFor="repository-url">Public GitHub repository URL</label>
          <input
            id="repository-url"
            type="url"
            required
            value={repoUrl}
            onChange={(event) => setRepoUrl(event.target.value)}
            placeholder="https://github.com/owner/repository"
          />
          <button disabled={loading} type="submit">
            {loading ? 'Analyzing repository…' : 'Start interview'}
          </button>
        </form>
      )}

      {error && <div className="error-box" role="alert">{error}</div>}

      {session && (
        <>
          <div className="progress-card">
            <div className="progress-heading">
              <strong>Interview progress</strong>
              <span>
                {Math.min(answers.length, INTERVIEW_QUESTION_COUNT)} / {INTERVIEW_QUESTION_COUNT}
              </span>
            </div>
            <progress value={answers.length} max={INTERVIEW_QUESTION_COUNT} />
          </div>

          <div className="layout">
            <aside className="panel analysis-panel">
              <h2>Repository analysis</h2>
              <p><strong>Session:</strong> {session.id}</p>
              <p><strong>Status:</strong> {session.status.replace('_', ' ')}</p>
              <h3>Repository profile</h3>
              <pre>{JSON.stringify(analysis?.profile ?? session.profile, null, 2)}</pre>
              {analysis?.technology_map.length ? (
                <>
                  <h3>Technology focus</h3>
                  <ul className="technology-list">
                    {analysis.technology_map.map((item) => (
                      <li key={item.concept_key}>{item.name}</li>
                    ))}
                  </ul>
                </>
              ) : null}
              <button className="secondary-button" type="button" onClick={handleReset}>
                Start another interview
              </button>
            </aside>

            <main className="panel interview-panel">
              <h2>Technical interview</h2>
              {report ? (
                <section className="report-box" aria-live="polite">
                  <div className="report-heading">
                    <div>
                      <p className="report-eyebrow">Interview complete</p>
                      <h3>Fundamentals report</h3>
                    </div>
                    <strong className="report-score">{Math.round(report.overall_score)}<span>/100</span></strong>
                  </div>
                  <p className="report-readiness">{report.readiness}</p>
                  <p>{report.mentor_note}</p>

                  <h4>Concept coverage</h4>
                  <div className="report-concepts">
                    {(report.concepts_detected ?? session.profile.detected_concepts ?? []).map((concept) => {
                      const conceptAnswers = answers.filter(
                        (answer) => answer.concept === concept || answer.concept_label === concept,
                      );
                      const average = conceptAnswers.length
                        ? Math.round(
                            conceptAnswers.reduce((total, answer) => total + answer.score, 0) /
                              conceptAnswers.length,
                          )
                        : 0;
                      const label =
                        conceptAnswers[0]?.concept_label ??
                        concept.replace(/_/g, ' ').replace(/\b\w/g, (letter: string) => letter.toUpperCase());

                      return (
                        <details className="report-concept" key={concept}>
                          <summary>
                            <span>{label}</span>
                            <span className="report-concept-score">
                              {conceptAnswers.length
                                ? `${conceptAnswers.length} question${conceptAnswers.length === 1 ? '' : 's'} · ${average}/100`
                                : 'Not covered'}
                            </span>
                          </summary>
                          {conceptAnswers.length ? (
                            <div className="report-answer-list">
                              {conceptAnswers.map((answer) => (
                                <details className="report-answer" key={answer.question_id}>
                                  <summary>
                                    <span>{answer.question}</span>
                                    <span>{answer.score}/100 · {answer.difficulty}</span>
                                  </summary>
                                  <div className="report-answer-content">
                                    <h5>Your answer</h5>
                                    <p>{answer.answer}</p>
                                    <h5>Feedback</h5>
                                    <p>{answer.feedback}</p>
                                  </div>
                                </details>
                              ))}
                            </div>
                          ) : (
                            <p className="report-uncovered">
                              No question was completed for this detected concept.
                            </p>
                          )}
                        </details>
                      );
                    })}
                  </div>

                  <div className="report-highlights">
                    <section>
                      <h4>Strong areas</h4>
                      {report.strong_areas.length ? (
                        <ul>{report.strong_areas.map((area) => <li key={area}>{area}</li>)}</ul>
                      ) : <p>No strong area was identified yet.</p>}
                    </section>
                    <section>
                      <h4>Areas to strengthen</h4>
                      {report.weak_areas.length ? (
                        <ul>{report.weak_areas.map((area) => <li key={area}>{area}</li>)}</ul>
                      ) : <p>No weak area was identified.</p>}
                    </section>
                  </div>
                </section>
              ) : currentQuestion ? (
                <>
                  <div className="question-meta">
                    <span>{currentQuestion.concept_label ?? currentQuestion.category}</span>
                    <span>{currentQuestion.difficulty}</span>
                  </div>
                  <p className="question-count">
                    Question {questionNumber} of {INTERVIEW_QUESTION_COUNT}
                  </p>
                  <h3 className="question-title">{currentQuestion.question}</h3>
                  {currentQuestion.file_reference && (
                    <p className="file-reference">Knowledge base: {currentQuestion.file_reference}</p>
                  )}

                  <div className="voice-controls">
                    <button className="secondary-button" type="button" onClick={toggleQuestionSpeech}>
                      {speaking ? 'Stop question playback' : 'Read question aloud'}
                    </button>
                    {!recording ? (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={startRecording}
                        disabled={loading || transcribing}
                      >
                        {transcribing ? 'Transcribing…' : 'Record voice answer'}
                      </button>
                    ) : (
                      <button className="secondary-button" type="button" onClick={stopRecording}>
                        Stop and transcribe
                      </button>
                    )}
                    {voiceMessage && <p className="voice-help" aria-live="polite">{voiceMessage}</p>}
                  </div>

                  <form onSubmit={handleSubmitAnswer}>
                    <label htmlFor="candidate-answer">Your answer</label>
                    <textarea
                      id="candidate-answer"
                      rows={7}
                      value={answerText}
                      onChange={(event) => setAnswerText(event.target.value)}
                      placeholder="Type your answer, or record it above and review the transcription…"
                    />
                    <button disabled={loading || !answerText.trim()} type="submit">
                      {loading ? 'Submitting…' : 'Submit answer'}
                    </button>
                  </form>

                  {answers.length > 0 && (
                    <section className="answer-history" aria-live="polite">
                      <h3>Previous answers</h3>
                      {answers.slice(-2).map((answer) => (
                        <article key={answer.question_id} className="answer-feedback">
                          <p><strong>{answer.concept_label ?? answer.question}</strong></p>
                          <p>Score: {answer.score} / 100 · {answer.evaluation}</p>
                          <p>{answer.feedback}</p>
                        </article>
                      ))}
                    </section>
                  )}
                </>
              ) : (
                <p>Interview complete. Your final report is being prepared.</p>
              )}
            </main>
          </div>
        </>
      )}
    </div>
  );
}
