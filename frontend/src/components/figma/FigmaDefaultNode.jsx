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
  const label = data.label || data.name || data.title || id;
  const program = data.program || '';
  const topic = data.topic || '';
  const chapter = data.chapter || '';
  const explicitMessage = data.message || data.content || data.text || data.description || '';

  // Compute effective display message
  let displayMessage = explicitMessage;
  if (!displayMessage) {
    if (program || topic || chapter) {
      const parts = [chapter, program, topic].filter(Boolean);
      displayMessage = parts.join(' — ');
    } else if (nodeType === 'landing_page' || nodeType === 'landing' || id === 'landing_page') {
      displayMessage = data.subtitle || data.card_description || 'Your Trusted Healthcare Virtual Assistant';
    } else if (Array.isArray(data.fields) && data.fields.length > 0) {
      displayMessage = `Fields: ${data.fields
        .map((f) => (typeof f === 'string' ? f : f.name || f.label || ''))
        .filter(Boolean)
        .join(', ')}`;
    }
  }

  const buttons = Array.isArray(data.buttons) ? data.buttons : [];
  const status = data.status || '';
  const isPending = status === 'PENDING';
  const isContentDep = data.note?.includes('DEPENDENCY') || nodeType === 'content';
  const note = data.note || '';
  const mappingStatus = data.mapping_status || '';

  // Type metadata
  const getTypeMeta = (t) => {
    switch (t) {
      case 'landing_page':
      case 'landing':
        return { label: 'Landing Page', color: '#0284C7', bg: '#E0F2FE', border: '#BAE6FD' };
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
  const isStartNode = nodeType === 'start' || nodeType === 'landing_page' || nodeType === 'landing' || id === 'landing_page' || id === 'welcome';
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

      {/* Message preview or fallback */}
      {displayMessage ? (
        <div className="figma-node-body" title={displayMessage}>
          {displayMessage}
        </div>
      ) : buttons.length === 0 ? (
        <div className="figma-node-body" style={{ color: '#9CA3AF', fontStyle: 'italic' }}>
          No message configured
        </div>
      ) : null}

      {/* Button Rows with individual right-side handles */}
      {buttons.length > 0 && (
        <div
          className="figma-buttons-list"
          style={{
            maxHeight: buttons.length > 8 ? 200 : 'none',
            overflowY: buttons.length > 8 ? 'auto' : 'visible',
          }}
        >
          {buttons.map((btn, idx) => {
            const btnSlug = (btn.label || `opt_${idx}`).toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 24);
            const btnHandleId = btn.id || `${id}__${btnSlug}__${idx}`;

            return (
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
                  id={btnHandleId}
                  className="figma-btn-handle"
                />
              </div>
            );
          })}
        </div>
      )}

      {/* Fallback outgoing handle on right for edges without specific button sourceHandle */}
      {!isTerminalNode && (
        <Handle
          type="source"
          position={Position.Right}
          style={{
            right: -5,
            top: buttons.length > 0 ? 24 : '50%',
            transform: buttons.length > 0 ? 'none' : 'translateY(-50%)',
            width: 8,
            height: 8,
            background: '#0D99FF',
            border: '1.5px solid #FFFFFF',
            borderRadius: '50%',
          }}
        />
      )}
    </div>
  );
};

export default React.memo(FigmaDefaultNode);
