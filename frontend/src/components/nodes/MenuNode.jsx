import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import FormattedText from '../../utils/formatTemplate';
import NodeBadges from './NodeBadges';

/**
 * MenuNode Component (type: "menu")
 * Renders a conversation menu card with header (title = message),
 * a button-count badge, and a vertical list of button rows with individual
 * outgoing connection handles on the right.
 * Scrollable when there are more than 8 buttons. Unconnected buttons show a warning.
 */
const MenuNode = ({ data = {}, selected }) => {
  const titleText = data.message || data.text || data.label || 'Menu Options';
  const buttonsList = Array.isArray(data.buttons) ? data.buttons : [];
  const isPending = data.status === 'PENDING';
  const isScrollable = buttonsList.length > 8;

  // Branch indicator styling
  const branchClass = data.branch ? `branch-${data.branch}` : '';

  return (
    <div
      className={`custom-node menu-node ${branchClass} ${isPending ? 'pending-node' : ''} ${selected ? 'selected' : ''}`}
    >
      {/* Incoming Connection Handle */}
      <Handle
        type="target"
        position={Position.Top}
        id="menu-in"
        className="node-main-handle"
        title="Incoming connection"
      />

      {/* Node Header */}
      <div className="node-header menu-header">
        <span className="node-header-icon" aria-hidden="true">📋</span>
        <span className="node-header-title" title={data.label || 'Menu'}>
          {data.label || 'Menu Options'}
        </span>
        <span className="node-header-subbadge menu-subbadge">
          {buttonsList.length} Option{buttonsList.length === 1 ? '' : 's'}
        </span>
      </div>

      {/* Node Body */}
      <div className="node-body menu-body">
        {/* Title Message */}
        <div className="node-text-preview menu-text-preview" title={titleText}>
          <FormattedText text={titleText} />
        </div>

        {/* Global flags: note, mapping_status */}
        <NodeBadges
          note={data.note}
          mappingStatus={data.mapping_status}
          status={data.status}
          branch={data.branch}
        />

        {/* Vertical List of Button Rows */}
        {buttonsList.length > 0 && (
          <div className={`node-buttons-container ${isScrollable ? 'menu-scrollable-buttons' : ''}`}>
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
                    <span
                      className="unconnected-warning-icon"
                      title="Unconnected button branch"
                      aria-label="Unconnected button branch"
                    >
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

      {/* Default Outgoing Handle if no buttons */}
      {buttonsList.length === 0 && (
        <Handle
          type="source"
          position={Position.Bottom}
          id="menu-out"
          className="node-main-handle"
          title="Default outgoing connection"
        />
      )}
    </div>
  );
};

export default memo(MenuNode);
