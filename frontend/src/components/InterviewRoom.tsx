import React, { useState, useEffect, useRef } from 'react';
import {
  HelpCircle,
  Volume2,
  VolumeX,
  Mic,
  MicOff,
  Send,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  Lightbulb,
  Clock,
  BookOpen,
} from 'lucide-react';
import { Question, AnswerRecord } from '../types';

interface InterviewRoomProps {
  currentQuestion: Question;
  answers: AnswerRecord[];
  questionIndex: number;
  totalQuestions: number;
  loading: boolean;
  onSubmitAnswer: (answerText: string) => Promise<void>;
}

export const InterviewRoom: React.FC<InterviewRoomProps> = ({
  currentQuestion,
  answers,
  questionIndex,
  totalQuestions,
  loading,
  onSubmitAnswer,
}) => {
  const [answerText, setAnswerText] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const recognitionRef = useRef<any>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Setup browser Speech Recognition if available
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      setSpeechSupported(true);
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }
        setAnswerText((prev) => (prev ? prev + ' ' + transcript : transcript));
      };

      recognition.onerror = () => {
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Text to speech for question
  const toggleSpeakQuestion = () => {
    if (!('speechSynthesis' in window)) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    } else {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(currentQuestion.question);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      setIsSpeaking(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  // Toggle dictation
  const toggleListening = () => {
    if (!recognitionRef.current) return;

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.error('Speech recognition error:', err);
      }
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!answerText.trim() || loading) return;

    if (isSpeaking && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }

    const currentText = answerText;
    setAnswerText('');
    await onSubmitAnswer(currentText);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      void handleSubmit();
    }
  };

  const difficulty = currentQuestion.difficulty?.toLowerCase() || 'medium';
  const wordCount = answerText.trim() ? answerText.trim().split(/\s+/).length : 0;
  const progressPercent = Math.min(100, Math.round(((questionIndex + 1) / totalQuestions) * 100));

  return (
    <div className="interview-room">
      {/* Top Progress Bar & Difficulty Tracker */}
      <div className="panel progress-panel">
        <div className="progress-meta-row">
          <div className="progress-info">
            <span className="step-count">
              Question <strong>{questionIndex + 1}</strong> of {totalQuestions}
            </span>
            <span className="step-difficulty-label">
              Stage:{' '}
              <span className={`diff-text diff-${difficulty}`}>
                {difficulty.toUpperCase()}
              </span>
            </span>
          </div>
          <span className="progress-percentage">{progressPercent}% Completed</span>
        </div>

        <div className="progress-track">
          <div
            className="progress-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="difficulty-stepper">
          <div className={`stepper-node ${questionIndex >= 0 ? 'active' : ''}`}>
            <span className="node-dot" />
            <span className="node-label">1. Foundational (Easy)</span>
          </div>
          <div className={`stepper-node ${questionIndex >= 1 ? 'active' : ''}`}>
            <span className="node-dot" />
            <span className="node-label">2. Architecture (Medium)</span>
          </div>
          <div className={`stepper-node ${questionIndex >= 2 ? 'active' : ''}`}>
            <span className="node-dot" />
            <span className="node-label">3. System Trade-offs (Hard)</span>
          </div>
        </div>
      </div>

      {/* Active Question Box */}
      <div className="panel question-panel">
        <div className="question-header">
          <div className="question-tags">
            <span className={`badge-difficulty badge-${difficulty}`}>
              {difficulty.toUpperCase()}
            </span>
            <span className="badge-category">
              <BookOpen size={12} className="inline-icon" />
              {currentQuestion.concept_label ||
                currentQuestion.topic ||
                currentQuestion.category.replace(/_/g, ' ')}
            </span>
          </div>

          {/* Audio Question Reader */}
          <button
            type="button"
            className={`audio-speech-btn ${isSpeaking ? 'speaking' : ''}`}
            onClick={toggleSpeakQuestion}
            title={isSpeaking ? 'Stop speaking question' : 'Listen to question aloud'}
          >
            {isSpeaking ? (
              <>
                <VolumeX size={15} />
                <span>Stop Audio</span>
                <span className="sound-wave">
                  <span />
                  <span />
                  <span />
                </span>
              </>
            ) : (
              <>
                <Volume2 size={15} />
                <span>Listen to Viva Question</span>
              </>
            )}
          </button>
        </div>

        <h2 className="question-text">{currentQuestion.question}</h2>

        {/* Expected Knowledge Pill Group */}
        {currentQuestion.expected_knowledge && currentQuestion.expected_knowledge.length > 0 && (
          <div className="expected-knowledge-bar">
            <span className="expected-label">Key Competencies Evaluated:</span>
            <div className="expected-tags-list">
              {currentQuestion.expected_knowledge.map((k) => (
                <span key={k} className="expected-tag">
                  #{k}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Answer Form */}
        <form onSubmit={handleSubmit} className="answer-form">
          <div className="textarea-container">
            <textarea
              ref={textareaRef}
              id="candidate-answer-input"
              rows={6}
              className="answer-textarea"
              placeholder="Explain your approach, implementation reasoning, and practical trade-offs here..."
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              autoFocus
            />

            <div className="textarea-bottom-toolbar">
              <div className="counter-group">
                <span className={`word-counter ${wordCount < 15 ? 'low-words' : 'good-words'}`}>
                  {wordCount} words
                </span>
                <span className="shortcut-hint">Tip: Press Ctrl + Enter to submit</span>
              </div>

              {speechSupported && (
                <button
                  type="button"
                  className={`voice-dictate-btn ${isListening ? 'listening' : ''}`}
                  onClick={toggleListening}
                  title={isListening ? 'Stop dictation' : 'Dictate your answer via microphone'}
                >
                  {isListening ? (
                    <>
                      <MicOff size={14} />
                      <span>Recording voice...</span>
                    </>
                  ) : (
                    <>
                      <Mic size={14} />
                      <span>Voice Dictation</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          <div className="answer-guidance-callout">
            <Lightbulb size={16} className="guidance-icon" />
            <p>
              <strong>Scoring Criteria:</strong> Strong answers explain <em>why</em> design decisions
              were made, highlight trade-offs, and connect theory with real codebase application.
            </p>
          </div>

          <div className="form-submit-row">
            <button
              id="submit-answer-btn"
              type="submit"
              className="btn-primary submit-answer-btn"
              disabled={loading || !answerText.trim()}
            >
              {loading ? (
                <>
                  <div className="spinner-border" />
                  <span>Evaluating Conceptual Depth with AI...</span>
                </>
              ) : (
                <>
                  <span>Submit Answer & Continue</span>
                  <Send size={16} />
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Answers History / Feedback Section */}
      {answers.length > 0 && (
        <div className="panel answers-history-panel">
          <h3 className="history-heading">Previous Viva Responses ({answers.length})</h3>
          <div className="history-cards-list">
            {answers.map((record, index) => {
              const score = record.score;
              const evaluation = (record.evaluation || 'correct').toLowerCase();
              return (
                <div key={record.question_id || index} className="history-card">
                  <div className="history-card-header">
                    <span className="history-question-num">Q{index + 1}</span>
                    <span className="history-concept">
                      {record.concept_label || record.concept || 'General Concept'}
                    </span>
                    <div className="history-score-badge">
                      <span className={`eval-pill eval-${evaluation}`}>
                        {evaluation.toUpperCase()}
                      </span>
                      <span className="score-num">{score}/100</span>
                    </div>
                  </div>

                  <p className="history-question-title">{record.question}</p>

                  <div className="history-candidate-answer">
                    <span className="sub-label">Your Response:</span>
                    <p className="candidate-answer-text">{record.answer}</p>
                  </div>

                  <div className="history-feedback-box">
                    <div className="feedback-title-row">
                      <Sparkles size={14} className="sparkle-icon" />
                      <span>AI Evaluator Feedback:</span>
                    </div>
                    <p className="feedback-content">{record.feedback}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
