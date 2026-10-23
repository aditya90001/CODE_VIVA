import React from 'react';
import {
  Zap,
  Activity,
  Database,
  Sparkles,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { API_BASE } from '../constants';

interface NavbarProps {
  backendOnline: boolean | null;
  demoMode: boolean;
  onToggleDemoMode: () => void;
  onOpenKBModal: () => void;
  onResetSession?: () => void;
  hasActiveSession: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  backendOnline,
  demoMode,
  onToggleDemoMode,
  onOpenKBModal,
  onResetSession,
  hasActiveSession,
}) => {
  return (
    <header className="navbar-container">
      <div className="navbar-content">
        {/* Brand Logo */}
        <div className="brand-group">
          <div className="logo-badge">
            <Zap className="logo-icon" size={22} />
          </div>
          <div className="brand-text">
            <div className="brand-title-row">
              <span className="brand-name">CODE_VIVA</span>
              <span className="brand-pill">v2.0 RAG</span>
            </div>
            <span className="brand-subtitle">Adaptive Technical Viva Evaluator</span>
          </div>
        </div>

        {/* Right side controls */}
        <div className="nav-actions">
          {/* Backend Status indicator */}
          <div
            className={`status-pill ${
              demoMode
                ? 'status-demo'
                : backendOnline
                ? 'status-online'
                : 'status-offline'
            }`}
            title={
              demoMode
                ? 'Running in Client-Side Interactive Sandbox Mode'
                : backendOnline
                ? `Backend API Connected (${new URL(API_BASE).origin})`
                : 'Backend API Offline — run `uvicorn backend.app.main:app` or use Sandbox Mode'
            }
          >
            <span className="status-dot" />
            <span className="status-label">
              {demoMode ? (
                <>
                  <Sparkles size={13} className="inline-icon" /> Sandbox Demo
                </>
              ) : backendOnline ? (
                <>
                  <CheckCircle2 size={13} className="inline-icon" /> Backend Online
                </>
              ) : (
                <>
                  <AlertTriangle size={13} className="inline-icon" /> Backend Offline
                </>
              )}
            </span>
          </div>

          {/* Sandbox Toggle */}
          <button
            type="button"
            className={`mode-toggle-btn ${demoMode ? 'active' : ''}`}
            onClick={onToggleDemoMode}
            title={demoMode ? 'Switch to Live Backend API' : 'Switch to Interactive Sandbox Demo'}
          >
            <Sparkles size={15} />
            <span>{demoMode ? 'Live Mode' : 'Sandbox Demo'}</span>
          </button>

          {/* KB Inspector */}
          <button
            type="button"
            className="icon-action-btn"
            onClick={onOpenKBModal}
            title="Inspect ChromaDB Knowledge Base"
          >
            <Database size={16} />
            <span className="btn-label-desktop">Knowledge Base</span>
          </button>

          {/* Reset session button if active */}
          {hasActiveSession && onResetSession && (
            <button
              type="button"
              className="icon-action-btn reset-btn"
              onClick={onResetSession}
              title="Start a new interview evaluation"
            >
              <RotateCcw size={16} />
              <span className="btn-label-desktop">New Session</span>
            </button>
          )}

          {/* GitHub repo link */}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="icon-action-btn github-btn"
            title="GitHub"
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
              <path d="M9 18c-4.51 2-5-2-7-2" />
            </svg>
          </a>
        </div>
      </div>
    </header>
  );
};
