import React, { useState } from 'react';
import {
  FolderGit2,
  Star,
  GitFork,
  GitBranch,
  FileCode2,
  Copy,
  Check,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Cpu,
  Layers,
  Sparkles,
} from 'lucide-react';
import { RepoProfile, TechnologyMapItem } from '../types';

interface AnalysisPanelProps {
  sessionId: string;
  status: string;
  profile: RepoProfile;
  technologyMap?: TechnologyMapItem[];
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({
  sessionId,
  status,
  profile,
  technologyMap = [],
}) => {
  const [copied, setCopied] = useState(false);
  const [readmeExpanded, setReadmeExpanded] = useState(false);

  const copySessionId = () => {
    navigator.clipboard.writeText(sessionId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const detectedConcepts = profile.detected_concepts || [];
  const repoName = profile.full_name || profile.repo || 'Evaluated Repository';
  const repoUrl = profile.repository_url || (profile.full_name ? `https://github.com/${profile.full_name}` : '');

  return (
    <aside className="panel analysis-panel">
      {/* Session Header */}
      <div className="panel-header">
        <div className="panel-title-group">
          <FolderGit2 className="panel-title-icon" size={18} />
          <h3 className="panel-title">Repository Profile</h3>
        </div>
        <span className={`status-tag status-${status}`}>
          {status === 'in_progress' ? 'In Progress' : status === 'completed' ? 'Completed' : 'Analysis'}
        </span>
      </div>

      {/* Repo Name & Link */}
      <div className="repo-identity-card">
        <div className="repo-name-row">
          <span className="repo-title" title={repoName}>
            {repoName}
          </span>
          {repoUrl && (
            <a
              href={repoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="repo-external-link"
              title="Open in GitHub"
            >
              <ExternalLink size={14} />
            </a>
          )}
        </div>
        {profile.description && (
          <p className="repo-description-text">{profile.description}</p>
        )}

        {/* Quick Stats Grid */}
        <div className="repo-stats-grid">
          {profile.language && (
            <div className="stat-pill">
              <FileCode2 size={13} className="stat-icon lang-icon" />
              <span>{profile.language}</span>
            </div>
          )}
          {typeof profile.stars === 'number' && (
            <div className="stat-pill">
              <Star size={13} className="stat-icon star-icon" />
              <span>{profile.stars.toLocaleString()}</span>
            </div>
          )}
          {typeof profile.forks === 'number' && (
            <div className="stat-pill">
              <GitFork size={13} className="stat-icon fork-icon" />
              <span>{profile.forks.toLocaleString()}</span>
            </div>
          )}
          {profile.default_branch && (
            <div className="stat-pill">
              <GitBranch size={13} className="stat-icon branch-icon" />
              <span>{profile.default_branch}</span>
            </div>
          )}
        </div>
      </div>

      {/* Detected Engineering Concepts */}
      <div className="detected-concepts-section">
        <div className="section-label-row">
          <Cpu size={14} className="section-icon" />
          <span className="section-label">Detected Concepts ({detectedConcepts.length})</span>
        </div>

        {detectedConcepts.length > 0 ? (
          <div className="concepts-chip-grid">
            {detectedConcepts.map((conceptKey) => {
              const formattedName = conceptKey
                .replace(/_/g, ' ')
                .replace(/\b\w/g, (c) => c.toUpperCase());
              return (
                <div key={conceptKey} className="concept-chip">
                  <span className="concept-dot" />
                  <span className="concept-text">{formattedName}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="empty-hint">Concepts are being extracted from AST tree...</p>
        )}
      </div>

      {/* Technology Map items if provided */}
      {technologyMap.length > 0 && (
        <div className="tech-map-section">
          <div className="section-label-row">
            <Layers size={14} className="section-icon" />
            <span className="section-label">Technology Focus Areas</span>
          </div>
          <div className="tech-map-list">
            {technologyMap.slice(0, 4).map((item) => (
              <div key={item.name} className="tech-map-item">
                <span className="tech-map-name">{item.name}</span>
                <div className="tech-map-meter">
                  <div
                    className="tech-map-bar"
                    style={{ width: `${Math.min(100, (item.importance || 4) * 20)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* README Summary Collapsible */}
      {profile.readme_summary && (
        <div className="readme-accordion">
          <button
            type="button"
            className="readme-toggle-btn"
            onClick={() => setReadmeExpanded(!readmeExpanded)}
          >
            <span>Extracted README Analysis</span>
            {readmeExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {readmeExpanded && (
            <div className="readme-content-box">
              <p className="readme-text">{profile.readme_summary}</p>
            </div>
          )}
        </div>
      )}

      {/* Session ID Pill */}
      <div className="session-footer">
        <span className="session-label">Session ID:</span>
        <button
          type="button"
          className="session-id-pill"
          onClick={copySessionId}
          title="Click to copy Session ID"
        >
          <span className="session-id-text">{sessionId.slice(0, 14)}...</span>
          {copied ? <Check size={12} className="check-green" /> : <Copy size={12} />}
        </button>
      </div>
    </aside>
  );
};
