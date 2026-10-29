import React, { useState } from 'react';

const ExportModal = ({ isOpen, onClose, flowPayload, title = 'Flow Data JSON' }) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const jsonString = JSON.stringify(flowPayload, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `flow-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: '4px 8px' }}
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        <div className="modal-body">
          <p style={{ fontSize: '0.825rem', color: '#94a3b8', marginBottom: '12px' }}>
            This schema is 100% compatible with the FastAPI backend <code>POST /flows</code> and <code>PUT /flows/{'{flow_id}'}</code> endpoints:
          </p>
          <pre className="json-preview">{jsonString}</pre>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={handleDownload}>
            💾 Download File
          </button>
          <button type="button" className="btn btn-primary" onClick={handleCopy}>
            {copied ? '✅ Copied!' : '📋 Copy JSON'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExportModal;
