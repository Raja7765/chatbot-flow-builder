import React from 'react';
import ChatbotSelector from './ChatbotSelector';

const TopBar = ({
  chatbots = [],
  selectedChatbotId,
  onSelectChatbot,
  isLoadingChatbots,
  chatbotsError,
  onRetryChatbots,
  onSave,
  onExportJson,
  onReset,
  onOpenLoadModal,
  onOpenImportModal,
  onRelayout,
  onOpenSearch,
  onOpenWireframeExport,
  onTogglePendingDrawer,
  pendingCount = 0,
  filterMode = 'all',
  onSetFilterMode,
  onExpandAll,
  onCollapseAll,
  nodeCount,
  edgeCount,
  loadedFlowId,
  flowName,
  activeTracePath = null,
  onClearTracePath,
}) => {
  return (
    <>
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-icon">🤖</div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span className="brand-title">Chatbot Flow Builder</span>
            {flowName && (
              <span style={{ fontSize: '0.725rem', color: '#38bdf8', fontWeight: 500 }} title={flowName}>
                {flowName.length > 32 ? `${flowName.slice(0, 30)}...` : flowName}
              </span>
            )}
          </div>

          {/* Chatbot Selector in TopBar */}
          <div className="header-chatbot-selector">
            <ChatbotSelector
              chatbots={chatbots}
              selectedChatbotId={selectedChatbotId}
              onSelectChatbot={onSelectChatbot}
              isLoading={isLoadingChatbots}
              error={chatbotsError}
              onRetry={onRetryChatbots}
              compact={true}
            />
          </div>

          <span className="flow-badge">
            {nodeCount} Nodes · {edgeCount} Edges
          </span>

          {loadedFlowId && (
            <span className="flow-badge active-flow-id-badge" title={`Flow ID: ${loadedFlowId}`}>
              ID: {loadedFlowId.slice(0, 8)}...
            </span>
          )}
        </div>

        {/* Middle Toolbar Controls */}
        <div className="header-middle-toolbar">
          {/* Search Trigger */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onOpenSearch}
            title="Search nodes by label or ID (Ctrl+K)"
          >
            🔍 Search <kbd className="kbd-shortcut">Ctrl+K</kbd>
          </button>

          {/* Re-Layout Button */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRelayout}
            title="Re-run Dagre Left-to-Right auto layout"
          >
            📐 Re-layout
          </button>

          {/* Hierarchy Toggles */}
          <div className="btn-group-toggle">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onExpandAll}
              title="Expand all branches"
            >
              Expand All
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onCollapseAll}
              title="Collapse deeper levels"
            >
              Collapse L3+
            </button>
          </div>

          {/* Filter Mode Dropdown */}
          <select
            className="header-filter-select"
            value={filterMode}
            onChange={(e) => onSetFilterMode(e.target.value)}
            title="Filter nodes on the canvas"
          >
            <option value="all">Filter: All Nodes</option>
            <option value="hide_pending">Hide Pending</option>
            <option value="only_pending">Show Only Pending</option>
          </select>

          {/* Pending Items Drawer Trigger */}
          <button
            type="button"
            className={`btn btn-secondary btn-sm ${pendingCount > 0 ? 'btn-has-pending' : ''}`}
            onClick={onTogglePendingDrawer}
            title="View unresolved flow items and content dependencies"
          >
            ⏳ Pending {pendingCount > 0 ? `(${pendingCount})` : ''}
          </button>
        </div>

        {/* Right Header Actions */}
        <div className="header-actions">
          {/* Import Flow JSON */}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onOpenImportModal}
            title="Import and normalize flow JSON (e.g. nabh_qmitra_flow.json)"
          >
            📥 Import Flow
          </button>

          {/* Load Saved Flow */}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onOpenLoadModal}
            title="Browse and load saved flows for the current chatbot"
          >
            📂 Load Flow
          </button>

          {/* Export Wireframe */}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onOpenWireframeExport}
            title="Export wireframe diagram (PNG, PDF, Mermaid, CSV)"
          >
            📤 Export Wireframe
          </button>

          {/* Reset */}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onReset}
            title="Reset canvas to default initial state"
          >
            🔄 Reset
          </button>

          {/* Save Flow */}
          <button
            type="button"
            className="btn btn-primary"
            onClick={onSave}
            title="Save flow to database"
          >
            💾 Save Flow
          </button>
        </div>
      </header>

      {/* Breadcrumb Path Trace Bar (Active during path tracing) */}
      {activeTracePath && (
        <div className="trace-path-bar" role="navigation" aria-label="Conversation Path">
          <div className="trace-path-content">
            <span className="trace-label">Active Path:</span>
            {activeTracePath.map((item, idx) => (
              <React.Fragment key={item.id}>
                <span className={`trace-item ${idx === activeTracePath.length - 1 ? 'current' : ''}`}>
                  {item.label}
                </span>
                {idx < activeTracePath.length - 1 && (
                  <span className="trace-arrow">➔</span>
                )}
              </React.Fragment>
            ))}
          </div>
          <button
            type="button"
            className="btn-clear-trace"
            onClick={onClearTracePath}
            title="Clear path trace"
          >
            ✕ Clear Trace
          </button>
        </div>
      )}
    </>
  );
};

export default TopBar;
