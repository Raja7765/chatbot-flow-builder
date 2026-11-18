import React, { useMemo, useCallback } from 'react';

/**
 * Synchronize flow edges with node buttons.
 * Preserves existing edge IDs, source handles, and updates targets/labels.
 * Removes orphaned edges for deleted buttons, and creates smoothstep edges for new links.
 */
export function syncEdgesForButtons(nodeId, newButtons, currentEdges = []) {
  const strNodeId = String(nodeId);
  const otherEdges = currentEdges.filter((e) => String(e.source) !== strNodeId);
  const nodeOutgoingEdges = currentEdges.filter((e) => String(e.source) === strNodeId);

  const usedEdgeIds = new Set();
  const updatedNodeEdges = [];

  newButtons.forEach((btn, idx) => {
    const targetNodeId = btn.next ? String(btn.next).trim() : '';
    if (!targetNodeId) {
      // Button has no target destination configured; skip creating an edge
      return;
    }

    const btnSlug = (btn.label || `opt_${idx}`)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .slice(0, 24);
    const expectedHandleId = btn.id || `${strNodeId}__${btnSlug}__${idx}`;

    // Priority 1: Match by exact sourceHandle
    let matchedEdge = nodeOutgoingEdges.find(
      (e) => !usedEdgeIds.has(e.id) && btn.id && e.sourceHandle === btn.id
    );

    // Priority 2: Match by target destination (handles existing flows where sourceHandle wasn't stored)
    if (!matchedEdge) {
      matchedEdge = nodeOutgoingEdges.find(
        (e) => !usedEdgeIds.has(e.id) && String(e.target) === targetNodeId
      );
    }

    // Priority 3: Match by label
    if (!matchedEdge && btn.label) {
      matchedEdge = nodeOutgoingEdges.find(
        (e) => !usedEdgeIds.has(e.id) && e.label === btn.label
      );
    }

    if (matchedEdge) {
      usedEdgeIds.add(matchedEdge.id);
      updatedNodeEdges.push({
        ...matchedEdge,
        target: targetNodeId,
        label: btn.label || matchedEdge.label || '',
        // If button has an explicit ID, ensure handle matches
        ...(btn.id ? { sourceHandle: btn.id } : matchedEdge.sourceHandle ? { sourceHandle: matchedEdge.sourceHandle } : {}),
      });
    } else {
      // Create new edge connecting button to destination
      const newEdgeId = `edge-${strNodeId}-${targetNodeId}-${btn.id || Math.random().toString(36).substring(2, 7)}`;
      updatedNodeEdges.push({
        id: newEdgeId,
        source: strNodeId,
        target: targetNodeId,
        ...(btn.id ? { sourceHandle: btn.id } : { sourceHandle: expectedHandleId }),
        label: btn.label || '',
        type: 'smoothstep',
        style: { stroke: '#A3A3A3', strokeWidth: 1.5 },
      });
    }
  });

  return [...otherEdges, ...updatedNodeEdges];
}

/**
 * NodeButtonsEditor Component
 * Embedded in FigmaPropertiesPanel to allow full management of individual buttons inside a node:
 * - Edit button labels
 * - Change destination (next) via node dropdown
 * - Add new buttons
 * - Delete buttons
 * - Reorder buttons (Move Up / Down)
 * - Immediate canvas & React Flow edge synchronization
 * - Direct save to PostgreSQL flow persistence
 */
