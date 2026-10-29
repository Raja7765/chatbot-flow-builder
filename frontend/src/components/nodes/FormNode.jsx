import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import FormattedText from '../../utils/formatTemplate';
import NodeBadges from './NodeBadges';

/**
 * FormNode Component (type: "form")
 * Renders a form card showing title, description, input fields mockup
 * (label + required asterisk), progress stepper, and Continue/Back buttons
 * with their own individual outgoing handles.
 */
const FormNode = ({ data = {}, selected }) => {
  const title = data.label || 'Input Form';
  const description = data.description || data.message || data.text || '';
  const fields = Array.isArray(data.fields) ? data.fields : [];
  const buttonsList = Array.isArray(data.buttons) ? data.buttons : [];
  const progressSteps = data.progress_steps;

  return (
    <div className={`custom-node form-node ${selected ? 'selected' : ''}`}>
      {/* Incoming Handle */}
      <Handle
        type="target"
        position={Position.Top}
        id="form-in"
        className="node-main-handle"
        title="Incoming connection"
      />

      {/* Node Header */}
      <div className="node-header form-header">
        <span className="node-header-icon" aria-hidden="true">📝</span>
        <span className="node-header-title">{title}</span>
        <span className="node-header-subbadge form-subbadge">
          FORM
        </span>
      </div>

      {/* Node Body */}
      <div className="node-body form-body">
        {/* Progress Stepper if available */}
        {progressSteps && (
          <div className="form-progress-stepper" title={`Progress: ${progressSteps.current || 1} of ${progressSteps.total || 4}`}>
            <div className="stepper-label">
              Step {progressSteps.current || 1} of {progressSteps.total || 4}
            </div>
            <div className="stepper-dots">
              {Array.from({ length: progressSteps.total || 4 }).map((_, i) => (
                <span
                  key={i}
                  className={`stepper-dot ${i + 1 <= (progressSteps.current || 1) ? 'active' : ''}`}
                />
              ))}
            </div>
          </div>
        )}

        {/* Description */}
        {description && (
          <div className="node-text-preview form-text-preview" title={description}>
            <FormattedText text={description} />
          </div>
        )}

        {/* Mock Input Fields */}
        {fields.length > 0 && (
          <div className="form-fields-mockup-list">
            {fields.map((f, idx) => {
              const fieldLabel = typeof f === 'string' ? f : (f.label || f.name || `Field ${idx + 1}`);
              const isRequired = typeof f === 'object' ? f.required !== false : true;
              const fieldType = typeof f === 'object' ? f.type || 'text' : 'text';

              return (
                <div key={idx} className="form-field-mockup-item">
                  <div className="field-mockup-label">
                    <span>{fieldLabel}</span>
                    {isRequired && <span className="input-required-star">*</span>}
                  </div>
                  <div className="field-mockup-input">
                    <span className="field-type-tag">{fieldType}</span>
                    <span className="field-placeholder">
                      {f.placeholder || `Enter ${fieldLabel}...`}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Global Flags */}
        <NodeBadges
          note={data.note}
          mappingStatus={data.mapping_status}
          status={data.status}
          branch={data.branch}
        />

        {/* Action Buttons (Continue, Back, Submit) */}
        {buttonsList.length > 0 && (
          <div className="node-buttons-container">
            {buttonsList.map((btn, idx) => {
              const isUnconnected = !btn.target && !btn.next;
              return (
                <div
                  key={btn.id || idx}
                  className={`node-button-row form-action-button ${isUnconnected ? 'unconnected-branch' : ''}`}
                >
                  <span className="node-button-label" title={btn.label}>
                    <FormattedText text={btn.label || `Option ${idx + 1}`} />
                  </span>

                  {isUnconnected && (
                    <span className="unconnected-warning-icon" title="Unconnected action branch">
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
          id="form-out"
          className="node-main-handle"
          title="Outgoing connection"
        />
      )}
    </div>
  );
};

export default memo(FormNode);
