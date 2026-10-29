import React from 'react';

/**
 * FigmaPropertiesPanel Component
 * 280px wide clean properties inspector adhering to Figma design principles:
 * - Clean section headers
 * - Small, readable labels with 1px border inputs
 * - Empty state when no node is selected
 */
const FigmaPropertiesPanel = ({
  selectedNode,
  onUpdateNode,
  onDeleteNode,
}) => {
  if (!selectedNode) {
    return (
      <aside className="figma-right-panel">
        <div className="properties-panel-header">
          <span className="properties-panel-title">Properties</span>
        </div>
        <div className="properties-empty-state">
          <div className="properties-empty-icon">👆</div>
          <div className="properties-empty-text">
            Select a node on the canvas to view and configure its properties.
          </div>
        </div>
      </aside>
    );
  }

  const { id, type, data = {} } = selectedNode;

  const handleFieldChange = (field, value) => {
    onUpdateNode(id, {
      ...data,
      [field]: value,
    });
  };

  const getTypeTagColor = (nodeType) => {
    switch (nodeType) {
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
      {/* Header */}
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
            Label
          </label>
          <input
            id="prop-label"
            type="text"
            className="figma-input"
            value={data.label || ''}
            onChange={(e) => handleFieldChange('label', e.target.value)}
            placeholder="Step label..."
          />
        </div>

        {/* Message / Content */}
        <div className="figma-form-group">
          <label className="figma-label" htmlFor="prop-message">
            Message
          </label>
          <textarea
            id="prop-message"
            className="figma-textarea"
            value={data.message || data.text || ''}
            onChange={(e) => {
              handleFieldChange('message', e.target.value);
              handleFieldChange('text', e.target.value);
            }}
            placeholder="Message text..."
            rows={3}
          />
        </div>

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
    </aside>
  );
};

export default React.memo(FigmaPropertiesPanel);