const NodeButtonsEditor = ({
  node,
  nodes = [],
  edges = [],
  onUpdateNode,
  onUpdateEdges,
  onUpdateNodeAndEdges,
  onSaveFlow,
  isSavingFlow = false,
}) => {
  const nodeId = node?.id;
  const nodeData = node?.data || {};
  const buttons = Array.isArray(nodeData.buttons) ? nodeData.buttons : [];

  // Candidate destination nodes (all nodes in flow except current node)
  const destinationOptions = useMemo(() => {
    return nodes
      .filter((n) => String(n.id) !== String(nodeId))
      .map((n) => {
        const nLabel = n.data?.label || n.data?.name || n.data?.title || n.id;
        return {
          id: String(n.id),
          label: nLabel,
          display: `${nLabel} (${n.id})`,
        };
      })
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [nodes, nodeId]);

  // Dispatch synchronized node and edges update
  const propagateButtonsUpdate = useCallback(
    (newButtons) => {
      if (!nodeId) return;
      const updatedEdges = syncEdgesForButtons(nodeId, newButtons, edges);

      if (typeof onUpdateNodeAndEdges === 'function') {
        onUpdateNodeAndEdges(nodeId, { buttons: newButtons }, updatedEdges);
      } else {
        if (typeof onUpdateNode === 'function') {
          onUpdateNode(nodeId, { buttons: newButtons });
        }
        if (typeof onUpdateEdges === 'function') {
          onUpdateEdges(updatedEdges);
        }
      }
    },
    [nodeId, edges, onUpdateNodeAndEdges, onUpdateNode, onUpdateEdges]
  );

  // Edit button label
  const handleLabelChange = (idx, newLabel) => {
    const updated = buttons.map((b, i) => (i === idx ? { ...b, label: newLabel } : b));
    propagateButtonsUpdate(updated);
  };

  // Change button destination (next)
  const handleDestinationChange = (idx, newTarget) => {
    const updated = buttons.map((b, i) => (i === idx ? { ...b, next: newTarget } : b));
    propagateButtonsUpdate(updated);
  };

  // Add new button
  const handleAddButton = () => {
    const nextIdx = buttons.length;
    const btnSlug = `opt_${Date.now().toString(36).slice(-4)}`;
    const newBtnId = `${nodeId}__${btnSlug}__${nextIdx}`;
    const newBtn = {
      id: newBtnId,
      label: `Option ${nextIdx + 1}`,
      next: '',
    };
    const updated = [...buttons, newBtn];
    propagateButtonsUpdate(updated);
  };

  // Delete button
  const handleDeleteButton = (idx) => {
    const updated = buttons.filter((_, i) => i !== idx);
    propagateButtonsUpdate(updated);
  };

  // Reorder: Move Up
  const handleMoveUp = (idx) => {
    if (idx === 0) return;
    const copy = [...buttons];
    const temp = copy[idx - 1];
    copy[idx - 1] = copy[idx];
    copy[idx] = temp;
    propagateButtonsUpdate(copy);
  };

  // Reorder: Move Down
  const handleMoveDown = (idx) => {
    if (idx >= buttons.length - 1) return;
    const copy = [...buttons];
    const temp = copy[idx + 1];
    copy[idx + 1] = copy[idx];
    copy[idx] = temp;
    propagateButtonsUpdate(copy);
  };

  return (
    <div className="figma-buttons-editor">
      {/* Section Header */}
      <div className="figma-buttons-header">
        <span className="figma-label" style={{ marginBottom: 0 }}>
          Buttons / Choices ({buttons.length})
        </span>

        <button
          type="button"
          className="btn-add-choice"
          onClick={handleAddButton}
          title="Add a new button choice to this node"
        >
          + Add Button
        </button>
      </div>

      {/* Buttons List */}
      {buttons.length === 0 ? (
        <div
          style={{
            fontSize: '11px',
            color: '#94A3B8',
            fontStyle: 'italic',
            background: 'var(--panel-hover)',
            padding: '8px 10px',
            borderRadius: 'var(--radius-sm)',
            border: '1px dashed var(--border-color)',
            textAlign: 'center',
          }}
        >
          No buttons configured. Click <strong>+ Add Button</strong> to create interactive choices.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {buttons.map((btn, idx) => {
            const isFirst = idx === 0;
            const isLast = idx === buttons.length - 1;
            const targetId = btn.next || '';
            const targetNode = nodes.find((n) => String(n.id) === String(targetId));
            const targetLabel = targetNode?.data?.label || targetNode?.id || targetId;

            return (
              <div key={btn.id || `btn_${idx}`} className="figma-btn-item-card">
                {/* Item Top Bar */}
                <div className="figma-btn-item-top">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0 }}>
                    <span className="figma-btn-index-badge">#{idx + 1}</span>
                    <span
                      className={`figma-btn-dest-tag ${targetId ? '' : 'unlinked'}`}
                      title={targetId ? `Destination: ${targetLabel} (${targetId})` : 'No destination connected'}
                    >
                      {targetId ? `→ ${targetLabel}` : '⚠️ Unlinked'}
                    </span>
                  </div>

                  {/* Actions: Move Up, Move Down, Delete */}
                  <div className="figma-btn-actions">
                    <button
                      type="button"
                      className="figma-btn-move-btn"
                      disabled={isFirst}
                      onClick={() => handleMoveUp(idx)}
                      title="Move button up"
                      aria-label="Move up"
                    >
                      ▲
                    </button>
                    <button
                      type="button"
                      className="figma-btn-move-btn"
                      disabled={isLast}
                      onClick={() => handleMoveDown(idx)}
                      title="Move button down"
                      aria-label="Move down"
                    >
                      ▼
                    </button>
                    <button
                      type="button"
                      className="figma-btn-move-btn delete"
                      onClick={() => handleDeleteButton(idx)}
                      title="Delete button"
                      aria-label="Delete button"
                    >
                      🗑
                    </button>
                  </div>
                </div>

                {/* Input: Button Label */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  <label
                    className="figma-label"
                    style={{ fontSize: '10px', color: '#64748B' }}
                    htmlFor={`btn-lbl-${idx}`}
                  >
                    Button Label
                  </label>
                  <input
                    id={`btn-lbl-${idx}`}
                    type="text"
                    className="figma-input"
                    style={{ fontSize: '12px', padding: '4px 8px' }}
                    value={btn.label || ''}
                    onChange={(e) => handleLabelChange(idx, e.target.value)}
                    placeholder="Button label..."
                  />
                </div>

                {/* Select: Destination (next) */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  <label
                    className="figma-label"
                    style={{ fontSize: '10px', color: '#64748B' }}
                    htmlFor={`btn-target-${idx}`}
                  >
                    Destination Node (next)
                  </label>
                  <select
                    id={`btn-target-${idx}`}
                    className="figma-select"
                    style={{ fontSize: '11px', padding: '4px 24px 4px 8px' }}
                    value={targetId}
                    onChange={(e) => handleDestinationChange(idx, e.target.value)}
                  >
                    <option value="">-- None (Unlinked) --</option>
                    {/* If current target is not in destinationOptions, preserve it as an option */}
                    {targetId && !destinationOptions.some((o) => o.id === targetId) && (
                      <option value={targetId}>
                        {targetLabel} ({targetId}) [Current]
                      </option>
                    )}
                    {destinationOptions.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.display}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Identifier subtle tag */}
                {btn.id && (
                  <div
                    style={{
                      fontSize: '9.5px',
                      color: '#94A3B8',
                      fontFamily: 'monospace',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={`Handle ID: ${btn.id}`}
                  >
                    id: {btn.id}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Save Flow to PostgreSQL Action */}
      {typeof onSaveFlow === 'function' && (
        <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid #E2E8F0' }}>
          <button
            type="button"
            className="btn-figma-primary"
            style={{
              width: '100%',
              justifyContent: 'center',
              gap: '6px',
              background: '#0F172A',
              color: '#FFFFFF',
              padding: '7px 10px',
              fontSize: '11.5px',
              fontWeight: 600,
              borderRadius: '6px',
              cursor: isSavingFlow ? 'not-allowed' : 'pointer',
              border: 'none',
              opacity: isSavingFlow ? 0.7 : 1,
            }}
            onClick={onSaveFlow}
            disabled={isSavingFlow}
            title="Persist flow and updated buttons to PostgreSQL database"
          >
            {isSavingFlow ? (
              <>
                <svg className="spin-animation" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                </svg>
                <span>Saving Flow to PostgreSQL...</span>
              </>
            ) : (
              <>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                  <polyline points="17 21 17 13 7 13 7 21"></polyline>
                  <polyline points="7 3 7 8 15 8"></polyline>
                </svg>
                <span>Save Flow to Database</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default React.memo(NodeButtonsEditor);
