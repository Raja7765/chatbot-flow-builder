import React, { useState, useEffect } from 'react';
import { createFlow, updateFlow, fetchFlowById } from '../api/client';

/**
 * SaveFlowModal Component
 * Dialog allowing users to name, describe, and persist a flow to SQLite via FastAPI.
 * Handles both creating new flows (POST /flows) and updating existing flows (PUT /flows/{flow_id}).
 */
const SaveFlowModal = ({
  isOpen,
  onClose,
  onSaveSuccess,
  flowId = null,
  chatbots = [],
  selectedChatbotId = null,
  initialName = '',
  initialDescription = '',
  flowData = { nodes: [], edges: [] },
  getLatestFlowData = null,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [targetChatbotId, setTargetChatbotId] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [nameError, setNameError] = useState(null);

  // Lock background page scrolling when modal is open and restore on close
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isOpen]);

  // Initialize form whenever modal opens or props change
  useEffect(() => {
    if (isOpen) {
      setName(initialName || (flowId ? 'Untitled Flow' : 'New Flow'));
      setDescription(initialDescription || '');

      // Default target chatbot to selectedChatbotId, or first available bot
      if (selectedChatbotId && chatbots.some((b) => b.id === selectedChatbotId)) {
        setTargetChatbotId(selectedChatbotId);
      } else if (chatbots.length > 0) {
        setTargetChatbotId(chatbots[0].id);
      } else {
        setTargetChatbotId('');
      }

      setErrorMessage(null);
      setNameError(null);
      setIsSaving(false);
    }
  }, [isOpen, flowId, initialName, initialDescription, selectedChatbotId, chatbots]);

  if (!isOpen) return null;

  const isExistingFlow = Boolean(flowId);
  const activeChatbot = chatbots.find((b) => b.id === targetChatbotId) || null;
  const hasNoChatbots = chatbots.length === 0;

  // Extract latest live flow data if getter is provided, otherwise fallback to flowData prop
  const currentFlowData = typeof getLatestFlowData === 'function' ? getLatestFlowData() : flowData;

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Client-side validation
    const trimmedName = name.trim();
    if (!trimmedName) {
      setNameError('Flow name is required and cannot be empty.');
      return;
    }
    setNameError(null);

    if (!targetChatbotId) {
      setErrorMessage('A chatbot must be selected. Flows must belong to a chatbot.');
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);

    // Re-evaluate live flow data at moment of submission
    const liveData = typeof getLatestFlowData === 'function' ? getLatestFlowData() : flowData;

    // Build the payload conforming to FlowCreate / FlowUpdate schemas
    const payload = {
      chatbot_id: targetChatbotId,
      name: trimmedName,
      description: description.trim() || undefined,
      flow_data: {
        nodes: liveData.nodes || [],
        edges: liveData.edges || [],
      },
    };

    console.log('[SaveFlowModal] 1. Submit handler INVOKED:', {
      flowId,
      isExistingFlow,
      targetChatbotId,
      name: trimmedName,
      outgoingNodeCount: payload.flow_data.nodes.length,
      outgoingEdgeCount: payload.flow_data.edges.length,
    });

    try {
      let savedResult;
      if (isExistingFlow) {
        // Save updates to existing flow (PUT /flows/{flow_id})
        savedResult = await updateFlow(flowId, payload);
      } else {
        // Save as new flow (POST /flows)
        savedResult = await createFlow(payload);
      }

      if (!savedResult || !savedResult.id) {
        throw new Error('Server returned an empty or invalid flow response.');
      }

      // Verify that the expected flow ID is returned
      if (isExistingFlow && savedResult.id !== flowId) {
        throw new Error(`Flow ID mismatch: requested update for '${flowId}', but server returned '${savedResult.id}'.`);
      }

      console.log('[SaveFlowModal] 2. HTTP response received:', {
        id: savedResult.id,
        name: savedResult.name,
        responseNodeCount: savedResult.flow_data?.nodes?.length,
        responseEdgeCount: savedResult.flow_data?.edges?.length,
        updated_at: savedResult.updated_at,
      });

      // 3. Fresh GET verification request to prove SQLite database persisted the exact nodes
      console.log(`[SaveFlowModal] 3. Executing verification GET /flows/${savedResult.id}...`);
      const verifiedFlow = await fetchFlowById(savedResult.id);
      console.log('[SaveFlowModal] 4. Fresh GET response verified from database:', {
        id: verifiedFlow.id,
        name: verifiedFlow.name,
        persistedNodeCount: verifiedFlow?.flow_data?.nodes?.length,
        persistedEdgeCount: verifiedFlow?.flow_data?.edges?.length,
        persisted_updated_at: verifiedFlow.updated_at,
      });

      // Confirm expected flow ID in GET response
      if (verifiedFlow.id !== savedResult.id) {
        throw new Error(`Persistence verification error: expected flow ID '${savedResult.id}', but database returned '${verifiedFlow.id}'.`);
      }

      // Confirm persisted node count matches what was sent
      const persistedNodes = Array.isArray(verifiedFlow?.flow_data?.nodes) ? verifiedFlow.flow_data.nodes : [];
      const persistedEdges = Array.isArray(verifiedFlow?.flow_data?.edges) ? verifiedFlow.flow_data.edges : [];
      if (persistedNodes.length !== payload.flow_data.nodes.length) {
        throw new Error(
          `Persistence verification mismatch: submitted ${payload.flow_data.nodes.length} nodes, but database returned ${persistedNodes.length} nodes.`
        );
      }
      if (persistedEdges.length !== payload.flow_data.edges.length) {
        throw new Error(
          `Persistence verification mismatch: submitted ${payload.flow_data.edges.length} edges, but database returned ${persistedEdges.length} edges.`
        );
      }

      // Confirm node IDs are preserved
      const submittedNodeIds = new Set(payload.flow_data.nodes.map((n) => String(n.id)));
      const missingNodeIds = persistedNodes.filter((n) => !submittedNodeIds.has(String(n.id)));
      if (missingNodeIds.length > 0) {
        throw new Error(`Persistence verification mismatch: unexpected or corrupted nodes returned from database.`);
      }

      // Notify parent on success and close modal ONLY AFTER verification passes
      if (onSaveSuccess) {
        onSaveSuccess(verifiedFlow, isExistingFlow);
      }
      onClose();
    } catch (err) {
      console.error('[SaveFlowModal] Save failed with error:', err);
      let friendlyError = 'Failed to save flow to backend. Please check network connection and try again.';
      if (err && err.message) {
        friendlyError = err.message.replace(/^Error:\s*/i, '');
      }
      setErrorMessage(friendlyError);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={isSaving ? undefined : onClose}>
      <div
        className="modal-content save-flow-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="save-modal-title"
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.25rem' }}>💾</span>
            <div>
              <h3 id="save-modal-title">
                {isExistingFlow ? 'Save Flow (Update Existing Record)' : 'Save New Flow'}
              </h3>
              <span style={{ fontSize: '0.725rem', color: isExistingFlow ? '#38bdf8' : '#10b981', fontWeight: 500 }}>
                {isExistingFlow
                  ? `Updating Flow ID: ${flowId.slice(0, 8)}... (created_at preserved)`
                  : 'Creates a new flow record in the database'}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: '4px 8px' }}
            onClick={onClose}
            disabled={isSaving}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="modal-body">
            {/* Warning if no chatbots exist */}
            {hasNoChatbots && (
              <div className="modal-alert modal-alert-error">
                <span style={{ fontSize: '1.2rem' }}>⚠️</span>
                <div>
                  <strong>No Chatbots Available:</strong>
                  <p style={{ marginTop: '2px', fontSize: '0.8rem' }}>
                    Flows require an associated chatbot. Please ensure a chatbot is created on the backend before saving.
                  </p>
                </div>
              </div>
            )}

            {/* Error Message Alert */}
            {errorMessage && (
              <div className="modal-alert modal-alert-error">
                <span style={{ fontSize: '1.2rem' }}>⚠️</span>
                <div style={{ flex: 1 }}>
                  <strong>Error Saving Flow:</strong>
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

            {/* 1. Target Chatbot Confirmation */}
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label htmlFor="save-target-chatbot">
                Associated Chatbot <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <select
                id="save-target-chatbot"
                className="modal-filter-select"
                value={targetChatbotId}
                onChange={(e) => setTargetChatbotId(e.target.value)}
                disabled={isSaving || hasNoChatbots}
                style={{ width: '100%', marginTop: '4px' }}
              >
                {chatbots.map((bot) => (
                  <option key={bot.id} value={bot.id}>
                    {bot.name} ({bot.id.slice(0, 8)}...)
                  </option>
                ))}
              </select>
              {activeChatbot && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                  <span className="status-badge status-active">{activeChatbot.status || 'active'}</span>
                  <span style={{ fontSize: '0.725rem', color: 'var(--text-dim)', fontFamily: 'monospace' }}>
                    Full Chatbot ID: {activeChatbot.id}
                  </span>
                </div>
              )}
            </div>

            {/* 2. Flow Name Field */}
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label htmlFor="save-flow-name">
                Flow Name <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <input
                id="save-flow-name"
                type="text"
                className="form-input"
                style={{
                  marginTop: '4px',
                  borderColor: nameError ? '#ef4444' : undefined,
                }}
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (nameError) setNameError(null);
                }}
                placeholder="e.g. Customer Onboarding Flow"
                disabled={isSaving}
                autoFocus
              />
              {nameError && (
                <span style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '4px' }}>
                  {nameError}
                </span>
              )}
            </div>

            {/* 3. Flow Description Field */}
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label htmlFor="save-flow-description">Description (Optional)</label>
              <textarea
                id="save-flow-description"
                className="form-textarea"
                style={{ marginTop: '4px' }}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the purpose, steps, or routing logic of this flow..."
                rows={3}
                disabled={isSaving}
              />
            </div>

            {/* 4. Canvas Contents Summary */}
            <div className="node-meta" style={{ marginTop: '12px' }}>
              <div className="meta-row">
                <span>Canvas Elements to Persist:</span>
                <span className="meta-val">
                  {currentFlowData.nodes?.length || 0} Nodes · {currentFlowData.edges?.length || 0} Edges
                </span>
              </div>
              <div className="meta-row">
                <span>Persistence Method:</span>
                <span className="meta-val" style={{ color: isExistingFlow ? '#38bdf8' : '#10b981' }}>
                  {isExistingFlow ? `PUT /flows/${flowId.slice(0, 8)}...` : 'POST /flows'}
                </span>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSaving || hasNoChatbots || !targetChatbotId}
              style={{ minWidth: '150px' }}
              aria-busy={isSaving}
            >
              {isSaving ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                  <span className="save-spinner" aria-hidden="true" />
                  <span>{isExistingFlow ? 'Updating Flow...' : 'Creating Flow...'}</span>
                </span>
              ) : isExistingFlow ? (
                '💾 Update Flow'
              ) : (
                '💾 Create Flow'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SaveFlowModal;
