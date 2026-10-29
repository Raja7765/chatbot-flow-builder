import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import FormattedText from '../../utils/formatTemplate';
import NodeBadges from './NodeBadges';

/**
 * ContentNode Component (type: "content")
 * Purple card for images, testimonials, or external content dependencies.
 * Shows "CONTENT DEPENDENCY" badge and note text prominently.
 */
const ContentNode = ({ data = {}, selected }) => {
  const displayText = data.message || data.text || data.label || 'Content item';
  const buttonsList = Array.isArray(data.buttons) ? data.buttons : [];

  return (
    <div className={`custom-node content-node ${selected ? 'selected' : ''}`}>
      {/* Incoming Connection Handle */}
      <Handle
        type="target"
        position={Position.Top}
        id="content-in"
        className="node-main-handle"
        title="Incoming connection"
      />

      {/* Node Header */}
      <div className="node-header content-header">
        <span className="node-header-icon" aria-hidden="true">🖼️</span>
        <span className="node-header-title">{data.label || 'Content'}</span>
        <span className="node-header-subbadge content-subbadge">
          CONTENT DEPENDENCY
        </span>
      </div>

      {/* Node Body */}
      <div className="node-body content-body">
        {/* Prominent Note Box if present */}
        {data.note && (
          <div className="content-dependency-box">
            <span className="dep-icon" aria-hidden="true">⚠️</span>
            <div className="dep-text">
              <strong>Dependency Note:</strong> {data.note}
            </div>
          </div>
        )}

        {/* Message Content Preview */}
        <div className="node-text-preview content-text-preview" title={displayText}>
          <FormattedText text={displayText} />
        </div>

        {/* Global Flags */}
        <NodeBadges
          mappingStatus={data.mapping_status}
          status={data.status}
          branch={data.branch}
        />

        {/* Action Buttons if any */}
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
                    <span className="unconnected-warning-icon" title="Unconnected button branch">
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

      {/* Outgoing Handle if no buttons */}
      {buttonsList.length === 0 && (
        <Handle
          type="source"
          position={Position.Bottom}
          id="content-out"
          className="node-main-handle"
          title="Outgoing connection"
        />
      )}
    </div>
  );
};

export default memo(ContentNode);
