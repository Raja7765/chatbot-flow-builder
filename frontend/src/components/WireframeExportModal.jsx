import React, { useState } from 'react';
import {
  exportCanvasAsPNG,
  exportCanvasAsPDF,
  generateMermaidFlowchart,
  generateCSVExport,
  downloadFile,
} from '../utils/exportTools';

/**
 * WireframeExportModal Component
 * Provides complete review wireframe export options:
 * - PNG Image capture
 * - PDF document capture
 * - Mermaid Flowchart syntax & download
 * - CSV matrix export
 */
const WireframeExportModal = ({
  isOpen,
  onClose,
  nodes = [],
  edges = [],
  canvasElement,
  flowName = 'NABH_QMitra_Flow',
}) => {
  const [activeTab, setActiveTab] = useState('image'); // 'image' | 'mermaid' | 'csv'
  const [isExporting, setIsExporting] = useState(false);
  const [copiedNotice, setCopiedNotice] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const sanitizedFilename = (flowName || 'flow').replace(/[^a-zA-Z0-9_-]/g, '_');

  const handleExportPNG = async () => {
    setIsExporting(true);
    setError(null);
    try {
      await exportCanvasAsPNG(canvasElement, `${sanitizedFilename}.png`);
      setIsExporting(false);
    } catch (err) {
      setIsExporting(false);
      setError(`PNG Export Failed: ${err.message}`);
    }
  };

  const handleExportPDF = async () => {
    setIsExporting(true);
    setError(null);
    try {
      await exportCanvasAsPDF(canvasElement, `${sanitizedFilename}.pdf`);
      setIsExporting(false);
    } catch (err) {
      setIsExporting(false);
      setError(`PDF Export Failed: ${err.message}`);
    }
  };

  const mermaidText = generateMermaidFlowchart(nodes, edges);
  const csvText = generateCSVExport(nodes, edges);

  const handleDownloadMermaid = () => {
    downloadFile(`${sanitizedFilename}.mmd`, mermaidText, 'text/plain');
  };

  const handleCopyMermaid = () => {
    navigator.clipboard.writeText(mermaidText);
    setCopiedNotice('Copied Mermaid syntax to clipboard!');
    setTimeout(() => setCopiedNotice(false), 2500);
  };

  const handleDownloadCSV = () => {
    downloadFile(`${sanitizedFilename}_matrix.csv`, csvText, 'text/csv');
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-container wireframe-export-modal"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '680px', width: '92%' }}
      >
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-icon" aria-hidden="true">📤</span>
            <div>
              <h3>Export Wireframe &amp; Reports</h3>
              <p className="modal-subtitle">
                Export client-ready wireframes, diagrams, or flow matrices for lead review.
              </p>
            </div>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        {/* Tab Selector */}
        <div className="import-tabs-bar">
          <button
            type="button"
            className={`import-tab-btn ${activeTab === 'image' ? 'active' : ''}`}
            onClick={() => setActiveTab('image')}
          >
            🖼️ PNG &amp; PDF Wireframe
          </button>
          <button
            type="button"
            className={`import-tab-btn ${activeTab === 'mermaid' ? 'active' : ''}`}
            onClick={() => setActiveTab('mermaid')}
          >
            📊 Mermaid Flowchart
          </button>
          <button
            type="button"
            className={`import-tab-btn ${activeTab === 'csv' ? 'active' : ''}`}
            onClick={() => setActiveTab('csv')}
          >
            📑 CSV Flow Matrix
          </button>
        </div>

        <div className="modal-body" style={{ maxHeight: '55vh', overflowY: 'auto' }}>
          {error && (
            <div className="modal-error-banner">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {copiedNotice && (
            <div className="modal-success-banner">
              <span>✓</span>
              <span>{copiedNotice}</span>
            </div>
          )}

          {activeTab === 'image' && (
            <div className="export-action-grid">
              <div className="export-card">
                <div className="export-card-icon">📸</div>
                <h4>High-Resolution PNG</h4>
                <p>Captures the complete visual layout with dark wireframe styling for reviews and presentations.</p>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={isExporting}
                  onClick={handleExportPNG}
                >
                  {isExporting ? 'Capturing PNG...' : 'Download PNG Image'}
                </button>
              </div>

              <div className="export-card">
                <div className="export-card-icon">📄</div>
                <h4>Landscape PDF Document</h4>
                <p>Generates an architectural wireframe PDF document ready for client documentation and approvals.</p>
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={isExporting}
                  onClick={handleExportPDF}
                >
                  {isExporting ? 'Generating PDF...' : 'Download PDF Wireframe'}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'mermaid' && (
            <div className="export-text-view">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Mermaid syntax representing {nodes.length} nodes and {edges.length} connections:
                </span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button type="button" className="btn btn-secondary btn-xs" onClick={handleCopyMermaid}>
                    📋 Copy Text
                  </button>
                  <button type="button" className="btn btn-primary btn-xs" onClick={handleDownloadMermaid}>
                    📥 Download .mmd
                  </button>
                </div>
              </div>
              <textarea
                className="form-textarea"
                rows={12}
                value={mermaidText}
                readOnly
                style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
              />
            </div>
          )}

          {activeTab === 'csv' && (
            <div className="export-text-view">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Tabular CSV matrix of all from/to connections, button labels, and node statuses:
                </span>
                <button type="button" className="btn btn-primary btn-xs" onClick={handleDownloadCSV}>
                  📥 Download CSV File
                </button>
              </div>
              <textarea
                className="form-textarea"
                rows={12}
                value={csvText}
                readOnly
                style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
              />
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default WireframeExportModal;
