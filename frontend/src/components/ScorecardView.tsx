import React, { useEffect, useState } from 'react';
import confetti from 'canvas-confetti';
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  Download,
  Share2,
  RotateCcw,
  Sparkles,
  BookOpen,
  TrendingUp,
  Brain,
  MessageSquare,
  Copy,
  Check,
} from 'lucide-react';
import { FinalReport, AnswerRecord, RepoProfile } from '../types';

interface ScorecardViewProps {
  report: FinalReport | Record<string, any>;
  answers: AnswerRecord[];
  profile: RepoProfile;
  onReset: () => void;
}

export const ScorecardView: React.FC<ScorecardViewProps> = ({
  report,
  answers,
  profile,
  onReset,
}) => {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Fire celebratory confetti!
    try {
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#6366f1', '#8b5cf6', '#10b981', '#38bdf8', '#fbbf24'],
      });
    } catch (e) {
      // Graceful fallback if canvas is restricted
    }
  }, []);

  const overallScore = Math.round(report.overall_score || 0);
  const readiness = report.readiness || 'Ready for technical interview';
  const mentorNote =
    report.mentor_note ||
    'Strong conceptual foundation. The student demonstrates genuine understanding of the technologies they used.';
  const strongAreas: string[] = report.strong_areas || ['System Architecture', 'Core Patterns'];
  const weakAreas: string[] = report.weak_areas || ['Edge Case Handling', 'Concurrency Nuances'];
  const conceptsTested: string[] = report.concepts_tested || [];

  const handleDownloadReport = () => {
    const reportData = {
      evaluated_repository: profile.full_name || profile.repo,
      timestamp: new Date().toISOString(),
      scorecard: {
        overall_score: overallScore,
        readiness,
        mentor_note: mentorNote,
        strong_areas: strongAreas,
        weak_areas: weakAreas,
        concepts_tested: conceptsTested,
      },
      audit_trail: answers,
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `CODE_VIVA_Report_${(profile.repo || 'session').replace(/\s+/g, '_')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopySummary = () => {
    const summaryText = `🎓 CODE_VIVA Technical Evaluation Result
Repository: ${profile.full_name || 'Codebase'}
Overall Score: ${overallScore}/100
Readiness: ${readiness}
Mentor Summary: ${mentorNote}
Strong Areas: ${strongAreas.join(', ')}
Areas for Growth: ${weakAreas.join(', ')}`;

    navigator.clipboard.writeText(summaryText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isHighScoring = overallScore >= 75;
  const isMediumScoring = overallScore >= 50 && overallScore < 75;

  return (
    <div className="scorecard-container">
      {/* Hero Score Banner */}
      <div className="panel scorecard-hero-panel">
        <div className="scorecard-hero-content">
          <div className="score-meter-box">
            <div
              className={`score-radial-circle ${
                isHighScoring ? 'score-high' : isMediumScoring ? 'score-med' : 'score-low'
              }`}
            >
              <span className="score-number">{overallScore}</span>
              <span className="score-max">/ 100</span>
            </div>
            <span className="score-caption">Overall Viva Score</span>
          </div>

          <div className="scorecard-summary-info">
            <div className="readiness-badge-row">
              <span
                className={`readiness-pill ${
                  isHighScoring ? 'readiness-ready' : 'readiness-prep'
                }`}
              >
                {isHighScoring ? (
                  <CheckCircle2 size={16} className="inline-icon" />
                ) : (
                  <AlertTriangle size={16} className="inline-icon" />
                )}
                {readiness}
              </span>
            </div>

            <h2 className="scorecard-title">Technical Viva Completed</h2>
            <p className="mentor-commentary-text">"{mentorNote}"</p>

            {/* Quick Metrics */}
            <div className="metrics-strip">
              <div className="metric-item">
                <span className="metric-label">Questions Evaluated</span>
                <span className="metric-val">{answers.length}</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Concepts Scanned</span>
                <span className="metric-val">{conceptsTested.length || 6}</span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Codebase</span>
                <span className="metric-val" title={profile.full_name}>
                  {profile.repo || profile.full_name || 'Project'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="scorecard-actions-bar">
          <button
            type="button"
            className="btn-secondary"
            onClick={handleDownloadReport}
            title="Download full evaluation report as JSON"
          >
            <Download size={15} />
            <span>Download Report (JSON)</span>
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={handleCopySummary}
            title="Copy shareable summary to clipboard"
          >
            {copied ? <Check size={15} className="check-green" /> : <Copy size={15} />}
            <span>{copied ? 'Copied!' : 'Copy Summary'}</span>
          </button>
          <button
            type="button"
            className="btn-primary reset-cta-btn"
            onClick={onReset}
            title="Start a new evaluation session"
          >
            <RotateCcw size={15} />
            <span>Start New Evaluation</span>
          </button>
        </div>
      </div>

      {/* Strengths & Growth Areas Grid */}
      <div className="areas-grid">
        <div className="panel strengths-panel">
          <div className="panel-title-group">
            <CheckCircle2 size={18} className="icon-green" />
            <h3 className="panel-title">Demonstrated Strengths</h3>
          </div>
          <div className="areas-list">
            {strongAreas.map((item, idx) => (
              <div key={idx} className="area-item area-strong">
                <span className="area-dot dot-green" />
                <span className="area-text">{item}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel weaknesses-panel">
          <div className="panel-title-group">
            <TrendingUp size={18} className="icon-amber" />
            <h3 className="panel-title">Growth & Prep Opportunities</h3>
          </div>
          <div className="areas-list">
            {weakAreas.map((item, idx) => (
              <div key={idx} className="area-item area-weak">
                <span className="area-dot dot-amber" />
                <span className="area-text">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Comprehensive Answers Breakdown */}
      <div className="panel detailed-audit-panel">
        <div className="panel-header">
          <div className="panel-title-group">
            <BookOpen size={18} className="panel-title-icon" />
            <h3 className="panel-title">Detailed Viva Q&A Audit Trail</h3>
          </div>
          <span className="badge-count">{answers.length} Questions Graded</span>
        </div>

        <div className="audit-cards-list">
          {answers.map((ans, idx) => {
            const score = ans.score;
            const evalGrade = (ans.evaluation || 'correct').toLowerCase();
            return (
              <div key={idx} className="audit-card">
                <div className="audit-card-top">
                  <div className="audit-meta-group">
                    <span className="audit-q-num">Q{idx + 1}</span>
                    <span className="audit-difficulty">
                      {ans.difficulty?.toUpperCase() || 'STAGE'}
                    </span>
                    <span className="audit-concept">
                      {ans.concept_label || ans.concept || 'Concept'}
                    </span>
                  </div>
                  <div className="audit-score-pill">
                    <span className={`eval-badge eval-${evalGrade}`}>
                      {evalGrade.toUpperCase()}
                    </span>
                    <span className="score-badge-val">{score}/100</span>
                  </div>
                </div>

                <h4 className="audit-question-title">{ans.question}</h4>

                <div className="audit-response-box">
                  <span className="audit-section-sub">Candidate Answer:</span>
                  <p className="audit-response-text">{ans.answer}</p>
                </div>

                <div className="audit-feedback-box">
                  <div className="feedback-hdr">
                    <Sparkles size={14} className="sparkle-icon" />
                    <span>Grading & Feedback:</span>
                  </div>
                  <p className="audit-feedback-text">{ans.feedback}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
