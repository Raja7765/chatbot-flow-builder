import React, { useState, useMemo } from 'react';

/**
 * FigmaLeftPanel Component
 * 240px wide sidebar with tabs:
 * 1. "Layers": Tree list of all canvas nodes grouped by branch, search box, click to focus.
 * 2. "Flows": Saved flows for the active chatbot, click to load, + New Flow action.
 */
const FigmaLeftPanel = ({
  nodes = [],
  selectedNodeId,
  onSelectNode,
  flows = [],
  isLoadingFlows = false,
  loadedFlowId,
  onLoadFlow,
  onCreateNewFlow,
}) => {
  const [activeTab, setActiveTab] = useState('layers'); // 'layers' | 'flows'
  const [searchQuery, setSearchQuery] = useState('');

  // Node type dot color mapper
  const getNodeColor = (type) => {
    switch (type) {
      case 'start':
        return '#10B981';
      case 'menu':
        return '#0D99FF';
      case 'rag':
      case 'answer':
        return '#0D9488';
      case 'form':
        return '#F97316';
      case 'content':
        return '#8B5CF6';
      case 'message':
      default:
        return '#6B7280';
    }
  };

  // Filter nodes by search query
  const filteredNodes = useMemo(() => {
    if (!searchQuery.trim()) return nodes;
    const q = searchQuery.toLowerCase();
    return nodes.filter((n) => {
      const label = n.data?.label || '';
      const text = n.data?.text || n.data?.message || '';
      const id = n.id || '';
      return label.toLowerCase().includes(q) || text.toLowerCase().includes(q) || id.toLowerCase().includes(q);
    });
  }, [nodes, searchQuery]);

  // Group filtered nodes by branch
  const groupedNodes = useMemo(() => {
    const groups = {
      welcome: [],
      programs: [],
      fee_roi: [],
      eligible_programs: [],
      accounts: [],
      other: [],
    };

    filteredNodes.forEach((node) => {
      const branch =
        node.data?.branch ||
        (node.id?.startsWith('eligible_')
          ? 'eligible_programs'
          : node.id === 'welcome' || node.type === 'start'
          ? 'welcome'
          : 'other');
      if (groups[branch]) {
        groups[branch].push(node);
      } else {
        groups.other.push(node);
      }
    });

    return groups;
  }, [filteredNodes]);

  const branchTitles = {
    welcome: 'Welcome & Entry',
    programs: 'Programs',
    fee_roi: 'Fee & ROI Calculator',
    eligible_programs: 'Eligible Programs',
    accounts: 'Accounts & Login',
    other: 'Other Steps',
  };

  return (
    <aside className="figma-left-panel">
      {/* Tabs Header */}
      <div className="panel-tabs-header">
        <button
          type="button"
          className={`panel-tab-btn ${activeTab === 'layers' ? 'active' : ''}`}
          onClick={() => setActiveTab('layers')}
        >
          <span>Layers</span>
          <span className="panel-tab-count">{nodes.length}</span>
        </button>

        <button
          type="button"
          className={`panel-tab-btn ${activeTab === 'flows' ? 'active' : ''}`}
          onClick={() => setActiveTab('flows')}
        >
          <span>Flows</span>
          <span className="panel-tab-count">{flows.length}</span>
        </button>
      </div>

      {/* Tab 1: Layers */}
      {activeTab === 'layers' && (
        <div className="panel-body-content">
          <div className="layers-search-box">
            <div className="search-input-field-wrap">
              <span className="search-input-icon">🔍</span>
              <input
                type="text"
                className="search-input-clean"
                placeholder="Search layers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          <div className="layers-tree-list">
            {filteredNodes.length === 0 ? (
              <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                No layers found
              </div>
            ) : (
              Object.entries(groupedNodes).map(([branchKey, branchNodes]) => {
                if (branchNodes.length === 0) return null;
                return (
                  <div key={branchKey} className="layer-branch-group">
                    <div className="branch-group-header">
                      <span>{branchTitles[branchKey] || branchKey}</span>
                      <span>{branchNodes.length}</span>
                    </div>

                    {branchNodes.map((node) => {
                      const isSelected = node.id === selectedNodeId;
                      const dotColor = getNodeColor(node.type);
                      const displayName = node.data?.label || node.data?.message?.slice(0, 24) || node.id;

                      return (
                        <div
                          key={node.id}
                          className={`layer-node-item ${isSelected ? 'selected' : ''}`}
                          onClick={() => onSelectNode(node.id)}
                          title={`${displayName} (${node.id})`}
                        >
                          <div className="layer-node-info">
                            <span className="layer-type-dot" style={{ backgroundColor: dotColor }} />
                            <span className="layer-node-name">{displayName}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Flows */}
      {activeTab === 'flows' && (
        <div className="panel-body-content">
          <div className="flows-tab-header">
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Saved Flows
            </span>
            <button
              type="button"
              className="btn-figma-secondary btn-figma-sm"
              onClick={onCreateNewFlow}
              title="Create a new flow"
            >
              + New Flow
            </button>
          </div>

          <div className="flows-list-items">
            {isLoadingFlows ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                Loading flows...
              </div>
            ) : flows.length === 0 ? (
              <div style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                No saved flows for this chatbot.
              </div>
            ) : (
              flows.map((flow) => {
                const isActive = flow.id === loadedFlowId;
                const nodeCount = flow.flow_data?.nodes?.length || 0;
                const edgeCount = flow.flow_data?.edges?.length || 0;

                return (
                  <div
                    key={flow.id}
                    className={`flow-card-item ${isActive ? 'active' : ''}`}
                    onClick={() => onLoadFlow(flow.id)}
                  >
                    <div className="flow-card-title">
                      <span>{flow.name || 'Untitled Flow'}</span>
                      {isActive && <span className="flow-active-badge">Active</span>}
                    </div>
                    <div className="flow-card-meta">
                      <span>{nodeCount} nodes • {edgeCount} edges</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </aside>
  );
};

export default React.memo(FigmaLeftPanel);
