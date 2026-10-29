import React, { useState, useRef } from 'react';
import { normalizeFlow } from '../utils/normalizeFlow';

/**
 * ImportFlowModal Component
 * Allows users to import flow JSON via file picker or raw paste.
 * Normalizes the flow, validates targets and orphans, and triggers the validation review modal.
 */
const ImportFlowModal = ({ isOpen, onClose, onImportAnalyzed }) => {
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'paste'
  const [jsonText, setJsonText] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
      const reader = new FileReader();
      reader.onload = (event) => {
        setJsonText(event.target?.result || '');
      };
      reader.onerror = () => {
        setError('Failed to read the selected file.');
      };
      reader.readAsText(file);
    }
  };

  const handleProcessImport = () => {
    if (!jsonText.trim()) {
      setError('Please select a JSON file or paste flow JSON content.');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const parsed = JSON.parse(jsonText);
      const normalizedResult = normalizeFlow(parsed);
      setIsProcessing(false);
      onImportAnalyzed(normalizedResult);
    } catch (err) {
      setIsProcessing(false);
      setError(`Invalid JSON Syntax: ${err.message}`);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-container import-flow-modal"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '640px', width: '90%' }}
      >
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-icon" aria-hidden="true">📥</span>
            <div>
              <h3>Import Flow JSON</h3>
              <p className="modal-subtitle">
                Import large chatbot conversation diagrams (e.g. NABH QMitra) with automatic edge reconstruction.
              </p>
            </div>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="import-tabs-bar">
          <button
            type="button"
            className={`import-tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => { setActiveTab('upload'); setError(null); }}
          >
            📁 File Upload
          </button>
          <button
            type="button"
            className={`import-tab-btn ${activeTab === 'paste' ? 'active' : ''}`}
            onClick={() => { setActiveTab('paste'); setError(null); }}
          >
            📋 Paste JSON
          </button>
        </div>

        <div className="modal-body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
          {error && (
            <div className="modal-error-banner" role="alert">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {activeTab === 'upload' ? (
            <div className="import-upload-zone" onClick={() => fileInputRef.current?.click()}>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
              <div className="upload-zone-content">
                <span className="upload-cloud-icon">☁️</span>
                <div className="upload-primary-text">
                  {selectedFile ? selectedFile.name : 'Click to select or drag & drop flow JSON'}
                </div>
                <div className="upload-sub-text">
                  Supports nabh_qmitra_flow.json and standard flow structures
                </div>
                {selectedFile && (
                  <div className="upload-file-size">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="import-json-paste">Paste Flow JSON</label>
              <textarea
                id="import-json-paste"
                className="form-textarea import-json-textarea"
                rows={12}
                value={jsonText}
                onChange={(e) => { setJsonText(e.target.value); setError(null); }}
                placeholder='Paste raw JSON containing nodes[...] and buttons[{label, next}]...'
              />
            </div>
          )}

          <div className="import-info-callout">
            <span className="info-icon">ℹ️</span>
            <div>
              <strong>Automatic Normalization:</strong> Garbage positions will be ignored,
              edges will be rebuilt uniquely from button targets, and cycle back-edges will be routed cleanly.
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={isProcessing}
            onClick={handleProcessImport}
          >
            {isProcessing ? 'Analyzing Flow...' : 'Analyze & Review Flow ➔'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ImportFlowModal;
