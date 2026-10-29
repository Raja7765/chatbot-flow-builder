import React from 'react';

/**
 * PropertiesPanel Component
 * Configures the selected React Flow node on the canvas.
 * Supports all SEBI flow node types: Start, Message, Router, Employee Search,
 * FAQ/RAG Pipeline, SSE Streaming Response, and TTS Audio Generation.
 */
const PropertiesPanel = ({
  selectedNode,
  onUpdateNode,
  onDeleteNode,
  allNodes = [],
  edges = [],
  onAssignButtonDestination,
  onRemoveButtonEdge,
  onUpdateButtonLabel,
  onTracePath,
}) => {
  if (!selectedNode) {
    return (
      <aside className="properties-panel">
        <div className="panel-header">
          <h3>Properties</h3>
        </div>
        <div className="panel-empty">
          <span style={{ fontSize: '28px' }}>👆</span>
          <p>Select a node on the canvas to configure its settings</p>
        </div>
      </aside>
    );
  }

  const { id, type, data = {}, position } = selectedNode;

  // Helper to update a specific property on the selected node's data
  const handleFieldChange = (field, value) => {
    onUpdateNode(id, {
      ...data,
      [field]: value,
    });
  };

  // Input fields management handlers for Message / Form nodes
  const inputFieldsList = Array.isArray(data.fields) ? data.fields : (Array.isArray(data.input_fields) ? data.input_fields : []);

  const handleAddInputField = () => {
    const nextIdx = inputFieldsList.length + 1;
    const newField = {
      id: `field_${Date.now().toString(36)}_${nextIdx}`,
      name: `field_${nextIdx}`,
      label: `Field ${nextIdx}`,
      type: 'text',
      placeholder: `Enter field ${nextIdx}...`,
      required: false,
    };
    handleFieldChange('fields', [...inputFieldsList, newField]);
    handleFieldChange('input_fields', [...inputFieldsList, newField]);
  };

  const handleRemoveInputField = (fieldId, idx) => {
    const updated = inputFieldsList.filter((f, i) => (f.id ? f.id !== fieldId : i !== idx));
    handleFieldChange('fields', updated);
    handleFieldChange('input_fields', updated);
  };

  const handleUpdateInputField = (fieldId, prop, value, idx) => {
    const updated = inputFieldsList.map((f, i) => {
      if ((fieldId && f.id === fieldId) || (!fieldId && i === idx)) {
        return { ...f, [prop]: value };
      }
      return f;
    });
    handleFieldChange('fields', updated);
    handleFieldChange('input_fields', updated);
  };

  const handleAddLoginFormPreset = () => {
    const loginFields = [
      {
        id: `field_mobile_${Date.now().toString(36)}`,
        name: 'mobile',
        label: 'Mobile Number',
        type: 'tel',
        placeholder: 'Enter 10-digit registered mobile',
        required: true,
      },
      {
        id: `field_email_${Date.now().toString(36)}`,
        name: 'email',
        label: 'Email Address',
        type: 'email',
        placeholder: 'hospital@example.com',
        required: true,
      },
    ];
    handleFieldChange('fields', [...inputFieldsList, ...loginFields]);
    handleFieldChange('input_fields', [...inputFieldsList, ...loginFields]);
  };

  // Button management handlers
  const buttonsList = Array.isArray(data.buttons) ? data.buttons : [];

  const handleAddButtonOption = () => {
    const nextIdx = buttonsList.length + 1;
    let newId = `${id}__btn_${nextIdx}`;
    let counter = nextIdx;
    while (buttonsList.some((b) => b.id === newId)) {
      counter++;
      newId = `${id}__btn_${counter}`;
    }
    const newButtons = [...buttonsList, { id: newId, label: `Option ${nextIdx}`, next: '', target: '' }];
    handleFieldChange('buttons', newButtons);
  };

  const handleRemoveButtonOption = (buttonId) => {
    const newButtons = buttonsList.filter((b) => b.id !== buttonId);
    handleFieldChange('buttons', newButtons);
    if (onRemoveButtonEdge) {
      onRemoveButtonEdge(id, buttonId);
    }
  };

  const handleEditButtonLabel = (buttonId, newLabel) => {
    const newButtons = buttonsList.map((b) => {
      if (b.id === buttonId) {
        return { ...b, label: newLabel };
      }
      return b;
    });
    handleFieldChange('buttons', newButtons);
    if (onUpdateButtonLabel) {
      onUpdateButtonLabel(id, buttonId, newLabel);
    }
  };

  const handleMoveButtonUp = (idx) => {
    if (idx <= 0) return;
    const newButtons = [...buttonsList];
    const temp = newButtons[idx - 1];
    newButtons[idx - 1] = newButtons[idx];
    newButtons[idx] = temp;
    handleFieldChange('buttons', newButtons);
  };

  const handleMoveButtonDown = (idx) => {
    if (idx >= buttonsList.length - 1) return;
    const newButtons = [...buttonsList];
    const temp = newButtons[idx + 1];
    newButtons[idx + 1] = newButtons[idx];
    newButtons[idx] = temp;
    handleFieldChange('buttons', newButtons);
  };

  const handleDestinationChange = (buttonId, targetNodeId) => {
    const newButtons = buttonsList.map((b) => {
      if (b.id === buttonId) {
        return { ...b, target: targetNodeId, next: targetNodeId };
      }
      return b;
    });
    handleFieldChange('buttons', newButtons);
    if (onAssignButtonDestination) {
      onAssignButtonDestination(id, buttonId, targetNodeId);
    }
  };

  // Node type display meta
  const getTypeBadge = (nodeType, source) => {
    if (source === 'custom') {
      return { label: `CUSTOM: ${(nodeType || '').toUpperCase()}`, color: '#a855f7', bg: 'rgba(168, 85, 247, 0.15)' };
    }
    switch (nodeType) {
      case 'start':
        return { label: 'START STEP', color: '#10b981', bg: 'rgba(16, 185, 129, 0.2)' };
      case 'menu':
        return { label: 'MENU OPTIONS', color: '#818cf8', bg: 'rgba(129, 140, 248, 0.2)' };
      case 'rag':
        return { label: 'AI RAG ANSWER', color: '#06b6d4', bg: 'rgba(6, 182, 212, 0.2)' };
      case 'message':
        return { label: 'MESSAGE', color: '#7C3AED', bg: 'rgba(124, 58, 237, 0.25)' };
      case 'content':
        return { label: 'CONTENT / MEDIA', color: '#c084fc', bg: 'rgba(192, 132, 252, 0.2)' };
      case 'form':
        return { label: 'FORM / STEPPER', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.2)' };
      case 'answer':
        return { label: 'ANSWER', color: '#164E63', bg: 'rgba(22, 78, 99, 0.35)' };
      case 'router':
        return { label: 'QUERY ROUTER', color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.15)' };
      case 'employee_search':
        return { label: 'EMPLOYEE SEARCH', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' };
      case 'response':
        return { label: 'SSE RESPONSE', color: '#ec4899', bg: 'rgba(236, 72, 153, 0.15)' };
      case 'tts':
        return { label: 'TTS AUDIO', color: '#14b8a6', bg: 'rgba(20, 184, 166, 0.15)' };
      case 'llm':
        return { label: 'LLM GENERATOR', color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.15)' };
      case 'api_request':
        return { label: 'API REQUEST', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' };
      case 'condition':
        return { label: 'CONDITION', color: '#ec4899', bg: 'rgba(236, 72, 153, 0.15)' };
      case 'database':
        return { label: 'DATABASE', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)' };
      default:
        return { label: (nodeType || 'CUSTOM').toUpperCase(), color: '#6366f1', bg: 'rgba(99, 102, 241, 0.15)' };
    }
  };

  const badge = getTypeBadge(type, data.node_source);

  return (
    <aside className="properties-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div>
          <h3>Node Settings</h3>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontFamily: 'monospace' }}>
            ID: {id}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {onTracePath && (
            <button
              type="button"
              className="btn btn-secondary btn-xs"
              onClick={() => onTracePath(id)}
              title="Trace conversation path from root to this node"
              style={{ fontSize: '0.7rem', padding: '3px 7px', background: 'rgba(99, 102, 241, 0.15)', borderColor: 'rgba(99, 102, 241, 0.4)', color: '#a5b4fc' }}
            >
              🧭 Trace
            </button>
          )}
          <span
            className="panel-badge"
            style={{ color: badge.color, background: badge.bg, border: `1px solid ${badge.color}40` }}
          >
            {badge.label}
          </span>
        </div>
      </div>

      {/* 1. Common Field: Step Label */}
      <div className="form-group">
        <label htmlFor="node-label">Step Label (Canvas Display)</label>
        <input
          id="node-label"
          type="text"
          className="form-input"
          value={data.label || ''}
          onChange={(e) => handleFieldChange('label', e.target.value)}
          placeholder="e.g. Query Router"
        />
      </div>

      {/* 2. Common Field: Description / Message */}
      <div className="form-group">
        <label htmlFor="node-description">Description / Note</label>
        <textarea
          id="node-description"
          className="form-textarea"
          value={data.description || ''}
          onChange={(e) => handleFieldChange('description', e.target.value)}
          placeholder="Brief description of this flow step..."
          rows={2}
        />
      </div>

      {/* 2b. Global Flow Flags: Status, Mapping Status, Note */}
      <div className="node-specific-section" style={{ background: 'rgba(15, 23, 42, 0.4)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '6px', padding: '10px', marginBottom: '12px' }}>
        <div className="section-divider-title" style={{ fontSize: '0.75rem', marginBottom: '8px', color: '#94a3b8' }}>
          Flow Status & Mapping Flags
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{ fontSize: '0.68rem' }}>Node Status</label>
            <select
              className="form-input form-input-sm"
              value={data.status || 'NORMAL'}
              onChange={(e) => handleFieldChange('status', e.target.value === 'NORMAL' ? '' : e.target.value)}
            >
              <option value="NORMAL">Normal / Active</option>
              <option value="PENDING">PENDING (Confirmation needed)</option>
              <option value="DRAFT">Draft</option>
              <option value="CONFIRMED">Confirmed</option>
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{ fontSize: '0.68rem' }}>Mapping Status</label>
            <select
              className="form-input form-input-sm"
              value={data.mapping_status || ''}
              onChange={(e) => handleFieldChange('mapping_status', e.target.value)}
            >
              <option value="">None / Unmapped</option>
              <option value="PENDING_VERIFICATION">PENDING_VERIFICATION (Amber)</option>
              <option value="PARTIALLY_MAPPED">PARTIALLY_MAPPED (Orange)</option>
              <option value="INDIVIDUAL_STANDARDS_MAPPED">INDIVIDUAL_STANDARDS_MAPPED (Green)</option>
              <option value="VERIFY_REQUIRED">VERIFY_REQUIRED (Orange)</option>
              <option value="OK">OK / VERIFIED (Green)</option>
            </select>
          </div>
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label style={{ fontSize: '0.68rem' }}>Note / Documentation Flag</label>
          <textarea
            className="form-textarea form-input-sm"
            value={data.note || ''}
            onChange={(e) => handleFieldChange('note', e.target.value)}
            placeholder="e.g. Needs NABH accreditation fee schedule update..."
            rows={2}
          />
        </div>
      </div>

      {/* 3. Node-Specific Configuration */}

      {/* --- MENU NODE --- */}
      {type === 'menu' && (
        <div className="node-specific-section">
          <div className="section-divider-title" style={{ color: '#818cf8' }}>Menu Node Configuration</div>
          <div className="form-group">
            <label htmlFor="menu-message">Menu Prompt / Question</label>
            <textarea
              id="menu-message"
              className="form-textarea"
              value={data.message || data.text || ''}
              onChange={(e) => {
                handleFieldChange('message', e.target.value);
                handleFieldChange('text', e.target.value);
              }}
              placeholder="e.g. Please choose an accreditation category:"
              rows={3}
            />
          </div>
        </div>
      )}

      {/* --- RAG NODE --- */}
      {type === 'rag' && (
        <div className="node-specific-section">
          <div className="section-divider-title" style={{ color: '#06b6d4' }}>AI RAG Answer Configuration</div>
          <div
            style={{
              padding: '8px 10px',
              background: 'rgba(6, 182, 212, 0.12)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              borderRadius: '6px',
              marginBottom: '10px',
              fontSize: '0.72rem',
              color: '#67e8f9',
            }}
          >
            ⚡ Terminal AI Answer node. Sourced from NABH standards & documents. No outgoing handle.
          </div>

          <div className="form-group">
            <label htmlFor="rag-message">AI Answer Content</label>
            <textarea
              id="rag-message"
              className="form-textarea"
              value={data.message || data.answer_text || data.text || ''}
              onChange={(e) => {
                handleFieldChange('message', e.target.value);
                handleFieldChange('answer_text', e.target.value);
                handleFieldChange('text', e.target.value);
              }}
              placeholder="e.g. Accreditation standards require at least 50 general hospital beds..."
              rows={4}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: '0.68rem' }}>Program</label>
              <input
                type="text"
                className="form-input form-input-sm"
                value={data.program || ''}
                onChange={(e) => handleFieldChange('program', e.target.value)}
                placeholder="e.g. Hospital"
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: '0.68rem' }}>Topic</label>
              <input
                type="text"
                className="form-input form-input-sm"
                value={data.topic || ''}
                onChange={(e) => handleFieldChange('topic', e.target.value)}
                placeholder="e.g. eligibility"
              />
            </div>
          </div>

          <div className="form-group">
            <label style={{ fontSize: '0.68rem' }}>Chapter / Standard Reference</label>
            <input
              type="text"
              className="form-input form-input-sm"
              value={data.chapter || ''}
              onChange={(e) => handleFieldChange('chapter', e.target.value)}
              placeholder="e.g. AAC, COP, MOM, PRE"
            />
          </div>
        </div>
      )}

      {/* --- CONTENT NODE --- */}
      {type === 'content' && (
        <div className="node-specific-section">
          <div className="section-divider-title" style={{ color: '#c084fc' }}>Content Dependency Configuration</div>
          <div
            style={{
              padding: '8px 10px',
              background: 'rgba(168, 85, 247, 0.12)',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              borderRadius: '6px',
              marginBottom: '10px',
              fontSize: '0.72rem',
              color: '#d8b4fe',
            }}
          >
            🎨 Content / Media block (testimonials, images, video assets). Flagged for client review.
          </div>

          <div className="form-group">
            <label htmlFor="content-message">Content Caption / Text</label>
            <textarea
              id="content-message"
              className="form-textarea"
              value={data.message || data.text || ''}
              onChange={(e) => {
                handleFieldChange('message', e.target.value);
                handleFieldChange('text', e.target.value);
              }}
              placeholder="e.g. [Infographic: 5-step accreditation journey]"
              rows={3}
            />
          </div>
        </div>
      )}

      {/* --- FORM NODE --- */}
      {type === 'form' && (
        <div className="node-specific-section">
          <div className="section-divider-title" style={{ color: '#38bdf8' }}>Interactive Form / Stepper</div>
          <div className="form-group">
            <label htmlFor="form-message">Form Prompt / Description</label>
            <textarea
              id="form-message"
              className="form-textarea"
              value={data.message || data.description || ''}
              onChange={(e) => {
                handleFieldChange('message', e.target.value);
                handleFieldChange('description', e.target.value);
              }}
              placeholder="e.g. Please enter your facility details to view accurate fees..."
              rows={2}
            />
          </div>

          <div className="form-group">
            <label style={{ fontSize: '0.68rem' }}>Progress Steps (e.g. Step 1 of 3)</label>
            <input
              type="text"
              className="form-input form-input-sm"
              value={Array.isArray(data.progress_steps) ? data.progress_steps.join(', ') : (data.progress_steps || '')}
              onChange={(e) => {
                const parts = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
                handleFieldChange('progress_steps', parts);
              }}
              placeholder="e.g. Step 1: Info, Step 2: Beds, Step 3: Confirmation"
            />
          </div>
        </div>
      )}

      {/* --- START NODE --- */}
      {type === 'start' && (
        <div className="node-specific-section">
          <div className="section-divider-title">Start Node Configuration</div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 12px',
              background: 'rgba(22, 101, 52, 0.25)',
              border: '1px solid rgba(22, 101, 52, 0.5)',
              borderRadius: '6px',
              marginBottom: '12px',
            }}
          >
            <span style={{ fontSize: '18px' }}>🟢</span>
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#4ade80' }}>
                Conversation Entrypoint
              </div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                Initiates the chatbot flow when the conversation starts.
              </div>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="start-text">Trigger Context / Description</label>
            <textarea
              id="start-text"
              className="form-textarea"
              value={data.text || data.message || data.description || ''}
              onChange={(e) => {
                handleFieldChange('text', e.target.value);
                handleFieldChange('message', e.target.value);
                handleFieldChange('description', e.target.value);
              }}
              placeholder="e.g. Triggered when a user opens the chat widget..."
              rows={3}
            />
          </div>
        </div>
      )}

      {/* --- MESSAGE NODE --- */}
      {type === 'message' && (
        <div className="node-specific-section">
          <div className="section-divider-title">Message Configuration</div>
          <div className="form-group">
            <label htmlFor="message-text">Message Content</label>
            <textarea
              id="message-text"
              className="form-textarea"
              value={data.text || ''}
              onChange={(e) => handleFieldChange('text', e.target.value)}
              placeholder="e.g. Namaste! Welcome. How can I help you?"
              rows={4}
            />
          </div>

          {/* User Input Fields Section (Scenario 11 - Accounts Detail Login Screen) */}
          <div className="input-fields-config-group" style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <div className="section-divider-title" style={{ margin: 0, fontSize: '0.78rem' }}>
                User Input Fields ({inputFieldsList.length})
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-xs"
                onClick={handleAddInputField}
                title="Add a user input prompt slot"
                style={{ fontSize: '0.7rem', padding: '2px 8px' }}
              >
                ➕ Add Field
              </button>
            </div>

            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
              Simulates interactive input capture (e.g., Mobile Number, Email ID) on the message node.
            </p>

            {inputFieldsList.length === 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontStyle: 'italic', padding: '4px 0' }}>
                  No input fields configured. This is a standard bot message.
                </div>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleAddLoginFormPreset}
                  style={{
                    fontSize: '0.72rem',
                    padding: '6px 10px',
                    textAlign: 'left',
                    background: 'rgba(99, 102, 241, 0.1)',
                    borderColor: 'rgba(99, 102, 241, 0.3)',
                    color: '#a5b4fc',
                    cursor: 'pointer',
                  }}
                  title="Preset for Accounts Detail login with Mobile and Email"
                >
                  ⚡ Preset: NABH Accounts Login (Mobile + Email)
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {inputFieldsList.map((field, idx) => (
                  <div
                    key={field.id || idx}
                    style={{
                      background: 'rgba(0, 0, 0, 0.3)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '6px',
                      padding: '8px 10px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#38bdf8' }}>
                        Input #{idx + 1}
                      </span>
                      <button
                        type="button"
                        className="btn-danger-subtle"
                        style={{ fontSize: '0.7rem', padding: '1px 5px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#f87171' }}
                        onClick={() => handleRemoveInputField(field.id)}
                        title="Remove input field"
                      >
                        🗑️
                      </button>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', marginBottom: '6px' }}>
                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label style={{ fontSize: '0.68rem' }}>Label</label>
                        <input
                          type="text"
                          className="form-input form-input-sm"
                          value={field.label}
                          onChange={(e) => handleUpdateInputField(field.id, 'label', e.target.value)}
                          placeholder="e.g. Mobile Number"
                        />
                      </div>
                      <div className="form-group" style={{ marginBottom: 0 }}>
                        <label style={{ fontSize: '0.68rem' }}>Type</label>
                        <select
                          className="form-input form-input-sm"
                          value={field.type}
                          onChange={(e) => handleUpdateInputField(field.id, 'type', e.target.value)}
                        >
                          <option value="text">Text</option>
                          <option value="tel">Phone / Mobile</option>
                          <option value="email">Email</option>
                          <option value="number">Number</option>
                          <option value="password">Password / OTP</option>
                        </select>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input
                        type="text"
                        className="form-input form-input-sm"
                        style={{ flex: 1 }}
                        value={field.placeholder || ''}
                        onChange={(e) => handleUpdateInputField(field.id, 'placeholder', e.target.value)}
                        placeholder="Placeholder text..."
                      />
                      <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.68rem', color: 'var(--text-muted)', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                        <input
                          type="checkbox"
                          checked={Boolean(field.required)}
                          onChange={(e) => handleUpdateInputField(field.id, 'required', e.target.checked)}
                        />
                        Required
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* --- ANSWER NODE --- */}
      {type === 'answer' && (
        <div className="node-specific-section">
          <div className="section-divider-title">Answer Configuration</div>

          <div className="form-group">
            <label htmlFor="answer-text">Answer Text</label>
            <textarea
              id="answer-text"
              className="form-textarea"
              value={data.answer_text !== undefined ? data.answer_text : (data.text || '')}
              onChange={(e) => {
                handleFieldChange('answer_text', e.target.value);
                handleFieldChange('text', e.target.value);
              }}
              placeholder="e.g. Please refer to the relevant healthcare quality guidelines for further information."
              rows={4}
            />
          </div>

          <div className="source-citation-section" style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--border-color)' }}>
            <div className="section-divider-title" style={{ fontSize: '0.78rem', marginBottom: '4px' }}>
              Source Citation (Optional)
            </div>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
              Manually entered citation reference displayed alongside this answer.
            </p>

            <div className="form-group">
              <label htmlFor="source-document">Source Document Name</label>
              <input
                id="source-document"
                type="text"
                className="form-input"
                value={data.source_document || ''}
                onChange={(e) => handleFieldChange('source_document', e.target.value)}
                placeholder="e.g. Healthcare Quality Guidelines.pdf"
              />
            </div>

            <div className="form-group">
              <label htmlFor="source-page">Page Number</label>
              <input
                id="source-page"
                type="text"
                className="form-input"
                value={data.page_number || ''}
                onChange={(e) => handleFieldChange('page_number', e.target.value)}
                placeholder="e.g. 12"
              />
            </div>

            <div className="form-group">
              <label htmlFor="source-url">Source URL</label>
              <input
                id="source-url"
                type="url"
                className="form-input"
                value={data.source_url || ''}
                onChange={(e) => handleFieldChange('source_url', e.target.value)}
                placeholder="e.g. https://example.com/guidelines"
              />
            </div>
          </div>
        </div>
      )}

      {/* --- QUERY ROUTER NODE --- */}
      {type === 'router' && (
        <div className="node-specific-section">
          <div className="section-divider-title">Routing Configuration</div>

          {/* Architecture Service reference (read-only metadata) */}
          {data.service && (
            <div className="form-group">
              <div className="meta-label-row">
                <label>Architecture Service</label>
                <span className="arch-badge">SEBI Core</span>
              </div>
              <input
                type="text"
                className="form-input form-input-readonly"
                value={data.service}
                readOnly
                title="Runtime service path defined in SEBI architecture"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="router-engine">Classifier Engine</label>
            <select
              id="router-engine"
              className="form-input"
              value={data.classifier_engine || 'DSPy + Gemini'}
              onChange={(e) => handleFieldChange('classifier_engine', e.target.value)}
            >
              <option value="DSPy + Gemini">DSPy + Gemini (Default)</option>
              <option value="Gemini Direct Zero-Shot">Gemini Direct Zero-Shot</option>
              <option value="Rule-Based Keyword Router">Rule-Based Keyword Router</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="router-fallback">Fallback Route</label>
            <select
              id="router-fallback"
              className="form-input"
              value={data.default_route || 'faq-rag'}
              onChange={(e) => handleFieldChange('default_route', e.target.value)}
            >
              <option value="faq-rag">FAQ / RAG Pipeline (faq-rag)</option>
              <option value="employee-search">Employee Search (employee-search)</option>
              <option value="sse-response">Direct SSE Response (sse-response)</option>
            </select>
          </div>
        </div>
      )}

      {/* --- EMPLOYEE SEARCH NODE --- */}
      {type === 'employee_search' && (
        <div className="node-specific-section">
          <div className="section-divider-title">Search Configuration</div>

          {data.service && (
            <div className="form-group">
              <div className="meta-label-row">
                <label>Architecture Service</label>
                <span className="arch-badge">SEBI Service</span>
              </div>
              <input
                type="text"
                className="form-input form-input-readonly"
                value={data.service}
                readOnly
                title="Runtime service path defined in SEBI architecture"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="emp-search-mode">Search Mode</label>
            <select
              id="emp-search-mode"
              className="form-input"
              value={data.search_mode || 'Exact & Department Filter'}
              onChange={(e) => handleFieldChange('search_mode', e.target.value)}
            >
              <option value="Exact & Department Filter">Exact & Department Filter (Default)</option>
              <option value="Fuzzy Name Match">Fuzzy Name Match</option>
              <option value="Semantic Role Match">Semantic Role Match</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="emp-max-results">Max Results (Top K)</label>
            <input
              id="emp-max-results"
              type="number"
              min="1"
              max="50"
              className="form-input"
              value={data.max_results || 5}
              onChange={(e) => handleFieldChange('max_results', parseInt(e.target.value, 10) || 5)}
            />
          </div>
        </div>
      )}

      {/* --- FAQ / RAG PIPELINE NODE --- */}
      {type === 'rag' && (
        <div className="node-specific-section">
          <div className="section-divider-title">Retrieval & LLM Configuration</div>

          {data.service && (
            <div className="form-group">
              <div className="meta-label-row">
                <label>Architecture Service</label>
                <span className="arch-badge">SEBI Service</span>
              </div>
              <input
                type="text"
                className="form-input form-input-readonly"
                value={data.service}
                readOnly
                title="Runtime service path defined in SEBI architecture"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="rag-vector-store">Vector Store</label>
            <select
              id="rag-vector-store"
              className="form-input"
              value={data.vector_store || 'ChromaDB'}
              onChange={(e) => handleFieldChange('vector_store', e.target.value)}
            >
              <option value="ChromaDB">ChromaDB (Default)</option>
              <option value="FAISS">FAISS Index</option>
              <option value="Qdrant">Qdrant Vector DB</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="rag-llm">Generative LLM</label>
            <select
              id="rag-llm"
              className="form-input"
              value={data.llm || 'Gemini'}
              onChange={(e) => handleFieldChange('llm', e.target.value)}
            >
              <option value="Gemini">Gemini (Default)</option>
              <option value="Gemini 1.5 Pro">Gemini 1.5 Pro</option>
              <option value="Gemini 1.5 Flash">Gemini 1.5 Flash</option>
            </select>
          </div>

          <div className="form-row-2">
            <div className="form-group">
              <label htmlFor="rag-top-k">Top K Chunks</label>
              <input
                id="rag-top-k"
                type="number"
                min="1"
                max="20"
                className="form-input"
                value={data.top_k || 3}
                onChange={(e) => handleFieldChange('top_k', parseInt(e.target.value, 10) || 3)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="rag-threshold">Similarity Cutoff</label>
              <input
                id="rag-threshold"
                type="number"
                step="0.05"
                min="0.1"
                max="1.0"
                className="form-input"
                value={data.similarity_threshold || 0.7}
                onChange={(e) => handleFieldChange('similarity_threshold', parseFloat(e.target.value) || 0.7)}
              />
            </div>
          </div>
        </div>
      )}

      {/* --- SSE STREAMING RESPONSE NODE --- */}
      {type === 'response' && (
        <div className="node-specific-section">
          <div className="section-divider-title">Streaming Options</div>

          <div className="form-group">
            <label htmlFor="stream-mode">Streaming Protocol</label>
            <select
              id="stream-mode"
              className="form-input"
              value={data.stream_mode || 'Server-Sent Events (SSE)'}
              onChange={(e) => handleFieldChange('stream_mode', e.target.value)}
            >
              <option value="Server-Sent Events (SSE)">Server-Sent Events (SSE - Default)</option>
              <option value="WebSockets">WebSockets</option>
              <option value="Buffered Chunked JSON">Buffered Chunked JSON</option>
            </select>
          </div>

          <div className="form-group-checkbox">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={data.include_metadata !== false}
                onChange={(e) => handleFieldChange('include_metadata', e.target.checked)}
              />
              <span>Include Source Citations & Metadata in Stream</span>
            </label>
          </div>
        </div>
      )}

      {/* --- TTS AUDIO NODE --- */}
      {type === 'tts' && (
        <div className="node-specific-section">
          <div className="section-divider-title">TTS Audio Options</div>

          {data.service && (
            <div className="form-group">
              <div className="meta-label-row">
                <label>Architecture Service</label>
                <span className="arch-badge">SEBI Service</span>
              </div>
              <input
                type="text"
                className="form-input form-input-readonly"
                value={data.service}
                readOnly
                title="Runtime service path defined in SEBI architecture"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="tts-audio-format">Audio Output Format</label>
            <select
              id="tts-audio-format"
              className="form-input"
              value={data.audio_format || 'wav'}
              onChange={(e) => handleFieldChange('audio_format', e.target.value)}
            >
              <option value="wav">WAV (Default SEBI Audio)</option>
              <option value="mp3">MP3</option>
              <option value="ogg">OGG</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="tts-voice">Voice Profile</label>
            <select
              id="tts-voice"
              className="form-input"
              value={data.voice || 'en-IN-Wavenet-A'}
              onChange={(e) => handleFieldChange('voice', e.target.value)}
            >
              <option value="en-IN-Wavenet-A">en-IN-Wavenet-A (Indian English - Female)</option>
              <option value="en-IN-Wavenet-B">en-IN-Wavenet-B (Indian English - Male)</option>
              <option value="en-US-Neural2-F">en-US-Neural2-F (US English - Neutral)</option>
            </select>
          </div>
        </div>
      )}

      {/* --- LLM GENERATOR NODE --- */}
      {type === 'llm' && (
        <div className="node-specific-section">
          <div className="section-divider-title">LLM Configuration</div>
          <div className="form-group">
            <label htmlFor="llm-model">Model</label>
            <select
              id="llm-model"
              className="form-input"
              value={data.model || 'gemini-1.5-flash'}
              onChange={(e) => handleFieldChange('model', e.target.value)}
            >
              <option value="gemini-1.5-flash">Gemini 1.5 Flash (Fast & Cost-effective)</option>
              <option value="gemini-1.5-pro">Gemini 1.5 Pro (Complex Reasoning)</option>
              <option value="gpt-4o">GPT-4o (High Performance)</option>
              <option value="gpt-4o-mini">GPT-4o-mini (Lightweight)</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="llm-temperature">Temperature ({data.temperature ?? 0.7})</label>
            <input
              id="llm-temperature"
              type="range"
              min="0"
              max="2"
              step="0.1"
              className="form-input"
              style={{ padding: '4px 0' }}
              value={data.temperature ?? 0.7}
              onChange={(e) => handleFieldChange('temperature', parseFloat(e.target.value))}
            />
          </div>
          <div className="form-group">
            <label htmlFor="llm-max-tokens">Max Output Tokens</label>
            <input
              id="llm-max-tokens"
              type="number"
              className="form-input"
              value={data.max_tokens ?? 1024}
              onChange={(e) => handleFieldChange('max_tokens', parseInt(e.target.value, 10) || 512)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="llm-system-prompt">System Prompt / Instructions</label>
            <textarea
              id="llm-system-prompt"
              className="form-textarea"
              value={data.system_prompt || ''}
              onChange={(e) => handleFieldChange('system_prompt', e.target.value)}
              placeholder="System instructions for the model..."
              rows={3}
            />
          </div>
        </div>
      )}

      {/* --- API REQUEST NODE --- */}
      {type === 'api_request' && (
        <div className="node-specific-section">
          <div className="section-divider-title">API Request Configuration</div>
          <div className="form-group">
            <label htmlFor="api-method">HTTP Method</label>
            <select
              id="api-method"
              className="form-input"
              value={data.method || 'GET'}
              onChange={(e) => handleFieldChange('method', e.target.value)}
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="api-url">Endpoint URL</label>
            <input
              id="api-url"
              type="text"
              className="form-input"
              value={data.endpoint_url || ''}
              onChange={(e) => handleFieldChange('endpoint_url', e.target.value)}
              placeholder="https://api.example.com/v1/..."
            />
          </div>
          <div className="form-group">
            <label htmlFor="api-timeout">Timeout (seconds)</label>
            <input
              id="api-timeout"
              type="number"
              className="form-input"
              value={data.timeout_seconds ?? 10}
              onChange={(e) => handleFieldChange('timeout_seconds', parseInt(e.target.value, 10) || 10)}
            />
          </div>
        </div>
      )}

      {/* --- CONDITION NODE --- */}
      {type === 'condition' && (
        <div className="node-specific-section">
          <div className="section-divider-title">Condition Logic</div>
          <div className="form-group">
            <label htmlFor="condition-expr">Expression / Variable</label>
            <input
              id="condition-expr"
              type="text"
              className="form-input"
              value={data.expression || ''}
              onChange={(e) => handleFieldChange('expression', e.target.value)}
              placeholder="e.g. intent == 'support'"
            />
          </div>
          <div className="form-group">
            <label htmlFor="condition-op">Comparison Operator</label>
            <select
              id="condition-op"
              className="form-input"
              value={data.operator || 'equals'}
              onChange={(e) => handleFieldChange('operator', e.target.value)}
            >
              <option value="equals">Equals (==)</option>
              <option value="not_equals">Not Equals (!=)</option>
              <option value="contains">Contains Substring</option>
              <option value="greater_than">Greater Than (&gt;)</option>
              <option value="less_than">Less Than (&lt;)</option>
            </select>
          </div>
        </div>
      )}

      {/* --- DATABASE NODE --- */}
      {type === 'database' && (
        <div className="node-specific-section">
          <div className="section-divider-title">Database Query</div>
          <div className="form-group">
            <label htmlFor="db-query-type">Operation</label>
            <select
              id="db-query-type"
              className="form-input"
              value={data.query_type || 'SELECT'}
              onChange={(e) => handleFieldChange('query_type', e.target.value)}
            >
              <option value="SELECT">SELECT</option>
              <option value="INSERT">INSERT</option>
              <option value="UPDATE">UPDATE</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="db-table">Target Table</label>
            <input
              id="db-table"
              type="text"
              className="form-input"
              value={data.table_name || ''}
              onChange={(e) => handleFieldChange('table_name', e.target.value)}
              placeholder="e.g. users, audit_log"
            />
          </div>
          <div className="form-group">
            <label htmlFor="db-limit">Result Limit</label>
            <input
              id="db-limit"
              type="number"
              className="form-input"
              value={data.limit ?? 10}
              onChange={(e) => handleFieldChange('limit', parseInt(e.target.value, 10) || 10)}
            />
          </div>
        </div>
      )}

      {/* --- DYNAMIC CUSTOM NODE CONFIGURATION --- */}
      {(data.config_schema?.fields?.length > 0 || (data.node_source === 'custom' && !['start', 'message', 'router', 'employee_search', 'rag', 'response', 'tts', 'llm', 'api_request', 'condition', 'database'].includes(type))) && (
        <div className="node-specific-section">
          <div className="section-divider-title">
            {data.node_source === 'custom' ? 'Custom Node Properties' : 'Configurable Schema'}
          </div>

          {data.config_schema?.fields && data.config_schema.fields.length > 0 ? (
            data.config_schema.fields.map((field) => (
              <div className="form-group" key={field.name}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label htmlFor={`custom-field-${field.name}`}>
                    {field.label || field.name} {field.required && <span style={{ color: '#ef4444' }}>*</span>}
                  </label>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontFamily: 'monospace' }}>
                    {field.type}
                  </span>
                </div>

                {field.type === 'select' ? (
                  <select
                    id={`custom-field-${field.name}`}
                    className="form-input"
                    value={data[field.name] !== undefined ? data[field.name] : (field.default || '')}
                    onChange={(e) => handleFieldChange(field.name, e.target.value)}
                  >
                    {(field.options || []).map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : field.type === 'boolean' ? (
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', marginTop: '4px' }}>
                    <input
                      type="checkbox"
                      checked={Boolean(data[field.name] !== undefined ? data[field.name] : field.default)}
                      onChange={(e) => handleFieldChange(field.name, e.target.checked)}
                    />
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      Enable {field.label || field.name}
                    </span>
                  </label>
                ) : field.type === 'number' ? (
                  <input
                    id={`custom-field-${field.name}`}
                    type="number"
                    className="form-input"
                    value={data[field.name] !== undefined ? data[field.name] : (field.default ?? 0)}
                    onChange={(e) => handleFieldChange(field.name, parseFloat(e.target.value) || 0)}
                  />
                ) : (
                  <input
                    id={`custom-field-${field.name}`}
                    type="text"
                    className="form-input"
                    value={data[field.name] !== undefined ? data[field.name] : (field.default || '')}
                    onChange={(e) => handleFieldChange(field.name, e.target.value)}
                    placeholder={`Enter ${field.label || field.name}...`}
                  />
                )}
              </div>
            ))
          ) : (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontStyle: 'italic', padding: '6px 0' }}>
              No custom schema fields configured for this node.
            </div>
          )}
        </div>
      )}

      {/* --- BUTTONS & BRANCHING CONFIGURATION --- */}
      {(['message', 'menu', 'form', 'content', 'start'].includes(type) || data.node_source === 'custom' || Array.isArray(data.buttons) || !['answer', 'router', 'employee_search', 'rag', 'response', 'tts', 'llm', 'api_request', 'condition', 'database'].includes(type)) && (
        <div className="node-specific-section">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div className="section-divider-title" style={{ margin: 0 }}>
              Interactive Buttons ({buttonsList.length})
            </div>
            <button
              type="button"
              className="btn btn-primary btn-xs"
              onClick={handleAddButtonOption}
              title="Add an interactive button branch"
            >
              ➕ Add Button
            </button>
          </div>

          <p style={{ fontSize: '0.725rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
            Each button has its own connection handle and routes to a distinct destination step (e.g. Answer node).
          </p>

          {buttonsList.length === 0 ? (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '6px 0' }}>
              No buttons configured. Click <strong>➕ Add Button</strong> to add interactive choices (e.g. Explore All Programs, Fee &amp; ROI Calculator).
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {buttonsList.map((btn, idx) => {
                const currentEdge = edges.find((e) => e.source === id && (e.sourceHandle === btn.id || (!e.sourceHandle && buttonsList.length === 1)));
                const currentDestId = currentEdge ? currentEdge.target : (btn.next || btn.target || '');
                const targetNodeObj = allNodes.find((n) => n.id === currentDestId);

                return (
                  <div
                    key={btn.id || idx}
                    style={{
                      background: 'rgba(0, 0, 0, 0.25)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '6px',
                      padding: '10px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.68rem', color: '#c084fc', fontFamily: 'monospace', fontWeight: 600 }}>
                          Handle ID: {btn.id}
                        </span>
                        {!currentDestId && (
                          <span
                            style={{
                              fontSize: '0.62rem',
                              fontWeight: 600,
                              padding: '1px 5px',
                              borderRadius: '3px',
                              background: 'rgba(245, 158, 11, 0.15)',
                              color: '#f59e0b',
                              border: '1px solid rgba(245, 158, 11, 0.35)',
                            }}
                          >
                            ⚠️ Unconnected
                          </span>
                        )}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ fontSize: '0.7rem', padding: '2px 6px', lineHeight: 1 }}
                          disabled={idx === 0}
                          onClick={() => handleMoveButtonUp(idx)}
                          title="Move button up"
                        >
                          ▲
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ fontSize: '0.7rem', padding: '2px 6px', lineHeight: 1 }}
                          disabled={idx === buttonsList.length - 1}
                          onClick={() => handleMoveButtonDown(idx)}
                          title="Move button down"
                        >
                          ▼
                        </button>
                        <button
                          type="button"
                          className="btn-danger-subtle"
                          style={{ fontSize: '0.725rem', padding: '2px 6px' }}
                          onClick={() => handleRemoveButtonOption(btn.id)}
                          title="Remove button and disconnect its edge"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>

                    <div className="form-group" style={{ marginBottom: '8px' }}>
                      <label style={{ fontSize: '0.7rem' }}>Button Label</label>
                      <input
                        type="text"
                        className="form-input form-input-sm"
                        value={btn.label}
                        onChange={(e) => handleEditButtonLabel(btn.id, e.target.value)}
                        placeholder="e.g. About NABH"
                      />
                    </div>

                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label style={{ fontSize: '0.7rem', display: 'flex', justifyContent: 'space-between' }}>
                        <span>Destination Node:</span>
                        {currentDestId ? (
                          <span style={{ color: '#10b981', fontWeight: 500 }}>
                            → {targetNodeObj?.data?.label || currentDestId}
                          </span>
                        ) : (
                          <span style={{ color: '#f59e0b', fontWeight: 600 }}>⚠️ Unconnected branch</span>
                        )}
                      </label>
                      <select
                        className="form-input form-input-sm"
                        value={currentDestId}
                        onChange={(e) => handleDestinationChange(btn.id, e.target.value)}
                      >
                        <option value="">-- Disconnected (No destination) --</option>
                        {allNodes
                          .filter((n) => n.id !== id)
                          .map((targetNode) => (
                            <option key={targetNode.id} value={targetNode.id}>
                              {targetNode.data?.label || targetNode.id} ({targetNode.type})
                            </option>
                          ))}
                      </select>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Runtime Architecture Notice */}
      <div className="properties-arch-notice">
        <span>ℹ️</span>
        <p>Configuration updates apply directly to the node & flow schema. Architecture services reflect SEBI runtime components.</p>
      </div>

      {/* Metadata Readout */}
      <div className="node-meta">
        <div className="meta-row">
          <span>Node ID:</span>
          <span className="meta-val">{id}</span>
        </div>
        <div className="meta-row">
          <span>Node Type:</span>
          <span className="meta-val">{type}</span>
        </div>
        <div className="meta-row">
          <span>Position:</span>
          <span className="meta-val">
            X: {Math.round(position?.x || 0)}, Y: {Math.round(position?.y || 0)}
          </span>
        </div>
      </div>

      {/* Quick Delete */}
      <div style={{ marginTop: 'auto', paddingTop: '10px' }}>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ width: '100%', borderColor: 'rgba(239, 68, 68, 0.4)', color: '#f87171' }}
          onClick={() => onDeleteNode(id)}
        >
          🗑️ Delete Node
        </button>
      </div>
    </aside>
  );
};

export default PropertiesPanel;
