import React, { useState, useEffect } from 'react';

/**
 * FigmaTopBar Component
 * 48px high top bar adhering to Figma design aesthetics:
 * - Editable flow name inline
 * - Chatbot selector dropdown
 * - Action buttons: Import JSON, Save, Export
 * - Canvas Zoom % indicator
 */
const FigmaTopBar = ({
  flowName = 'Untitled Flow',
  onUpdateFlowName,
  chatbots = [],
  selectedChatbotId,
  onSelectChatbot,
  onImportClick,
  onSaveClick,
  onExportClick,
  zoomLevel = 100,
  hasUnsavedChanges = false,
  isSaving = false,
}) => {
  const [isEditingName, setIsEditingName] = useState(false);
  const [currentName, setCurrentName] = useState(flowName);

  useEffect(() => {
    setCurrentName(flowName);
  }, [flowName]);

  const handleNameBlur = () => {
    setIsEditingName(false);
    const trimmed = currentName.trim();
    if (trimmed && trimmed !== flowName && onUpdateFlowName) {
      onUpdateFlowName(trimmed);
    } else {
      setCurrentName(flowName);
    }
  };

  const handleNameKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.target.blur();
    } else if (e.key === 'Escape') {
      setCurrentName(flowName);
      setIsEditingName(false);
    }
  };

  return (
    <header className="figma-topbar">
      {/* Left: Brand Logo & Editable Flow Name */}
      <div className="topbar-left">
        <div className="figma-brand-logo">
          <div className="figma-logo-icon">F</div>
          <span>FlowBuilder</span>
        </div>

        <div className="topbar-separator" />

        <div className="editable-flow-name-container">
          <input
            type="text"
            className="flow-name-input"
            value={currentName}
            onChange={(e) => setCurrentName(e.target.value)}
            onFocus={() => setIsEditingName(true)}
            onBlur={handleNameBlur}
            onKeyDown={handleNameKeyDown}
            title="Click to rename flow"
            placeholder="Untitled Flow"
          />
        </div>
      </div>

      {/* Center: Chatbot Selector */}
      <div className="topbar-center">
        <div className="topbar-chatbot-selector">
          <label htmlFor="topbar-chatbot-dropdown" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Chatbot:
          </label>
          <select
            id="topbar-chatbot-dropdown"
            className="chatbot-select-dropdown"
            value={selectedChatbotId || ''}
            onChange={(e) => onSelectChatbot(e.target.value)}
          >
            {chatbots.length === 0 ? (
              <option value="">No chatbots</option>
            ) : (
              chatbots.map((bot) => (
                <option key={bot.id} value={bot.id}>
                  {bot.name}
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Right: Actions & Zoom */}
      <div className="topbar-right">
        <div className="zoom-indicator-badge" title="Canvas zoom level">
          {Math.round(zoomLevel)}%
        </div>

        <button
          type="button"
          className="btn-figma-secondary btn-figma-sm"
          onClick={onImportClick}
          title="Import flow from JSON"
        >
          <span>📁</span>
          <span>Import JSON</span>
        </button>

        <button
          type="button"
          className="btn-figma-secondary btn-figma-sm"
          onClick={onExportClick}
          title="Export wireframe options (PNG, PDF, Mermaid, CSV)"
        >
          <span>↗</span>
          <span>Export</span>
        </button>

        <button
          type="button"
          className="btn-figma-primary btn-figma-sm"
          onClick={onSaveClick}
          disabled={isSaving}
          title="Save flow to database"
        >
          <span>💾</span>
          <span>{isSaving ? 'Saving...' : 'Save'}</span>
        </button>
      </div>
    </header>
  );
};

export default React.memo(FigmaTopBar);
