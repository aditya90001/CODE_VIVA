import React, { useState, useEffect } from 'react';
import {
  Database,
  X,
  RefreshCw,
  FileText,
  CheckCircle2,
  Layers,
  Sparkles,
} from 'lucide-react';
import { API_BASE } from '../constants';
import { KBStatsData } from '../types';

interface KBStatsModalProps {
  isOpen: boolean;
  onClose: () => void;
  demoMode: boolean;
}

export const KBStatsModal: React.FC<KBStatsModalProps> = ({
  isOpen,
  onClose,
  demoMode,
}) => {
  const [stats, setStats] = useState<KBStatsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [reindexMsg, setReindexMsg] = useState('');

  const fetchStats = async () => {
    if (demoMode) {
      setStats({
        json_kb: {
          total: 85,
          by_domain: { rag: 30, python: 55 },
          by_difficulty: { easy: 30, medium: 35, hard: 20 },
        },
        pdf_bank: {
          total_chunks: 142,
          files_indexed: ['fastapi_guide.pdf', 'system_design_primer.pdf', 'python_concurrency.pdf'],
          topics: { backend: 48, rag: 42, python: 52 },
        },
      });
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/knowledge-base-stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      // Fallback
      setStats({
        json_kb: { total: 0 },
        pdf_bank: { total_chunks: 0 },
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStats();
    }
  }, [isOpen, demoMode]);

  const handleReindex = async () => {
    if (demoMode) {
      setReindexing(true);
      setTimeout(() => {
        setReindexing(false);
        setReindexMsg('Sandbox KB refreshed with 85 entries.');
      }, 1000);
      return;
    }

    setReindexing(true);
    setReindexMsg('');
    try {
      const res = await fetch(`${API_BASE}/admin/ingest-json-kb`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setReindexMsg(data.message || 'Ingestion initiated in background.');
        await fetchStats();
      } else {
        setReindexMsg('Ingestion failed to start.');
      }
    } catch (e) {
      setReindexMsg('Could not connect to backend server.');
    } finally {
      setReindexing(false);
    }
  };

  if (!isOpen) return null;

  const jsonTotal = stats?.json_kb?.total ?? 0;
  const pdfChunks = stats?.pdf_bank?.total_chunks ?? 0;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="panel-title-group">
            <Database size={20} className="panel-title-icon" />
            <h3 className="modal-title">ChromaDB Knowledge Base Inspector</h3>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          <p className="modal-intro">
            CODE_VIVA indexes curated technical interview banks into ChromaDB vector collections.
            When a candidate submits a repository, questions are retrieved dynamically based on
            detected code concepts.
          </p>

          <div className="kb-stats-grid">
            {/* JSON Question Bank */}
            <div className="kb-stat-card">
              <div className="kb-stat-header">
                <FileText size={16} className="icon-cyan" />
                <h4>JSON Question Bank</h4>
              </div>
              <div className="kb-stat-count">{jsonTotal}</div>
              <span className="kb-stat-caption">Indexed Q&A Entries</span>

              {stats?.json_kb?.by_domain && (
                <div className="kb-domain-breakdown">
                  {Object.entries(stats.json_kb.by_domain).map(([domain, count]) => (
                    <div key={domain} className="domain-row">
                      <span className="domain-name">{domain.toUpperCase()}</span>
                      <span className="domain-val">{count} questions</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* PDF Question Bank */}
            <div className="kb-stat-card">
              <div className="kb-stat-header">
                <Layers size={16} className="icon-purple" />
                <h4>PDF Vector Bank</h4>
              </div>
              <div className="kb-stat-count">{pdfChunks}</div>
              <span className="kb-stat-caption">Indexed Vector Chunks</span>

              <p className="kb-sub-info">
                PDFs in <code>knowledge_base/*.pdf</code> are chunked and embedded using ChromaDB for
                concept-level retrieval.
              </p>
            </div>
          </div>

          {reindexMsg && (
            <div className="reindex-notification">
              <CheckCircle2 size={15} />
              <span>{reindexMsg}</span>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="btn-secondary"
            onClick={handleReindex}
            disabled={reindexing}
          >
            <RefreshCw size={14} className={reindexing ? 'spin-icon' : ''} />
            <span>{reindexing ? 'Re-indexing...' : 'Trigger Re-Ingestion'}</span>
          </button>
          <button type="button" className="btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
