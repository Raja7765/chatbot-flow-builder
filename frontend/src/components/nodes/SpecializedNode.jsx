import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';

/**
 * Metadata and theme configurations for SEBI specialized node types.
 * Specialized nodes represent architectural pipeline steps in the flow builder.
 */
const NODE_CONFIGS = {
  router: {
    typeLabel: 'Query Router',
    icon: '🔀',
    headerColor: '#8b5cf6',
    borderClass: 'router-node-border',
    badgeText: 'DSPy + Gemini',
  },
  employee_search: {
    typeLabel: 'Employee Search',
    icon: '🔍',
    headerColor: '#f59e0b',
    borderClass: 'employee-node-border',
    badgeText: 'Directory',
  },
  rag: {
    typeLabel: 'RAG / Source',
    icon: '📚',
    headerColor: '#06b6d4',
    borderClass: 'rag-node-border',
    badgeText: 'ChromaDB + Gemini',
  },
  response: {
    typeLabel: 'SSE Response',
    icon: '📡',
    headerColor: '#ec4899',
    borderClass: 'response-node-border',
    badgeText: 'SSE Stream',
  },
  tts: {
    typeLabel: 'TTS Audio',
    icon: '🔊',
    headerColor: '#14b8a6',
    borderClass: 'tts-node-border',
    badgeText: 'Audio WAV',
  },
  llm: {
    typeLabel: 'LLM Generation',
    icon: '🤖',
    headerColor: '#6366f1',
    borderClass: 'llm-node-border',
    badgeText: 'Gemini / LLM',
  },
  api_request: {
    typeLabel: 'API Request',
    icon: '🌐',
    headerColor: '#10b981',
    borderClass: 'api-node-border',
    badgeText: 'REST HTTP',
  },
  condition: {
    typeLabel: 'Condition',
    icon: '⚖️',
    headerColor: '#eab308',
    borderClass: 'condition-node-border',
    badgeText: 'Branch / Rule',
  },
  database: {
    typeLabel: 'Database Query',
    icon: '🗄️',
    headerColor: '#3b82f6',
    borderClass: 'database-node-border',
    badgeText: 'SQL DB',
  },
};

/**
 * SpecializedNode Component
 * Renders custom React Flow nodes for Query Router, Employee Search,
 * FAQ/RAG Pipeline, SSE Streaming Response, TTS Audio Generation,
 * LLM, API Request, Condition, Database, and User-Created Custom Nodes.
 */
const SpecializedNode = ({ id, data = {}, type, selected }) => {
  const isCustom = data.node_source === 'custom' || (!NODE_CONFIGS[type] && type !== 'start' && type !== 'message');
  const config = NODE_CONFIGS[type] || {
    typeLabel: data.label || (type || 'Custom Step').replace(/_/g, ' ').toUpperCase(),
    icon: data.icon || (isCustom ? '🧩' : '⚙️'),
    headerColor: isCustom ? '#a855f7' : '#6366f1',
    borderClass: isCustom ? 'custom-node-border' : 'specialized-node-border',
    badgeText: data.category || (isCustom ? 'Custom' : 'Config'),
  };

  const label = data.label || config.typeLabel;
  const description = data.description || data.service || '';
  const subBadge = data.classifier_engine || data.vector_store || data.stream_mode || data.voice || config.badgeText;

  const hasButtons = Array.isArray(data.buttons) && data.buttons.length > 0;

  return (
    <div className={`custom-node specialized-node ${config.borderClass} ${selected ? 'selected' : ''}`}>
      {/* Incoming Connection Handle */}
      <Handle
        type="target"
        position={Position.Top}
        id={`${type}-in`}
        style={{ background: config.headerColor }}
      />

      {/* Node Header */}
      <div className="node-header">
        <span className="node-header-icon" style={{ color: config.headerColor }}>
          {config.icon}
        </span>
        <span className="node-header-title">{config.typeLabel}</span>
        <span
          className="node-header-subbadge"
          style={{
            backgroundColor: `${config.headerColor}18`,
            borderColor: `${config.headerColor}40`,
            color: '#111827',
          }}
          title={subBadge}
        >
          {subBadge.length > 18 ? `${subBadge.slice(0, 16)}...` : subBadge}
        </span>
      </div>

      {/* Node Body */}
      <div className="node-body">
        <div className="node-label">{label}</div>
        {description && (
          <div className="node-text-preview" title={description}>
            {description}
          </div>
        )}

        {/* Dynamic Buttons with Dedicated Outgoing Connection Handles */}
        {hasButtons && (
          <div className="node-buttons-container">
            {data.buttons.map((btn, idx) => (
              <div key={btn.id || idx} className="node-button-row">
                <span className="node-button-label" title={btn.label}>
                  {btn.label || `Option ${idx + 1}`}
                </span>
                <Handle
                  type="source"
                  position={Position.Right}
                  id={btn.id || `btn_${idx}`}
                  className="node-button-handle"
                  title={`Connect: ${btn.label || btn.id}`}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Default Outgoing Connection Handle (only when no buttons exist) */}
      {!hasButtons && (
        <Handle
          type="source"
          position={Position.Bottom}
          id={`${type}-out`}
          style={{ background: config.headerColor }}
        />
      )}
    </div>
  );
};

export default memo(SpecializedNode);
