import React, { useState, useRef, useEffect } from 'react';

/**
 * ChatbotSelector Component
 * Allows users to view and switch between available chatbots.
 * Displays chatbot name, unique ID, and status badge.
 * Provides loading, error, and empty states with retry capability.
 */
const ChatbotSelector = ({
  chatbots = [],
  selectedChatbotId,
  onSelectChatbot,
  isLoading = false,
  error = null,
  onRetry,
  compact = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedChatbot = chatbots.find((b) => b.id === selectedChatbotId) || null;

  const handleSelect = (botId) => {
    onSelectChatbot(botId);
    setIsOpen(false);
  };

  return (
    <div
      className={`chatbot-selector-wrapper ${compact ? 'compact' : ''}`}
      ref={containerRef}
    >
      <label className="selector-label">
        <span className="label-icon">🤖</span>
        <span>Chatbot:</span>
      </label>

      {/* Main Trigger Button */}
      <button
        type="button"
        className={`chatbot-selector-trigger ${isOpen ? 'active' : ''} ${error ? 'has-error' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading && chatbots.length === 0}
        title={selectedChatbot ? `${selectedChatbot.name} (ID: ${selectedChatbot.id})` : 'Select a Chatbot'}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        {isLoading && chatbots.length === 0 ? (
          <span className="selector-loading-text">
            <span className="spinner-inline">⏳</span> Loading chatbots...
          </span>
        ) : error && chatbots.length === 0 ? (
          <span className="selector-error-text">⚠️ Error loading chatbots</span>
        ) : selectedChatbot ? (
          <div className="selected-bot-info">
            <span className="selected-bot-name">{selectedChatbot.name}</span>
            <span className="selected-bot-id-badge" title={`Full ID: ${selectedChatbot.id}`}>
              ID: {selectedChatbot.id.length > 12 ? `${selectedChatbot.id.slice(0, 8)}...` : selectedChatbot.id}
            </span>
          </div>
        ) : (
          <span className="placeholder-text">Select a Chatbot...</span>
        )}

        <span className="dropdown-caret">{isOpen ? '▲' : '▼'}</span>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="chatbot-dropdown-menu" role="listbox">
          <div className="dropdown-header">
            <span>Available Chatbots ({chatbots.length})</span>
            {onRetry && (
              <button
                type="button"
                className="btn-link"
                onClick={(e) => {
                  e.stopPropagation();
                  onRetry();
                }}
                disabled={isLoading}
              >
                🔄 Refresh
              </button>
            )}
          </div>

          {/* Loading state */}
          {isLoading && (
            <div className="dropdown-status-box">
              <span className="spinner-inline">⏳</span>
              <span>Fetching chatbots from backend...</span>
            </div>
          )}

          {/* Error alert inside dropdown */}
          {error && (
            <div className="dropdown-error-box">
              <span>⚠️ {error}</span>
              {onRetry && (
                <button
                  type="button"
                  className="btn btn-secondary btn-xs"
                  onClick={onRetry}
                  style={{ marginTop: '6px' }}
                >
                  Retry Connection
                </button>
              )}
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && chatbots.length === 0 && (
            <div className="dropdown-empty-box">
              <p>No chatbots found on the server.</p>
            </div>
          )}

          {/* Chatbots list */}
          <div className="dropdown-list">
            {chatbots.map((bot) => {
              const isSelected = bot.id === selectedChatbotId;
              return (
                <div
                  key={bot.id}
                  className={`chatbot-option ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleSelect(bot.id)}
                  role="option"
                  aria-selected={isSelected}
                >
                  <div className="option-header">
                    <span className="option-name">{bot.name}</span>
                    <span className={`status-badge status-${bot.status || 'active'}`}>
                      {bot.status || 'active'}
                    </span>
                  </div>

                  <div className="option-meta">
                    <span className="option-id">ID: {bot.id}</span>
                    {isSelected && <span className="option-selected-check">✓ Active</span>}
                  </div>

                  {bot.description && (
                    <div className="option-desc">{bot.description}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatbotSelector;
