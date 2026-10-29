import React, { useState } from 'react';

/**
 * ValidationReportModal Component
 * Displays a comprehensive graph validation report on import:
 * - Missing target nodes
 * - Orphan nodes
 * - Non-terminal dead-ends
 * - Duplicate IDs
 * - Buttons without next
 * Provides one-click action to execute DAG auto-layout and load the flow.
 */
const ValidationReportModal = ({
  isOpen,
  onClose,
  validationData,
  onApplyAndLoad,
}) => {
  const [activeSection, setActiveSection] = useState('summary');
  const [collapseDeepLevels, setCollapseDeepLevels] = useState(true);

  if (!isOpen || !validationData) return null;

  const { validation, nodes, edges, flowName } = validationData;
  const {
    totalNodes,
    totalEdges,
    missingTargetNodes = [],
    orphanNodes = [],
    deadEndNodes = [],
    duplicateIds = [],
    buttonsWithoutNext = [],
  } = validation || {};

  const totalWarnings =
    missingTargetNodes.length +
    orphanNodes.length +
    deadEndNodes.length +
    duplicateIds.length +
    buttonsWithoutNext.length;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-container validation-report-modal"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '780px', width: '92%' }}
      >
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-icon" aria-hidden="true">
              {totalWarnings === 0 ? '✅' : '📊'}
            </span>
            <div>
              <h3>Import Validation Report: {flowName || 'Flow'}</h3>
              <p className="modal-subtitle">
                Reconstructed {totalEdges} connection branches across {totalNodes} conversation nodes.
              </p>
            </div>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        {/* Summary Metrics Bar */}
        <div className="validation-metrics-grid">
          <div className="metric-card">
            <span className="metric-val text-emerald">{totalNodes}</span>
            <span className="metric-lbl">Total Nodes</span>
          </div>
          <div className="metric-card">
            <span className="metric-val text-purple">{totalEdges}</span>
            <span className="metric-lbl">Rebuilt Edges</span>
          </div>
          <div className="metric-card">
            <span className={`metric-val ${missingTargetNodes.length > 0 ? 'text-rose' : 'text-slate'}`}>
              {missingTargetNodes.length}
            </span>
            <span className="metric-lbl">Missing Targets</span>
          </div>
          <div className="metric-card">
            <span className={`metric-val ${orphanNodes.length > 0 ? 'text-amber' : 'text-slate'}`}>
              {orphanNodes.length}
            </span>
            <span className="metric-lbl">Orphan Nodes</span>
          </div>
          <div className="metric-card">
            <span className={`metric-val ${buttonsWithoutNext.length > 0 ? 'text-amber' : 'text-slate'}`}>
              {buttonsWithoutNext.length}
            </span>
            <span className="metric-lbl">Unlinked Buttons</span>
          </div>
        </div>

        {/* Section Navigation Tabs */}
        <div className="validation-tabs-row">
          <button
            type="button"
            className={`val-tab-btn ${activeSection === 'summary' ? 'active' : ''}`}
            onClick={() => setActiveSection('summary')}
          >
            Overview
          </button>
          <button
            type="button"
            className={`val-tab-btn ${activeSection === 'missing' ? 'active' : ''}`}
            onClick={() => setActiveSection('missing')}
          >
            Missing Targets ({missingTargetNodes.length})
          </button>
          <button
            type="button"
            className={`val-tab-btn ${activeSection === 'orphans' ? 'active' : ''}`}
            onClick={() => setActiveSection('orphans')}
          >
            Orphans ({orphanNodes.length})
          </button>
          <button
            type="button"
            className={`val-tab-btn ${activeSection === 'unlinked' ? 'active' : ''}`}
            onClick={() => setActiveSection('unlinked')}
          >
            Unlinked Buttons ({buttonsWithoutNext.length})
          </button>
          <button
            type="button"
            className={`val-tab-btn ${activeSection === 'deadends' ? 'active' : ''}`}
            onClick={() => setActiveSection('deadends')}
          >
            Dead Ends ({deadEndNodes.length})
          </button>
        </div>

        {/* Tab Content Body */}
        <div className="modal-body validation-report-body" style={{ maxHeight: '42vh', overflowY: 'auto' }}>
          {activeSection === 'summary' && (
            <div className="validation-summary-view">
              <div className="val-callout success">
                <strong>✓ Edge Rebuilding Complete:</strong> All connections have been reconstructed
                strictly from button targets with stable, immutable handle IDs.
              </div>

              {totalWarnings > 0 ? (
                <div className="val-callout warning">
                  <strong>Notice:</strong> Found {totalWarnings} flow notices (missing targets, orphans, or unlinked buttons).
                  You can safely load the flow onto the canvas; unconnected branches will be highlighted with ⚠️ warning badges for easy editing.
                </div>
              ) : (
                <div className="val-callout success">
                  <strong>Perfect Graph:</strong> No missing targets, orphan nodes, or unlinked buttons detected!
                </div>
              )}

              <div className="validation-settings-box">
                <label className="checkbox-setting-label">
                  <input
                    type="checkbox"
                    checked={collapseDeepLevels}
                    onChange={(e) => setCollapseDeepLevels(e.target.checked)}
                  />
                  <span>
                    <strong>Initial High-Level View:</strong> Collapse descendant nodes beyond level 3
                    by default (click any node's expand toggle to reveal deeper sub-menus).
                  </span>
                </label>
              </div>
            </div>
          )}

          {activeSection === 'missing' && (
            <div className="val-issue-list">
              {missingTargetNodes.length === 0 ? (
                <div className="empty-val-msg">✓ No missing target nodes found.</div>
              ) : (
                missingTargetNodes.map((item, idx) => (
                  <div key={idx} className="val-issue-card rose">
                    <div className="issue-title">
                      Source Node: <strong>{item.sourceLabel || item.sourceId}</strong>
                    </div>
                    <div className="issue-desc">
                      Button <code>"{item.buttonLabel}"</code> points to non-existent target ID: <code>{item.targetId}</code>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeSection === 'orphans' && (
            <div className="val-issue-list">
              {orphanNodes.length === 0 ? (
                <div className="empty-val-msg">✓ No orphan nodes found.</div>
              ) : (
                orphanNodes.map((item, idx) => (
                  <div key={idx} className="val-issue-card amber">
                    <div className="issue-title">
                      Orphan Node: <strong>{item.label}</strong> (<code>{item.id}</code>)
                    </div>
                    <div className="issue-desc">
                      Type: <code>{item.type}</code> — No incoming connections route to this node.
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeSection === 'unlinked' && (
            <div className="val-issue-list">
              {buttonsWithoutNext.length === 0 ? (
                <div className="empty-val-msg">✓ All buttons have destination targets.</div>
              ) : (
                buttonsWithoutNext.map((item, idx) => (
                  <div key={idx} className="val-issue-card amber">
                    <div className="issue-title">
                      Node: <strong>{item.nodeLabel}</strong>
                    </div>
                    <div className="issue-desc">
                      Button <code>"{item.buttonLabel}"</code> has no <code>next</code> destination configured.
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeSection === 'deadends' && (
            <div className="val-issue-list">
              {deadEndNodes.length === 0 ? (
                <div className="empty-val-msg">✓ No unexpected dead-end nodes found.</div>
              ) : (
                deadEndNodes.map((item, idx) => (
                  <div key={idx} className="val-issue-card slate">
                    <div className="issue-title">
                      Non-Terminal Node: <strong>{item.label}</strong> (<code>{item.id}</code>)
                    </div>
                    <div className="issue-desc">
                      Type: <code>{item.type}</code> — Has 0 outgoing choices and is not an Answer node.
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary btn-lg"
            onClick={() => onApplyAndLoad(collapseDeepLevels)}
          >
            ⚡ Apply Auto-Layout &amp; Load Canvas ({totalNodes} Nodes)
          </button>
        </div>
      </div>
    </div>
  );
};

export default ValidationReportModal;
