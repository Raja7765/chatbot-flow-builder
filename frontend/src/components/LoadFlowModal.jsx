import React, { useState, useEffect, useCallback } from 'react';
import { fetchChatbots, fetchChatbotFlows, fetchFlowById } from '../api/client';

/**
 * LoadFlowModal Component
 * Modal dialog allowing users to browse and load flows for any chatbot.
 * Uses the reusable API utility and handles loading, empty, and error states.
 */
const LoadFlowModal = ({
  isOpen,
  onClose,
  onLoadFlow,
  currentFlowId,
  initialChatbotId,
}) => {
  const [chatbots, setChatbots] = useState([]);
  const [activeBotId, setActiveBotId] = useState(initialChatbotId || null);
  const [flows, setFlows] = useState([]);
  const [selectedFlowId, setSelectedFlowId] = useState(null);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Sync active chatbot ID with prop when modal opens
  useEffect(() => {
    if (isOpen && initialChatbotId) {
      setActiveBotId(initialChatbotId);
    }
  }, [isOpen, initialChatbotId]);

  // Fetch available chatbots list
  const loadChatbots = useCallback(async () => {
    try {
      const bots = await fetchChatbots();
      setChatbots(bots);
      if (!activeBotId && bots.length > 0) {
        setActiveBotId(bots[0].id);
      }
    } catch (err) {
      setErrorMessage(err.message);
    }
  }, [activeBotId]);

  // Fetch flows for the active chatbot
  const loadFlows = useCallback(async (botId) => {
    if (!botId) return;
    setIsLoadingList(true);
    setErrorMessage(null);
    try {
      const botFlows = await fetchChatbotFlows(botId);
      setFlows(botFlows);

      // Pre-select current flow or first flow
      if (currentFlowId && botFlows.some((f) => f.id === currentFlowId)) {
        setSelectedFlowId(currentFlowId);
      } else if (botFlows.length > 0) {
        setSelectedFlowId(botFlows[0].id);
      } else {
        setSelectedFlowId(null);
      }
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setIsLoadingList(false);
    }
  }, [currentFlowId]);

  // Initial load when modal opens
  useEffect(() => {
    if (isOpen) {
      loadChatbots();
    } else {
      setErrorMessage(null);
      setSelectedFlowId(null);
    }
  }, [isOpen, loadChatbots]);

  // Load flows whenever active chatbot changes
  useEffect(() => {
    if (isOpen && activeBotId) {
      loadFlows(activeBotId);
    }
  }, [isOpen, activeBotId, loadFlows]);

  // Confirm loading the selected flow
  const handleConfirmLoad = async () => {
    if (!selectedFlowId) return;

    setIsLoadingDetail(true);
    setErrorMessage(null);
    try {
      const detailedFlow = await fetchFlowById(selectedFlowId);
      onLoadFlow(detailedFlow);
      onClose();
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  if (!isOpen) return null;

  const currentBot = chatbots.find((b) => b.id === activeBotId);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content load-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.2rem' }}>📂</span>
            <h3>Load Saved Flow</h3>
          </div>
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
          {/* Chatbot Selector inside modal */}
          <div className="modal-bot-filter-row">
            <label htmlFor="modal-bot-select" className="modal-filter-label">
              <span>Chatbot:</span>
            </label>
            <select
              id="modal-bot-select"
              className="modal-filter-select"
              value={activeBotId || ''}
              onChange={(e) => setActiveBotId(e.target.value)}
              disabled={isLoadingList}
            >
              {chatbots.map((bot) => (
                <option key={bot.id} value={bot.id}>
                  {bot.name} (ID: {bot.id.slice(0, 8)}...)
                </option>
              ))}
            </select>
            {currentBot && (
              <span className="modal-bot-id-tag" title={`Full ID: ${currentBot.id}`}>
                ID: {currentBot.id}
              </span>
            )}
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div className="modal-alert modal-alert-error">
              <span style={{ fontSize: '1.1rem' }}>⚠️</span>
              <div style={{ flex: 1 }}>
                <strong>API Notice:</strong>
                <p style={{ marginTop: '2px', fontSize: '0.8rem' }}>{errorMessage}</p>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-xs"
                onClick={() => loadFlows(activeBotId)}
              >
                Retry
              </button>
            </div>
          )}

          {/* Loading state for list */}
          {isLoadingList && (
            <div className="modal-empty-state">
              <span className="spinner">⏳</span>
              <p>Fetching saved flows for chatbot...</p>
            </div>
          )}

          {/* Empty state when no flows exist */}
          {!isLoadingList && !errorMessage && flows.length === 0 && (
            <div className="modal-empty-state">
              <span style={{ fontSize: '2rem' }}>📭</span>
              <h4>No Saved Flows Found</h4>
              <p>
                {currentBot
                  ? `No flows exist for "${currentBot.name}".`
                  : 'No saved flows available.'}
              </p>
            </div>
          )}

          {/* Flows List */}
          {!isLoadingList && flows.length > 0 && (
            <div className="flows-list-container">
              <div className="flows-list-header">
                <span>Select a flow to load into the canvas ({flows.length} available):</span>
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => loadFlows(activeBotId)}
                  disabled={isLoadingList}
                  title="Refresh list from backend"
                >
                  🔄 Refresh
                </button>
              </div>

              <div className="flows-list">
                {flows.map((flow) => {
                  const isSelected = selectedFlowId === flow.id;
                  const isCurrent = currentFlowId === flow.id;
                  const nodeCount = flow.flow_data?.nodes?.length || 0;
                  const edgeCount = flow.flow_data?.edges?.length || 0;

                  return (
                    <div
                      key={flow.id}
                      className={`flow-list-item ${isSelected ? 'selected' : ''}`}
                      onClick={() => setSelectedFlowId(flow.id)}
                      onDoubleClick={handleConfirmLoad}
                    >
                      <div className="flow-item-header">
                        <span className="flow-item-name">{flow.name}</span>
                        {isCurrent && <span className="current-badge">Currently Loaded</span>}
                      </div>

                      <div className="flow-item-meta">
                        <span className="flow-item-id">Flow ID: {flow.id}</span>
                        <span className="flow-item-counts">
                          {nodeCount} nodes · {edgeCount} edges
                        </span>
                      </div>

                      {flow.description && (
                        <div className="flow-item-description">{flow.description}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={isLoadingDetail}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleConfirmLoad}
            disabled={!selectedFlowId || isLoadingDetail || isLoadingList}
          >
            {isLoadingDetail ? 'Loading Flow...' : 'Load Selected Flow'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoadFlowModal;
