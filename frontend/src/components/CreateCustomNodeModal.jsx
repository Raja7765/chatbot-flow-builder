import React, { useState } from 'react';
import { createNodeDefinition } from '../api/client';

/**
 * Predefined suggested categories for node organization.
 */
const SUGGESTED_CATEGORIES = [
  'General',
  'AI',
  'Logic',
  'Integration',
  'Communication',
  'Data',
  'Tools',
  'Custom',
];

/**
 * Supported field types for configurable node properties.
 */
const FIELD_TYPES = [
  { value: 'string', label: 'Text (String)' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Boolean (Toggle)' },
  { value: 'select', label: 'Dropdown (Select)' },
];

/**
 * CreateCustomNodeModal Component
 * Allows users to define custom reusable node types with configurable fields.
 * Persists the definition directly to the SQLite backend via POST /node-definitions.
 */
const CreateCustomNodeModal = ({ isOpen, onClose, onCreated }) => {
  const [name, setName] = useState('');
  const [nodeType, setNodeType] = useState('');
  const [isTypeManuallyEdited, setIsTypeManuallyEdited] = useState(false);
  const [category, setCategory] = useState('Custom');
  const [description, setDescription] = useState('');
  const [fields, setFields] = useState([
    {
      name: '',
      label: '',
      type: 'string',
      required: false,
      defaultValue: '',
      optionsString: '',
    },
  ]);
  const [buttons, setButtons] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  if (!isOpen) return null;

  // Auto-generate node_type slug from display name if user hasn't typed custom slug
  const handleNameChange = (e) => {
    const val = e.target.value;
    setName(val);
    if (!isTypeManuallyEdited) {
      const slug = val
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '');
      setNodeType(slug);
    }
  };

  const handleNodeTypeChange = (e) => {
    setIsTypeManuallyEdited(true);
    setNodeType(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ''));
  };

  // Manage dynamic configuration fields
  const handleAddField = () => {
    setFields([
      ...fields,
      {
        name: '',
        label: '',
        type: 'string',
        required: false,
        defaultValue: '',
        optionsString: '',
      },
    ]);
  };

  const handleRemoveField = (index) => {
    setFields(fields.filter((_, i) => i !== index));
  };

  const handleFieldChange = (index, key, value) => {
    const updated = [...fields];
    updated[index] = { ...updated[index], [key]: value };

    // Auto-fill field name if empty when typing label
    if (key === 'label' && !updated[index].name) {
      updated[index].name = value
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '');
    }
    setFields(updated);
  };

  // Manage button configurations (outgoing branches)
  const handleAddButton = () => {
    const nextIdx = buttons.length + 1;
    let newId = `btn_${nextIdx}`;
    let counter = nextIdx;
    while (buttons.some((b) => b.id === newId)) {
      counter++;
      newId = `btn_${counter}`;
    }
    setButtons([...buttons, { id: newId, label: '', isIdCustomized: false }]);
  };

  const handleRemoveButton = (index) => {
    setButtons(buttons.filter((_, i) => i !== index));
  };

  const handleButtonChange = (index, key, value) => {
    const updated = [...buttons];
    updated[index] = { ...updated[index], [key]: value };

    // Auto-generate clean slug ID from label if user hasn't typed custom ID
    if (key === 'label' && !updated[index].isIdCustomized) {
      const slug = value
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '');
      if (slug) {
        updated[index].id = `btn_${slug}`;
      }
    }
    if (key === 'id') {
      updated[index].isIdCustomized = true;
    }
    setButtons(updated);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const trimmedName = name.trim();
    const trimmedType = nodeType.trim();

    if (!trimmedName) {
      setErrorMessage('Node Name is required.');
      return;
    }

    if (!trimmedType) {
      setErrorMessage('Node Type identifier is required.');
      return;
    }

    // Validate fields
    const validFields = [];
    for (const f of fields) {
      const fName = f.name.trim();
      const fLabel = f.label.trim();
      if (!fName && !fLabel) continue; // Skip empty row

      if (!fName) {
        setErrorMessage('Each configurable field must have a technical Field Name.');
        return;
      }

      let parsedDefault = f.defaultValue;
      if (f.type === 'number') {
        parsedDefault = f.defaultValue !== '' ? Number(f.defaultValue) : 0;
      } else if (f.type === 'boolean') {
        parsedDefault = Boolean(f.defaultValue === true || f.defaultValue === 'true');
      }

      let parsedOptions = undefined;
      if (f.type === 'select') {
        parsedOptions = (f.optionsString || '')
          .split(',')
          .map((opt) => opt.trim())
          .filter(Boolean);
        if (parsedOptions.length === 0) {
          parsedOptions = ['Option 1', 'Option 2'];
        }
      }

      validFields.push({
        name: fName,
        label: fLabel || fName,
        type: f.type,
        required: Boolean(f.required),
        default: parsedDefault,
        ...(parsedOptions ? { options: parsedOptions } : {}),
      });
    }

    // Validate button configurations
    const validButtons = [];
    const seenButtonIds = new Set();
    for (let i = 0; i < buttons.length; i++) {
      const b = buttons[i];
      const bLabel = (b.label || '').trim();
      let bId = (b.id || '').trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_');

      if (!bLabel) {
        setErrorMessage(`Button #${i + 1} must have a label (e.g. "About NABH").`);
        return;
      }
      if (!bId) {
        bId = `btn_${i + 1}`;
      }
      if (seenButtonIds.has(bId)) {
        setErrorMessage(`Duplicate button ID "${bId}" found. Every button must have a unique ID.`);
        return;
      }
      seenButtonIds.add(bId);
      validButtons.push({ id: bId, label: bLabel });
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const payload = {
      name: trimmedName,
      node_type: trimmedType,
      category: category.trim() || 'Custom',
      description: description.trim() || undefined,
      config_schema: {
        fields: validFields,
        buttons: validButtons,
      },
      input_schema: { properties: {} },
      output_schema: { properties: {} },
    };

    try {
      const created = await createNodeDefinition(payload);
      if (onCreated) {
        onCreated(created);
      }
      onClose();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create custom node definition.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={isSubmitting ? undefined : onClose}>
      <div
        className="modal-content custom-node-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="custom-node-modal-title"
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.25rem' }}>🧩</span>
            <div>
              <h3 id="custom-node-modal-title">Create Custom Node Definition</h3>
              <span style={{ fontSize: '0.725rem', color: '#a855f7', fontWeight: 500 }}>
                Define reusable node with custom properties for your flows
              </span>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: '4px 8px' }}
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="modal-body">
            {/* Error Message */}
            {errorMessage && (
              <div className="modal-alert modal-alert-error" role="alert">
                <span style={{ fontSize: '1.2rem' }}>⚠️</span>
                <div style={{ flex: 1 }}>
                  <strong>Error:</strong>
                  <p style={{ marginTop: '2px', fontSize: '0.8rem' }}>{errorMessage}</p>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-xs"
                  onClick={() => setErrorMessage(null)}
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Basic Info Grid */}
            <div className="form-row-2col">
              <div className="form-group">
                <label htmlFor="custom-node-name">
                  Node Name <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  id="custom-node-name"
                  type="text"
                  className="form-input"
                  value={name}
                  onChange={handleNameChange}
                  placeholder="e.g. Sentiment Analyzer"
                  disabled={isSubmitting}
                  autoFocus
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="custom-node-type">
                  Unique Node Type Slug <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  id="custom-node-type"
                  type="text"
                  className="form-input"
                  value={nodeType}
                  onChange={handleNodeTypeChange}
                  placeholder="e.g. sentiment_analyzer"
                  disabled={isSubmitting}
                  required
                />
              </div>
            </div>

            {/* Category & Description */}
            <div className="form-group" style={{ marginTop: '12px' }}>
              <label htmlFor="custom-node-category">Category</label>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <select
                  id="custom-node-category"
                  className="modal-filter-select"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  disabled={isSubmitting}
                  style={{ width: '160px' }}
                >
                  {SUGGESTED_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Or enter custom category..."
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="form-group" style={{ marginTop: '12px' }}>
              <label htmlFor="custom-node-desc">Description (Optional)</label>
              <textarea
                id="custom-node-desc"
                className="form-textarea"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What does this custom flow step do?..."
                rows={2}
                disabled={isSubmitting}
              />
            </div>

            {/* Configurable Properties Builder */}
            <div className="custom-fields-section" style={{ marginTop: '16px' }}>
              <div className="custom-fields-header">
                <div>
                  <h4 style={{ fontSize: '0.875rem', fontWeight: 600 }}>Configurable Fields</h4>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                    Fields user can configure in the Properties Panel when selecting this node
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-xs"
                  onClick={handleAddField}
                  disabled={isSubmitting}
                >
                  ➕ Add Field
                </button>
              </div>

              <div className="custom-fields-list">
                {fields.map((field, idx) => (
                  <div key={idx} className="custom-field-row">
                    <div className="field-grid">
                      <div className="form-group">
                        <label style={{ fontSize: '0.7rem' }}>Display Label</label>
                        <input
                          type="text"
                          className="form-input form-input-sm"
                          value={field.label}
                          onChange={(e) => handleFieldChange(idx, 'label', e.target.value)}
                          placeholder="e.g. API Secret Key"
                        />
                      </div>

                      <div className="form-group">
                        <label style={{ fontSize: '0.7rem' }}>Field Name (ID)</label>
                        <input
                          type="text"
                          className="form-input form-input-sm"
                          value={field.name}
                          onChange={(e) => handleFieldChange(idx, 'name', e.target.value)}
                          placeholder="e.g. api_key"
                        />
                      </div>

                      <div className="form-group">
                        <label style={{ fontSize: '0.7rem' }}>Type</label>
                        <select
                          className="modal-filter-select form-input-sm"
                          value={field.type}
                          onChange={(e) => handleFieldChange(idx, 'type', e.target.value)}
                        >
                          {FIELD_TYPES.map((t) => (
                            <option key={t.value} value={t.value}>
                              {t.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="form-group">
                        <label style={{ fontSize: '0.7rem' }}>Default Value</label>
                        {field.type === 'boolean' ? (
                          <select
                            className="modal-filter-select form-input-sm"
                            value={String(field.defaultValue)}
                            onChange={(e) => handleFieldChange(idx, 'defaultValue', e.target.value === 'true')}
                          >
                            <option value="false">False</option>
                            <option value="true">True</option>
                          </select>
                        ) : (
                          <input
                            type={field.type === 'number' ? 'number' : 'text'}
                            className="form-input form-input-sm"
                            value={field.defaultValue}
                            onChange={(e) => handleFieldChange(idx, 'defaultValue', e.target.value)}
                            placeholder={field.type === 'number' ? '0' : 'Default text...'}
                          />
                        )}
                      </div>
                    </div>

                    {field.type === 'select' && (
                      <div className="form-group" style={{ marginTop: '6px' }}>
                        <label style={{ fontSize: '0.7rem' }}>Dropdown Options (comma-separated)</label>
                        <input
                          type="text"
                          className="form-input form-input-sm"
                          value={field.optionsString}
                          onChange={(e) => handleFieldChange(idx, 'optionsString', e.target.value)}
                          placeholder="e.g. Low, Medium, High"
                        />
                      </div>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={field.required}
                          onChange={(e) => handleFieldChange(idx, 'required', e.target.checked)}
                        />
                        <span>Required field</span>
                      </label>
                      {fields.length > 1 && (
                        <button
                          type="button"
                          className="btn-danger-subtle"
                          onClick={() => handleRemoveField(idx)}
                          title="Remove field"
                        >
                          🗑️ Remove
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Button Configuration Section */}
            <div className="custom-fields-section" style={{ marginTop: '16px' }}>
              <div className="custom-fields-header">
                <div>
                  <h4 style={{ fontSize: '0.875rem', fontWeight: 600 }}>Button Configuration</h4>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                    Add interactive buttons that branch to different destination steps (e.g. About NABH, Accreditation, Ask a Question)
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary btn-xs"
                  onClick={handleAddButton}
                  disabled={isSubmitting}
                >
                  ➕ Add Button
                </button>
              </div>

              <div className="custom-buttons-list" style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                {buttons.length === 0 ? (
                  <div className="custom-fields-empty" style={{ padding: '12px', fontSize: '0.78rem' }}>
                    No buttons configured. This node will use standard single outgoing handle. Click <strong>➕ Add Button</strong> to add branching buttons.
                  </div>
                ) : (
                  buttons.map((btn, idx) => (
                    <div
                      key={idx}
                      className="custom-button-config-card"
                      style={{
                        background: '#101a2b',
                        border: '1px solid rgba(99, 102, 241, 0.25)',
                        borderRadius: '6px',
                        padding: '10px 12px',
                      }}
                    >
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '1fr 140px 36px',
                          gap: '10px',
                          alignItems: 'flex-end',
                        }}
                      >
                        <div className="form-group" style={{ margin: 0 }}>
                          <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            Button Label <span style={{ color: '#ef4444' }}>*</span>
                          </label>
                          <input
                            type="text"
                            className="form-input form-input-sm"
                            value={btn.label}
                            onChange={(e) => handleButtonChange(idx, 'label', e.target.value)}
                            placeholder="e.g. About NABH"
                          />
                        </div>

                        <div className="form-group" style={{ margin: 0 }}>
                          <label style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            Button ID
                          </label>
                          <input
                            type="text"
                            className="form-input form-input-sm"
                            style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                            value={btn.id}
                            onChange={(e) => handleButtonChange(idx, 'id', e.target.value)}
                            placeholder="btn_1"
                          />
                        </div>

                        <button
                          type="button"
                          className="btn-danger-subtle"
                          style={{
                            height: '32px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                          onClick={() => handleRemoveButton(idx)}
                          title="Remove button"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting || !name.trim() || !nodeType.trim()}
              style={{ minWidth: '150px' }}
            >
              {isSubmitting ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <span className="save-spinner" aria-hidden="true" />
                  <span>Creating Node...</span>
                </span>
              ) : (
                '🧩 Create Node'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateCustomNodeModal;
