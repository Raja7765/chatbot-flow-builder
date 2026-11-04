import React, { useState, useEffect, useRef } from 'react';

/**
 * NodeSearchModal Component (Ctrl+K)
 * Fast fuzzy search across all nodes on the canvas.
 * Clicking or pressing Enter centers the canvas onto the selected node.
 */
const NodeSearchModal = ({ isOpen, onClose, nodes = [], onSelectNode }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredNodes = nodes.filter((node) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    const idMatch = node.id.toLowerCase().includes(q);
    const labelMatch = (node.data?.label || '').toLowerCase().includes(q);
    const msgMatch = (node.data?.message || node.data?.text || '').toLowerCase().includes(q);
    const progMatch = (node.data?.program || '').toLowerCase().includes(q);
    const topicMatch = (node.data?.topic || '').toLowerCase().includes(q);
    return idMatch || labelMatch || msgMatch || progMatch || topicMatch;
  });

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < filteredNodes.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredNodes[selectedIndex]) {
        onSelectNode(filteredNodes[selectedIndex].id);
        onClose();
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div className="modal-backdrop search-modal-backdrop" onClick={onClose}>
      <div
        className="modal-container node-search-modal"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '580px', width: '90%' }}
      >
        <div className="search-input-wrapper">
          <span className="search-icon">🔍</span>
          <input
            ref={inputRef}
            type="text"
            className="search-input-field"
            placeholder="Search nodes by label, ID, program, topic... (Esc to close)"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
          />
          <span className="search-count-pill">{filteredNodes.length} nodes</span>
        </div>

        <div className="search-results-list">
          {filteredNodes.length === 0 ? (
            <div className="search-empty-state">No matching nodes found for "{query}"</div>
          ) : (
            filteredNodes.slice(0, 30).map((node, idx) => (
              <div
                key={node.id}
                className={`search-result-item ${idx === selectedIndex ? 'active' : ''}`}
                onClick={() => {
                  onSelectNode(node.id);
                  onClose();
                }}
                onMouseEnter={() => setSelectedIndex(idx)}
              >
                <div className="result-main-line">
                  <span className={`result-type-tag type-${node.type}`}>
                    {node.type.toUpperCase()}
                  </span>
                  <span className="result-label">{node.data?.label || node.id}</span>
                  {node.data?.branch && (
                    <span className={`result-branch-chip branch-${node.data.branch}`}>
                      {node.data.branch}
                    </span>
                  )}
                </div>
                <div className="result-sub-line">
                  <span className="result-id">ID: <code>{node.id}</code></span>
                  {node.data?.program && (
                    <span className="result-program">🏷️ {node.data.program}</span>
                  )}
                  {node.data?.topic && (
                    <span className="result-topic">📌 {node.data.topic}</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default NodeSearchModal;
