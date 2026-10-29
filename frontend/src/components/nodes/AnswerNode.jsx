import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';

/**
 * AnswerNode Component
 * Renders an Answer node for displaying configured responses with optional
 * manual source citation metadata (document name, page number, source URL).
 * Follows the theme palette: background #164E63, text #F8FAFC, selection #7C3AED.
 */
const AnswerNode = ({ data = {}, selected }) => {
  const answerText = data.answer_text || data.text || 'No answer text configured';
  const hasSource = Boolean(data.source_document || data.page_number || data.source_url);

  return (
    <div className={`custom-node answer-node ${selected ? 'selected' : ''}`}>
      {/* Incoming Connection Handle */}
      <Handle
        type="target"
        position={Position.Top}
        id="ans-in"
        className="node-main-handle"
        title="Incoming connection"
      />

      {/* Node Header */}
      <div className="node-header answer-header">
        <span className="node-header-icon" aria-hidden="true">💡</span>
        <span className="node-header-title">{data.label || 'Answer'}</span>
        <span className="node-header-subbadge answer-subbadge">Answer</span>
      </div>

      {/* Node Body */}
      <div className="node-body answer-body">
        <div className="node-text-preview answer-text-preview" title={answerText}>
          {answerText}
        </div>

        {/* Optional Manual Source Citation Metadata */}
        {hasSource && (
          <div className="answer-source-card">
            <div className="answer-source-title">Source Citation</div>
            {data.source_document && (
              <div className="answer-source-item" title={data.source_document}>
                <span className="source-icon" aria-hidden="true">📄</span>
                <span className="source-doc-name">{data.source_document}</span>
                {data.page_number && (
                  <span className="source-page-badge">p. {data.page_number}</span>
                )}
              </div>
            )}
            {data.source_url && (
              <div className="answer-source-item">
                <span className="source-icon" aria-hidden="true">🔗</span>
                <a
                  href={data.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="source-url-link"
                  title={data.source_url}
                  onClick={(e) => e.stopPropagation()}
                >
                  {data.source_url.length > 32
                    ? `${data.source_url.slice(0, 30)}...`
                    : data.source_url}
                </a>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Outgoing Connection Handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="ans-out"
        className="node-main-handle"
        title="Outgoing connection"
      />
    </div>
  );
};

export default memo(AnswerNode);
