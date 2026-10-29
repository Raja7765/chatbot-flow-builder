import React from 'react';
import { Handle, Position } from '@xyflow/react';

/**
 * Universal Figma-style Node Component
 * White card, 1px border #E5E5E5, 8px radius, soft shadow, selected = 2px blue outline.
 * Colored type tag: start=green, menu=blue, rag/answer=teal, message=grey, form=orange, content=purple.
 * Status badges: PENDING=amber dashed border + chip, CONTENT_DEPENDENCY=purple chip, note=info icon.
 * Supports button rows with individual right-side handles and internal scroll if > 8 buttons.
 * Fallback node for any unknown type to ensure the canvas NEVER crashes.
 */
const FigmaDefaultNode = ({ id, data = {}, type, selected }) => {
  const nodeType = (type || data.nodeType || 'default').toLowerCase();
  const label = data.label || data.name || id;
  const message = data.message || data.text || data.description || '';
  const buttons = Array.isArray(data.buttons) ? data.buttons : [];
  const status = data.status || '';
  const isPending = status === 'PENDING';
  const isContentDep = data.note?.includes('DEPENDENCY') || nodeType === 'content';
  const note = data.note || '';
  const mappingStatus = data.mapping_status || '';

  // Type metadata
  const getTypeMeta = (t) => {
    switch (t) {
      case 'start':
        return { label: 'Start', color: '#10B981', bg: '#ECFDF5', border: '#A7F3D0' };
      case 'menu':
        return { label: 'Menu', color: '#0D99FF', bg: '#E8F5FF', border: '#BCE3FF' };
      case 'rag':
      case 'answer':
        return { label: 'RAG', color: '#0D9488', bg: '#F0FDFA', border: '#99F6E4' };
      case 'form':
        return { label: 'Form', color: '#F97316', bg: '#FFF7ED', border: '#FED7AA' };
      case 'content':
        return { label: 'Content', color: '#8B5CF6', bg: '#F5F3FF', border: '#DDD6FE' };
      case 'message':
      default:
        return { label: 'Message', color: '#6B7280', bg: '#F3F4F6', border: '#E5E7EB' };
    }
  };

  const meta = getTypeMeta(nodeType);
  const isStartNode = nodeType === 'start' || id === 'welcome';
  const isTerminalNode = nodeType === 'rag' || nodeType === 'answer';

  return (
    <div
      className={`figma-node-card ${selected ? 'selected' : ''} ${isPending ? 'pending-node' : ''}`}
      style={{
        width: 250,
      }}
    >
      {/* Incoming connection handle on left (except start node) */}
      {!isStartNode && (
        <Handle
          type="target"
          position={Position.Left}
          style={{
            left: -5,
            top: 24,
            width: 8,
            height: 8,
            background: '#0D99FF',
            border: '1.5px solid #FFFFFF',
            borderRadius: '50%',
          }}
        />
      )}

      {/* Header with Type Tag and Status Badges */}
      <div className="figma-node-header">
        <span
          className="figma-node-tag"
          style={{
            color: meta.color,
            background: meta.bg,
            border: `1px solid ${meta.border}`,
          }}
        >
          {meta.label}
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {isPending && (
            <span className="figma-status-chip figma-chip-pending" title="Pending Confirmation">
              Pending
            </span>
          )}

          {isContentDep && (
            <span className="figma-status-chip figma-chip-content-dep" title="Content Dependency">
              Content
            </span>
          )}

          {mappingStatus && (
            <span
              className="figma-status-chip"
              style={{
                background: mappingStatus.includes('PENDING') ? '#FEF3C7' : '#ECFDF5',
                color: mappingStatus.includes('PENDING') ? '#D97706' : '#059669',
                border: `1px solid ${mappingStatus.includes('PENDING') ? '#FDE68A' : '#A7F3D0'}`,
              }}
              title={`Mapping Status: ${mappingStatus}`}
            >
              {mappingStatus.includes('PENDING') ? 'Verify' : 'OK'}
            </span>
          )}

          {note && (
            <span
              style={{
                cursor: 'help',
                fontSize: '11px',
                color: '#0D99FF',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '14px',
                height: '14px',
                borderRadius: '50%',
                background: '#E8F5FF',
                border: '1px solid #BCE3FF',
              }}
              title={note}
            >
              ℹ
            </span>
          )}
        </div>
      </div>

      {/* Title */}
      <div className="figma-node-title" title={label}>
        {label}
      </div>

      {/* Message preview if available */}
      {message && (
        <div className="figma-node-body" title={message}>
          {message}
        </div>
      )}

      {/* Button Rows with individual right-side handles */}
      {buttons.length > 0 ? (
        <div
          className="figma-buttons-list"
          style={{
            maxHeight: buttons.length > 8 ? 200 : 'none',
            overflowY: buttons.length > 8 ? 'auto' : 'visible',
          }}
        >
          {buttons.map((btn, idx) => (
            <div key={btn.id || idx} className="figma-button-row">
              <span
                style={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: '200px',
                }}
                title={btn.label}
              >
                {btn.label || `Option ${idx + 1}`}
              </span>

              {/* Right-side source handle for each button */}
              <Handle
                type="source"
                position={Position.Right}
                id={btn.id || `${id}__btn_${idx}`}
                className="figma-btn-handle"
              />
            </div>
          ))}
        </div>
      ) : (
        /* Outgoing handle on right if not terminal and no individual buttons */
        !isTerminalNode && (
          <Handle
            type="source"
            position={Position.Right}
            style={{
              right: -5,
              top: 24,
              width: 8,
              height: 8,
              background: '#0D99FF',
              border: '1.5px solid #FFFFFF',
              borderRadius: '50%',
            }}
          />
        )
      )}
    </div>
  );
};

export default React.memo(FigmaDefaultNode);
