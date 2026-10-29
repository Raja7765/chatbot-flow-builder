import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import FormattedText from '../../utils/formatTemplate';
import NodeBadges from './NodeBadges';

/**
 * StartNode Component (type: "start")
 * Green card/pill (#166534) with chat-bubble icon and welcome message.
 * Supports outgoing branch buttons (e.g. the 4 welcome branch choices).
 */
const StartNode = ({ data = {}, selected }) => {
  const displayText = data.message || data.text || data.description || 'Welcome to NABH QMitra';
  const buttonsList = Array.isArray(data.buttons) ? data.buttons : [];

  return (
    <div className={`custom-node start-node ${selected ? 'selected' : ''}`}>
      {/* Node Header */}
      <div className="node-header start-header">
        <span className="node-header-icon" aria-hidden="true">💬</span>
        <span className="node-header-title">{data.label || 'Welcome'}</span>
        <span className="node-header-subbadge start-subbadge">START</span>
      </div>

      {/* Node Body */}
      <div className="node-body start-body">
        <div className="node-text-preview start-text-preview" title={displayText}>
          <FormattedText text={displayText} />
        </div>

        {/* Global Flags */}
        <NodeBadges
          note={data.note}
          mappingStatus={data.mapping_status}
          status={data.status}
          branch={data.branch}
        />

        {/* Interactive Buttons with dedicated outgoing branching handles */}
        {buttonsList.length > 0 && (
          <div className="node-buttons-container">
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
                    <span className="unconnected-warning-icon" title="Unconnected branch">
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

      {/* Fallback Outgoing Handle if no buttons configured */}
      {buttonsList.length === 0 && (
        <Handle
          type="source"
          position={Position.Bottom}
          id="start-out"
          className="node-main-handle"
          title="Start connection"
        />
      )}
    </div>
  );
};

export default memo(StartNode);
