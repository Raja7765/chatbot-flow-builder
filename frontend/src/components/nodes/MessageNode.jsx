import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import FormattedText from '../../utils/formatTemplate';
import NodeBadges from './NodeBadges';

/**
 * MessageNode Component (type: "message")
 * Neutral dark card (#1E293B).
 * If status is PENDING, renders an amber dashed border and "PENDING CONFIRMATION" badge.
 * Supports template variables chips, buttons, and user input mockups.
 */
const MessageNode = ({ data = {}, selected }) => {
  const messageText = data.message || data.text || 'No message configured';
  const buttonsList = Array.isArray(data.buttons) ? data.buttons : [];
  const inputFields = Array.isArray(data.input_fields) ? data.input_fields : [];
  const hasButtons = buttonsList.length > 0;
  const hasInputFields = inputFields.length > 0;
  const isPending = data.status === 'PENDING';

  return (
    <div
      className={`custom-node message-node ${isPending ? 'pending-node' : ''} ${selected ? 'selected' : ''}`}
    >
      {/* Incoming Connection Handle */}
      <Handle
        type="target"
        position={Position.Top}
        id="msg-in"
        className="node-main-handle"
        title="Incoming connection"
      />

      {/* Node Header */}
      <div className="node-header message-header">
        <span className="node-header-icon" aria-hidden="true">
          {hasInputFields ? '📝' : isPending ? '⏳' : '💬'}
        </span>
        <span className="node-header-title">{data.label || 'Message'}</span>
        <span className="node-header-subbadge message-subbadge">
          {isPending
            ? 'PENDING'
            : hasInputFields && hasButtons
            ? `Form + ${buttonsList.length} Btns`
            : hasButtons
            ? `${buttonsList.length} Options`
            : 'Message'}
        </span>
      </div>

      {/* Node Body */}
      <div className="node-body message-body">
        {/* PENDING CONFIRMATION Banner if pending */}
        {isPending && (
          <div className="pending-confirmation-banner">
            <span className="pending-icon">⚠️</span>
            <span>PENDING CONFIRMATION</span>
          </div>
        )}

        {/* Message Preview with Template Variable Chip Support */}
        <div className="node-text-preview message-text-preview" title={messageText}>
          <FormattedText text={messageText} />
        </div>

        {/* Global Flags */}
        <NodeBadges
          note={data.note}
          mappingStatus={data.mapping_status}
          status={data.status}
          branch={data.branch}
        />

        {/* Optional User Input Fields Mockup */}
        {hasInputFields && (
          <div className="node-input-mockup-container">
            {inputFields.map((field, idx) => (
              <div key={field.id || idx} className="node-input-mockup-row">
                <div className="node-input-mockup-label">
                  <span>{field.label || `Field ${idx + 1}`}</span>
                  {field.required && <span className="input-required-star">*</span>}
                </div>
                <div className="node-input-mockup-box" title={field.placeholder || 'User input'}>
                  <span className="input-field-icon" aria-hidden="true">
                    {field.type === 'email'
                      ? '✉️'
                      : field.type === 'tel'
                      ? '📱'
                      : field.type === 'password'
                      ? '🔒'
                      : '✏️'}
                  </span>
                  <span className="input-placeholder-text">
                    {field.placeholder || `Enter ${field.label || 'value'}...`}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Interactive Buttons with dedicated outgoing branching handles */}
        {hasButtons && (
          <div className={`node-buttons-container ${buttonsList.length > 6 ? 'compact-buttons-list' : ''}`}>
            {buttonsList.map((btn, idx) => {
              const isUnconnected = !btn.target && !btn.next;
              return (
                <div
                  key={btn.id || idx}
                  className={`node-button-row ${isUnconnected ? 'unconnected-branch' : ''}`}
                >
                  <span className="node-button-label" title={btn.label}>
                    <FormattedText text={btn.label || `Option ${idx + 1}`} />
                  </span>

                  {isUnconnected && (
                    <span className="unconnected-warning-icon" title="Branch not connected yet">
                      ⚠️
                    </span>
                  )}

                  <Handle
                    type="source"
                    position={Position.Right}
                    id={btn.id}
                    className={`node-button-handle ${isUnconnected ? 'handle-unconnected' : ''}`}
                    title={
                      isUnconnected
                        ? `Branch unconnected (drag or select destination)`
                        : `Branch: ${btn.label || btn.id} -> ${btn.target || btn.next}`
                    }
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Default Outgoing Handle (when no buttons are configured) */}
      {!hasButtons && (
        <Handle
          type="source"
          position={Position.Bottom}
          id="msg-out"
          className="node-main-handle"
          title="Default outgoing connection"
        />
      )}
    </div>
  );
};

export default memo(MessageNode);
