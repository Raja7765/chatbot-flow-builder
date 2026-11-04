import React, { useState } from 'react';
import ChatbotPreview from './ChatbotPreview';

/**
 * FigmaPropertiesPanel Component
 * Right-side panel with tabs:
 * 1. "Chatbot Preview": Miniature rendition of NABH QMitra chatbot (nabh.corover.ai).
 * 2. "Properties": Clean node properties inspector adhering to Figma design principles.
 */
const FigmaPropertiesPanel = ({
  selectedNode,
  nodes = [],
  edges = [],
  onSelectNode,
  onUpdateNode,
  onDeleteNode,
}) => {
  const [activeTab, setActiveTab] = useState('preview'); // 'preview' | 'properties'

  const id = selectedNode?.id;
  const type = selectedNode?.type;
  const data = selectedNode?.data || {};

  const handleFieldChange = (field, value) => {
    if (!id || typeof onUpdateNode !== 'function') return;
    onUpdateNode(id, {
      ...data,
      [field]: value,
    });
  };

  const isLandingPage =
    type === 'landing_page' ||
    type === 'landing' ||
    id === 'landing_page';

  const getTypeTagColor = (nodeType) => {
    switch (nodeType) {
      case 'landing_page':
      case 'landing':
        return { color: '#0284C7', bg: '#E0F2FE', label: 'Landing Page' };
      case 'start':
        return { color: '#10B981', bg: '#ECFDF5', label: 'Start' };
      case 'menu':
        return { color: '#0D99FF', bg: '#E8F5FF', label: 'Menu' };
      case 'rag':
      case 'answer':
        return { color: '#0D9488', bg: '#F0FDFA', label: 'RAG / Answer' };
      case 'form':
        return { color: '#F97316', bg: '#FFF7ED', label: 'Form' };
      case 'content':
        return { color: '#8B5CF6', bg: '#F5F3FF', label: 'Content' };
      case 'message':
      default:
        return { color: '#6B7280', bg: '#F3F4F6', label: 'Message' };
    }
  };

  const tag = getTypeTagColor(type);

  return (
    <aside className="figma-right-panel">
      {/* Right Panel Tabs Header */}
      <div className="panel-tabs-header right-panel-tabs">
        <button
          type="button"
          className={`panel-tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveTab('preview')}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <span>Chatbot Preview</span>
        </button>
        <button
          type="button"
          className={`panel-tab-btn ${activeTab === 'properties' ? 'active' : ''}`}
          onClick={() => setActiveTab('properties')}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
          <span>Properties</span>
        </button>
      </div>

      {/* Tab 1: Chatbot Preview */}
      {activeTab === 'preview' && (
        <ChatbotPreview
          selectedNode={selectedNode}
          nodes={nodes}
          edges={edges}
          onSelectNode={onSelectNode}
          onSwitchToProperties={() => setActiveTab('properties')}
        />
      )}

      {/* Tab 2: Node Properties Inspector */}
      {activeTab === 'properties' && (
        <>
          {!selectedNode ? (
            <div className="properties-empty-state">
              <div className="properties-empty-icon">👆</div>
              <div className="properties-empty-text">
                Select a node on the canvas to view and configure its properties.
              </div>
            </div>
          ) : (
            <>
              {/* Properties Section Header */}
              <div className="properties-panel-header">
                <span className="properties-panel-title">Properties</span>
                <span
                  style={{
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    color: tag.color,
                    background: tag.bg,
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    border: `1px solid ${tag.color}40`,
                  }}
                >
                  {tag.label}
                </span>
              </div>

              <div className="properties-content">
                {/* Node Identifier */}
                <div className="figma-form-group">
                  <span className="figma-label">Node ID</span>
                  <div
                    style={{
                      fontSize: '0.75rem',
                      fontFamily: 'monospace',
                      color: 'var(--text-secondary)',
                      background: 'var(--panel-hover)',
                      padding: '5px 8px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-color)',
                    }}
                  >
                    {id}
                  </div>
                </div>

                {/* Step Label */}
                <div className="figma-form-group">
                  <label className="figma-label" htmlFor="prop-label">
                    Step Label
                  </label>
                  <input
                    id="prop-label"
                    type="text"
                    className="figma-input"
                    value={data.label || data.name || data.title || ''}
                    onChange={(e) => handleFieldChange('label', e.target.value)}
                    placeholder="Step label..."
                  />
                </div>

                {/* LANDING PAGE SPECIFIC CONFIGURATION */}
                {isLandingPage ? (
                  <>
                    <div className="figma-form-group">
                      <label className="figma-label" htmlFor="prop-heading">
                        Welcome Heading
                      </label>
                      <input
                        id="prop-heading"
                        type="text"
                        className="figma-input"
                        value={data.heading || 'Welcome to QMitra'}
                        onChange={(e) => handleFieldChange('heading', e.target.value)}
                        placeholder="e.g. Welcome to QMitra"
                      />
                    </div>

                    <div className="figma-form-group">
                      <label className="figma-label" htmlFor="prop-subtitle">
                        Subtitle
                      </label>
                      <input
                        id="prop-subtitle"
                        type="text"
                        className="figma-input"
                        value={data.subtitle || 'Your Trusted Healthcare Virtual Assistant'}
                        onChange={(e) => handleFieldChange('subtitle', e.target.value)}
                        placeholder="e.g. Your Trusted Healthcare Virtual Assistant"
                      />
                    </div>

                    <div className="figma-form-group">
                      <label className="figma-label" htmlFor="prop-card-title">
                        Card Heading
                      </label>
                      <input
                        id="prop-card-title"
                        type="text"
                        className="figma-input"
                        value={data.card_title || 'Ready to assist you!'}
                        onChange={(e) => handleFieldChange('card_title', e.target.value)}
                        placeholder="e.g. Ready to assist you!"
                      />
                    </div>

                    <div className="figma-form-group">
                      <label className="figma-label" htmlFor="prop-card-desc">
                        Card Description
                      </label>
                      <textarea
                        id="prop-card-desc"
                        className="figma-textarea"
                        value={data.card_description || 'I can help you with healthcare information'}
                        onChange={(e) => handleFieldChange('card_description', e.target.value)}
                        placeholder="Card description..."
                        rows={2}
                      />
                    </div>

                    <div className="figma-form-group">
                      <label className="figma-label" htmlFor="prop-btn-label">
                        Button Label
                      </label>
                      <input
                        id="prop-btn-label"
                        type="text"
                        className="figma-input"
                        value={data.button_label || 'Get Started'}
                        onChange={(e) => {
                          handleFieldChange('button_label', e.target.value);
                          if (Array.isArray(data.buttons) && data.buttons.length > 0) {
                            const updated = [...data.buttons];
                            updated[0] = { ...updated[0], label: e.target.value };
                            handleFieldChange('buttons', updated);
                          }
                        }}
                        placeholder="e.g. Get Started"
                      />
                    </div>
                  </>
                ) : (
                  /* STANDARD CONVERSATION NODE FIELDS */
                  <>
                    {/* Message / Content */}
                    <div className="figma-form-group">
                      <label className="figma-label" htmlFor="prop-message">
                        Message
                      </label>
                      <textarea
                        id="prop-message"
                        className="figma-textarea"
                        value={data.message || data.content || data.text || data.description || ''}
                        onChange={(e) => {
                          handleFieldChange('message', e.target.value);
                        }}
                        placeholder={
                          data.program || data.topic
                            ? `RAG: ${[data.chapter, data.program, data.topic].filter(Boolean).join(' — ')}`
                            : 'Message text...'
                        }
                        rows={3}
                      />
                    </div>
                  </>
                )}

                {/* RAG Metadata (if available) */}
                {(data.program || data.topic || data.chapter) && (
                  <div className="figma-form-group">
                    <span className="figma-label">RAG Scope</span>
                    <div
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-secondary)',
                        background: 'var(--panel-hover)',
                        padding: '6px 8px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-color)',
                        lineHeight: 1.4,
                      }}
                    >
                      {[
                        data.chapter && `Chapter: ${data.chapter}`,
                        data.program && `Program: ${data.program}`,
                        data.topic && `Topic: ${data.topic}`,
                      ]
                        .filter(Boolean)
                        .join(' • ')}
                    </div>
                  </div>
                )}

                {/* Buttons summary if present */}
                {Array.isArray(data.buttons) && data.buttons.length > 0 && (
                  <div className="figma-form-group">
                    <span className="figma-label">Buttons ({data.buttons.length})</span>
                    <div
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-secondary)',
                        background: 'var(--panel-hover)',
                        padding: '6px 8px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-color)',
                        maxHeight: '80px',
                        overflowY: 'auto',
                        lineHeight: 1.4,
                      }}
                    >
                      {data.buttons.map((b) => b.label || 'Option').join(', ')}
                    </div>
                  </div>
                )}

                {/* Status */}
                <div className="figma-form-group">
                  <label className="figma-label" htmlFor="prop-status">
                    Status
                  </label>
                  <select
                    id="prop-status"
                    className="figma-select"
                    value={data.status || 'NORMAL'}
                    onChange={(e) => handleFieldChange('status', e.target.value === 'NORMAL' ? '' : e.target.value)}
                  >
                    <option value="NORMAL">Normal</option>
                    <option value="PENDING">Pending Confirmation</option>
                    <option value="DRAFT">Draft</option>
                    <option value="CONFIRMED">Confirmed</option>
                  </select>
                </div>

                {/* Note */}
                <div className="figma-form-group">
                  <label className="figma-label" htmlFor="prop-note">
                    Note
                  </label>
                  <textarea
                    id="prop-note"
                    className="figma-textarea"
                    value={data.note || ''}
                    onChange={(e) => handleFieldChange('note', e.target.value)}
                    placeholder="Internal flow note..."
                    rows={2}
                  />
                </div>

                {/* Delete Node Action */}
                <div style={{ marginTop: 'auto', paddingTop: '16px' }}>
                  <button
                    type="button"
                    className="btn-figma-secondary"
                    style={{ width: '100%', color: '#EF4444', borderColor: '#FCA5A5', justifyContent: 'center' }}
                    onClick={() => onDeleteNode(id)}
                  >
                    Delete Node
                  </button>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </aside>
  );
};

export default React.memo(FigmaPropertiesPanel);
