import React, { useState, useMemo } from 'react';
import ChatbotSelector from './ChatbotSelector';

const PREBUILT_ICONS = {
  start: '🟢',
  message: '💬',
  answer: '💡',
  router: '🔀',
  llm: '🤖',
  api_request: '🌐',
  condition: '⚖️',
  database: '🗄️',
  response: '📡',
  employee_search: '🔍',
  rag: '📚',
  tts: '🔊',
};

/**
 * Sidebar Component
 * Houses the Chatbot Selector, the list of Flows associated with the selected chatbot,
 * and the database-driven Node Library (Prebuilt & Custom Nodes).
 */
const Sidebar = ({
  chatbots = [],
  selectedChatbotId,
  onSelectChatbot,
  isLoadingChatbots,
  chatbotsError,
  onRetryChatbots,
  flows = [],
  isLoadingFlows,
  flowsError,
  onRetryFlows,
  loadedFlowId,
  onSelectFlow,
  onCreateFlow,
  onAddNode,
  nodeDefinitions = [],
  isLoadingNodes = false,
  onOpenCreateCustomModal,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [activeTab, setActiveTab] = useState('ALL'); // 'ALL', 'PREBUILT', 'CUSTOM'

  const onDragStart = (event, nodeType, nodeDef) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    if (nodeDef) {
      event.dataTransfer.setData('application/node_def', JSON.stringify(nodeDef));
    }
    event.dataTransfer.effectAllowed = 'move';
  };

  const selectedChatbot = chatbots.find((b) => b.id === selectedChatbotId);

  // Extract distinct categories from node definitions
  const categories = useMemo(() => {
    const set = new Set();
    nodeDefinitions.forEach((def) => {
      if (def.category) set.add(def.category);
    });
    return Array.from(set).sort();
  }, [nodeDefinitions]);

  // Filter nodes by search query, category, and active status
  const filteredNodes = useMemo(() => {
    return nodeDefinitions.filter((def) => {
      // Must be active
      if (def.is_active === false || def.is_active === 0) return false;

      // Filter by category
      if (selectedCategory !== 'ALL' && def.category?.toLowerCase() !== selectedCategory.toLowerCase()) {
        return false;
      }

      // Filter by search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = def.name?.toLowerCase().includes(q);
        const matchesType = def.node_type?.toLowerCase().includes(q);
        const matchesDesc = def.description?.toLowerCase().includes(q);
        const matchesCat = def.category?.toLowerCase().includes(q);
        if (!matchesName && !matchesType && !matchesDesc && !matchesCat) return false;
      }

      return true;
    });
  }, [nodeDefinitions, searchQuery, selectedCategory]);

  const prebuiltNodes = useMemo(
    () => filteredNodes.filter((n) => n.node_source === 'prebuilt'),
    [filteredNodes]
  );

  const customNodes = useMemo(
    () => filteredNodes.filter((n) => n.node_source === 'custom'),
    [filteredNodes]
  );

  const renderNodeCard = (def) => {
    const icon = def.icon || PREBUILT_ICONS[def.node_type] || '🧩';
    const isCustom = def.node_source === 'custom';

    return (
      <div
        key={def.id || def.node_type}
        className={`dnd-node-card ${isCustom ? 'custom-dnd-card' : ''}`}
        onDragStart={(event) => onDragStart(event, def.node_type, def)}
        onClick={() => onAddNode(def.node_type, def)}
        draggable
        title={`Drag onto canvas or click to add ${def.name}`}
      >
        <div className={`dnd-node-icon icon-${def.node_type}`}>{icon}</div>
        <div className="dnd-node-info">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '4px' }}>
            <h4>{def.name}</h4>
            <span
              className={`node-source-pill ${isCustom ? 'pill-custom' : 'pill-prebuilt'}`}
              title={isCustom ? 'User Created Custom Node' : 'Prebuilt Core Template'}
            >
              {isCustom ? 'Custom' : def.category || 'Core'}
            </span>
          </div>
          <p>{def.description || `Node type: ${def.node_type}`}</p>
        </div>
      </div>
    );
  };

  return (
    <aside className="sidebar">
      {/* 1. Chatbot Selection Section */}
      <div className="sidebar-section">
        <ChatbotSelector
          chatbots={chatbots}
          selectedChatbotId={selectedChatbotId}
          onSelectChatbot={onSelectChatbot}
          isLoading={isLoadingChatbots}
          error={chatbotsError}
          onRetry={onRetryChatbots}
        />
      </div>

      {/* 2. Chatbot Flows List Section */}
      <div className="sidebar-section flows-sidebar-section">
        <div className="section-header">
          <div className="section-title-group">
            <span className="section-icon">🗂️</span>
            <span className="sidebar-title">
              Flows {flows.length > 0 && `(${flows.length})`}
            </span>
          </div>

          {onRetryFlows && selectedChatbotId && (
            <button
              type="button"
              className="btn-icon-subtle"
              onClick={onRetryFlows}
              disabled={isLoadingFlows}
              title="Refresh flows list"
            >
              🔄
            </button>
          )}
        </div>

        {/* Loading State */}
        {isLoadingFlows && (
          <div className="sidebar-status-box">
            <span className="spinner-inline">⏳</span>
            <span>Loading chatbot flows...</span>
          </div>
        )}

        {/* Error State */}
        {!isLoadingFlows && flowsError && (
          <div className="sidebar-error-box">
            <span>⚠️ {flowsError}</span>
            {onRetryFlows && (
              <button
                type="button"
                className="btn btn-secondary btn-xs"
                onClick={onRetryFlows}
                style={{ marginTop: '6px' }}
              >
                Retry
              </button>
            )}
          </div>
        )}

        {/* Empty State when chatbot has 0 flows */}
        {!isLoadingFlows && !flowsError && flows.length === 0 && (
          <div className="sidebar-empty-flows">
            <span style={{ fontSize: '1.5rem' }}>📄</span>
            <p className="empty-title">No flows yet</p>
            <p className="empty-subtitle">
              {selectedChatbot ? `No flows found for "${selectedChatbot.name}".` : 'Select a chatbot to view flows.'}
            </p>
            {onCreateFlow && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={onCreateFlow}
                style={{ marginTop: '8px', width: '100%', justifyContent: 'center' }}
                title="Create a new flow for this chatbot"
              >
                ➕ Create Flow
              </button>
            )}
          </div>
        )}

        {/* List of Flows */}
        {!isLoadingFlows && !flowsError && flows.length > 0 && (
          <div className="sidebar-flows-list">
            {flows.map((flow) => {
              const isLoaded = flow.id === loadedFlowId;
              const nodeCount = flow.flow_data?.nodes?.length || 0;
              const edgeCount = flow.flow_data?.edges?.length || 0;

              return (
                <div
                  key={flow.id}
                  className={`sidebar-flow-item ${isLoaded ? 'active-flow' : ''}`}
                  onClick={() => onSelectFlow(flow)}
                  title={`Click to load "${flow.name}" into canvas`}
                >
                  <div className="flow-item-top">
                    <span className="flow-name-text">{flow.name}</span>
                    {isLoaded && <span className="active-flow-badge">Active</span>}
                  </div>

                  <div className="flow-item-details">
                    <span className="flow-item-id-tag" title={`Full ID: ${flow.id}`}>
                      ID: {flow.id.length > 12 ? `${flow.id.slice(0, 8)}...` : flow.id}
                    </span>
                    <span className="flow-counts-tag">
                      {nodeCount}n · {edgeCount}e
                    </span>
                  </div>

                  {flow.description && (
                    <p className="flow-desc-snippet">{flow.description}</p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 3. Dynamic Node Library Palette (Prebuilt & Custom) */}
      <div className="sidebar-section node-library-section">
        <div className="section-header">
          <div className="section-title-group">
            <span className="section-icon">🧩</span>
            <span className="sidebar-title">Node Library</span>
          </div>
          {onOpenCreateCustomModal && (
            <button
              type="button"
              className="btn btn-primary btn-xs"
              onClick={onOpenCreateCustomModal}
              title="Create a new custom reusable node"
            >
              ➕ Custom Node
            </button>
          )}
        </div>

        {/* Search & Category Filter Controls */}
        <div className="node-library-controls">
          <div className="search-input-wrapper">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              className="node-search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search nodes by name, type, or desc..."
            />
            {searchQuery && (
              <button
                type="button"
                className="search-clear-btn"
                onClick={() => setSearchQuery('')}
                title="Clear search"
              >
                ✕
              </button>
            )}
          </div>

          <div className="category-select-wrapper">
            <select
              className="category-filter-select"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              <option value="ALL">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* Quick Source Filter Tabs */}
          <div className="source-filter-tabs">
            <button
              type="button"
              className={`source-tab-btn ${activeTab === 'ALL' ? 'active' : ''}`}
              onClick={() => setActiveTab('ALL')}
            >
              <span>All</span>
              <span className="tab-count">{filteredNodes.length}</span>
            </button>
            <button
              type="button"
              className={`source-tab-btn ${activeTab === 'PREBUILT' ? 'active' : ''}`}
              onClick={() => setActiveTab('PREBUILT')}
            >
              <span>Prebuilt</span>
              <span className="tab-count">{prebuiltNodes.length}</span>
            </button>
            <button
              type="button"
              className={`source-tab-btn ${activeTab === 'CUSTOM' ? 'active' : ''}`}
              onClick={() => setActiveTab('CUSTOM')}
            >
              <span>Custom</span>
              <span className="tab-count">{customNodes.length}</span>
            </button>
          </div>
        </div>

        {/* Loading Indicator */}
        {isLoadingNodes && (
          <div className="sidebar-status-box" style={{ margin: '8px 0' }}>
            <span className="spinner-inline">⏳</span>
            <span>Loading node library...</span>
          </div>
        )}

        {/* Empty Search Results */}
        {!isLoadingNodes && filteredNodes.length === 0 && (
          <div className="sidebar-empty-flows" style={{ padding: '16px 8px' }}>
            <span style={{ fontSize: '1.4rem' }}>🔍</span>
            <p className="empty-title">No nodes found</p>
            <p className="empty-subtitle">
              {searchQuery ? `No matching nodes for "${searchQuery}".` : 'No nodes available in this filter.'}
            </p>
            {searchQuery && (
              <button
                type="button"
                className="btn btn-secondary btn-xs"
                onClick={() => {
                  setSearchQuery('');
                  setSelectedCategory('ALL');
                }}
                style={{ marginTop: '8px' }}
              >
                Clear Filters
              </button>
            )}
          </div>
        )}

        {/* Node Lists Display */}
        <div className="node-templates">
          {/* Section A: Prebuilt Nodes */}
          {(activeTab === 'ALL' || activeTab === 'PREBUILT') && prebuiltNodes.length > 0 && (
            <div className="node-group-container">
              {activeTab === 'ALL' && (
                <div className="node-group-header">
                  <span>⚡ PREBUILT NODES ({prebuiltNodes.length})</span>
                </div>
              )}
              {prebuiltNodes.map(renderNodeCard)}
            </div>
          )}

          {/* Section B: Custom Nodes */}
          {(activeTab === 'ALL' || activeTab === 'CUSTOM') && (
            <div className="node-group-container">
              {activeTab === 'ALL' && (
                <div className="node-group-header custom-group-header">
                  <span>🧩 CUSTOM NODES ({customNodes.length})</span>
                  {onOpenCreateCustomModal && (
                    <button
                      type="button"
                      className="btn-link-xs"
                      onClick={onOpenCreateCustomModal}
                    >
                      + Create
                    </button>
                  )}
                </div>
              )}

              {customNodes.length > 0 ? (
                customNodes.map(renderNodeCard)
              ) : activeTab === 'CUSTOM' ? (
                <div className="sidebar-empty-flows" style={{ padding: '16px 8px' }}>
                  <span style={{ fontSize: '1.5rem' }}>🧩</span>
                  <p className="empty-title">No custom nodes yet</p>
                  <p className="empty-subtitle">
                    Build custom reusable steps with your own configurable fields.
                  </p>
                  {onOpenCreateCustomModal && (
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={onOpenCreateCustomModal}
                      style={{ marginTop: '8px', width: '100%', justifyContent: 'center' }}
                    >
                      ➕ Create Custom Node
                    </button>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {/* 4. Tips & Helper */}
      <div className="sidebar-help">
        <strong>💡 Pro-tip:</strong>
        <p style={{ marginTop: '6px' }}>
          Select a chatbot above to view its saved flows. Click any flow to view and edit its diagram on the canvas.
        </p>
      </div>
    </aside>
  );
};

export default Sidebar;
