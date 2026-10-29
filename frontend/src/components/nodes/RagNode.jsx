import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import FormattedText from '../../utils/formatTemplate';
import NodeBadges from './NodeBadges';

/**
 * RagNode Component (type: "rag")
 * Cyan card representing AI/RAG detailed answers.
 * Shows "AI answer" badge, program + topic chips, standards chapter chip.
 * Has NO outgoing handle (terminal response).
 * If message is missing, displays "{program} — {topic}".
 */
const RagNode = ({ data = {}, selected }) => {
  const program = data.program || '';
  const topic = data.topic || '';
  const chapter = data.chapter || (topic.includes('standards') ? topic.replace(/.*standards_?/, '').toUpperCase() : '');

  // Default display text if message is missing
  let displayText = data.message || data.text || '';
  if (!displayText) {
    if (program && topic) {
      displayText = `${program} — ${topic.replace(/_/g, ' ')}`;
    } else if (program) {
      displayText = `${program} Overview & Guidelines`;
    } else if (topic) {
      displayText = `${topic.replace(/_/g, ' ')} Details`;
    } else {
      displayText = data.label || 'Detailed AI Response';
    }
  }

  const isPending = data.status === 'PENDING';

  return (
    <div
      className={`custom-node rag-card-node ${isPending ? 'pending-node' : ''} ${selected ? 'selected' : ''}`}
    >
      {/* Incoming Connection Handle Only (No outgoing handle) */}
      <Handle
        type="target"
        position={Position.Top}
        id="rag-in"
        className="node-main-handle"
        title="Incoming connection"
      />

      {/* Node Header */}
      <div className="node-header rag-header">
        <span className="node-header-icon" aria-hidden="true">🤖</span>
        <span className="node-header-title">{data.label || 'AI Answer'}</span>
        <span className="node-header-subbadge rag-subbadge">
          AI Answer
        </span>
      </div>

      {/* Node Body */}
      <div className="node-body rag-body">
        {/* Metadata Chips: Program, Topic, Chapter */}
        <div className="rag-chips-container">
          {program && (
            <span className="rag-chip program-chip" title={`Program: ${program}`}>
              🏷️ {program}
            </span>
          )}
          {topic && (
            <span className="rag-chip topic-chip" title={`Topic: ${topic}`}>
              📌 {topic.replace(/_/g, ' ')}
            </span>
          )}
          {chapter && (
            <span className="rag-chip chapter-chip" title={`Chapter: ${chapter}`}>
              📖 {chapter}
            </span>
          )}
        </div>

        {/* Answer Content */}
        <div className="node-text-preview rag-text-preview" title={displayText}>
          <FormattedText text={displayText} />
        </div>

        {/* Global flags: note, mapping_status */}
        <NodeBadges
          note={data.note}
          mappingStatus={data.mapping_status}
          status={data.status}
          branch={data.branch}
        />
      </div>
    </div>
  );
};

export default memo(RagNode);
