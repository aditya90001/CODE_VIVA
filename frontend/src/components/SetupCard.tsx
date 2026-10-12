import React from 'react';
import {
  Code2,
  Terminal,
  Cpu,
  BrainCircuit,
  Award,
  ArrowRight,
  Sparkles,
  User,
  Mail,
  FolderGit2,
  CheckCircle2,
} from 'lucide-react';
import { PRESET_REPOSITORIES, PresetRepo } from '../constants';

interface SetupCardProps {
  name: string;
  setName: (v: string) => void;
  email: string;
  setEmail: (v: string) => void;
  repoUrl: string;
  setRepoUrl: (v: string) => void;
  loading: boolean;
  demoMode: boolean;
  onSubmit: (e: React.FormEvent) => void;
  onSelectPreset: (preset: PresetRepo) => void;
}

export const SetupCard: React.FC<SetupCardProps> = ({
  name,
  setName,
  email,
  setEmail,
  repoUrl,
  setRepoUrl,
  loading,
  demoMode,
  onSubmit,
  onSelectPreset,
}) => {
  return (
    <div className="setup-wrapper">
      {/* Hero Header */}
      <div className="hero-banner">
        <div className="hero-badge">
          <BrainCircuit size={16} />
          <span>Automated Technical Viva & Codebase Evaluator</span>
        </div>
        <h1 className="hero-title">
          Adaptive AI Technical Viva for <span className="gradient-text">GitHub Codebases</span>
        </h1>
        <p className="hero-description">
          Submit any public repository. Our engine analyzes AST patterns, extracts applied software
          concepts, retrieves verified interview questions from ChromaDB, and conducts an adaptive
          3-tier viva with instant AI scoring.
        </p>
      </div>

      <div className="setup-grid">
        {/* Main Intake Form */}
        <div className="panel setup-form-panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <Terminal className="panel-title-icon" size={20} />
              <h2 className="panel-title">Candidate & Repository Intake</h2>
            </div>
            {demoMode && (
              <span className="badge badge-accent">
                <Sparkles size={12} /> Sandbox Mode Active
              </span>
            )}
          </div>

          <form onSubmit={onSubmit} className="intake-form">
            {/* Student Name */}
            <div className="form-group">
              <label htmlFor="student-name" className="form-label">
                <User size={14} /> Candidate Full Name
              </label>
              <input
                id="student-name"
                type="text"
                className="form-input"
                placeholder="e.g. Alex Morgan"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            {/* Email Address */}
            <div className="form-group">
              <label htmlFor="student-email" className="form-label">
                <Mail size={14} /> Email Address
              </label>
              <input
                id="student-email"
                type="email"
                className="form-input"
                placeholder="e.g. alex.morgan@engineering.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            {/* GitHub URL */}
            <div className="form-group">
              <label htmlFor="repo-url" className="form-label">
                <FolderGit2 size={14} /> GitHub Repository URL
              </label>
              <input
                id="repo-url"
                type="url"
                className="form-input code-font"
                placeholder="https://github.com/owner/repository"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                required
              />
            </div>

            {/* Quick Presets */}
            <div className="presets-section">
              <span className="presets-label">⚡ Quick Presets (Click to autofill):</span>
              <div className="presets-list">
                {PRESET_REPOSITORIES.map((preset) => (
                  <button
                    key={preset.name}
                    type="button"
                    className={`preset-chip ${repoUrl === preset.url ? 'active' : ''}`}
                    onClick={() => onSelectPreset(preset)}
                    title={preset.description}
                  >
                    <span className="preset-name">{preset.name}</span>
                    <span className="preset-tag">{preset.language}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Submit Action */}
            <button
              id="start-viva-btn"
              type="submit"
              disabled={loading || !repoUrl.trim() || !name.trim()}
              className="btn-primary start-btn"
            >
              {loading ? (
                <>
                  <div className="spinner-border" />
                  <span>Scanning AST & Ingesting Repository...</span>
                </>
              ) : (
                <>
                  <span>Launch Technical Viva</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Feature Explainer Sidebar */}
        <div className="setup-sidebar">
          <div className="panel explainer-panel">
            <h3 className="sidebar-heading">How CODE_VIVA Works</h3>

            <div className="flow-step-card">
              <div className="flow-step-number">1</div>
              <div className="flow-step-info">
                <h4>AST & Concept Detection</h4>
                <p>
                  Scans imports, decorators, classes, async functions, and frameworks to detect the actual concepts used in the repository.
                </p>
              </div>
            </div>

            <div className="flow-step-card">
              <div className="flow-step-number">2</div>
              <div className="flow-step-info">
                <h4>ChromaDB Knowledge Retrieval</h4>
                <p>
                  Retrieves verified interview questions matching the candidate's exact stack from JSON & PDF vector knowledge bases.
                </p>
              </div>
            </div>

            <div className="flow-step-card">
              <div className="flow-step-number">3</div>
              <div className="flow-step-info">
                <h4>Adaptive 3-Tier Viva</h4>
                <p>
                  Questions escalate from Foundational (Easy) → Applied Architecture (Medium) → Deep System Design & Trade-offs (Hard).
                </p>
              </div>
            </div>

            <div className="flow-step-card">
              <div className="flow-step-number">4</div>
              <div className="flow-step-info">
                <h4>Instant AI Evaluation & Scorecard</h4>
                <p>
                  Grades conceptual depth, keyword mastery, and trade-off reasoning with comprehensive actionable feedback.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
