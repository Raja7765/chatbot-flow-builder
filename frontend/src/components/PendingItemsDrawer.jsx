import React from 'react';

/**
 * PendingItemsDrawer Component
 * Slide-out panel summarizing all PENDING / CONTENT_DEPENDENCY / VERIFY / Unconnected nodes.
 * Clicking any item smoothly focuses the canvas on that node.
 */
const PendingItemsDrawer = ({
  isOpen,
  onClose,
  nodes = [],
  edges = [],
  onSelectNode,
}) => {
  if (!isOpen) return null;

  // Filter pending or content-dependency items
  const pendingNodes = nodes.filter((n) => {
    const status = String(n.data?.status || '').toUpperCase();
    const mapping = String(n.data?.mapping_status || '').toUpperCase();
    const isContentDep = status === 'CONTENT_DEPENDENCY' || n.type === 'content';
    const isPending = status === 'PENDING' || mapping.includes('PENDING') || mapping.includes('VERIFY');
    const hasUnconnectedButtons = (n.data?.buttons || []).some((b) => !b.target && !b.next);
    return isContentDep || isPending || hasUnconnectedButtons;
  });

  return (
    <aside className="pending-items-drawer" aria-label="Pending Flow Items">
      <div className="drawer-header">
        <div className="drawer-title-group">
          <span className="drawer-icon">⏳</span>
          <div>
            <h4>Pending &amp; Review Items</h4>
            <span className="drawer-subtitle">
              {pendingNodes.length} unresolved or review items found
            </span>
          </div>
        </div>
        <button
          type="button"
          className="drawer-close-btn"
          onClick={onClose}
          aria-label="Close drawer"
        >
          ✕
        </button>
      </div>

      <div className="drawer-body">
        {pendingNodes.length === 0 ? (
          <div className="drawer-empty-msg">
            <span style={{ fontSize: '24px' }}>🎉</span>
            <p>All nodes and button branches are resolved and confirmed!</p>
          </div>
        ) : (
          <div className="drawer-items-list">
            {pendingNodes.map((node) => {
              const status = String(node.data?.status || '').toUpperCase();
              const mapping = String(node.data?.mapping_status || '').toUpperCase();
              const isContentDep = status === 'CONTENT_DEPENDENCY' || node.type === 'content';
              const unconnectedCount = (node.data?.buttons || []).filter((b) => !b.target && !b.next).length;

              return (
                <div
                  key={node.id}
                  className="drawer-item-card"
                  onClick={() => onSelectNode(node.id)}
                  title="Click to zoom to this node on canvas"
                >
                  <div className="drawer-card-header">
                    <span className="drawer-card-type">{node.type.toUpperCase()}</span>
                    <div className="drawer-badges-stack">
                      {isContentDep && (
                        <span className="badge-content-dep">CONTENT DEP</span>
                      )}
                      {status === 'PENDING' && (
                        <span className="badge-pending">PENDING</span>
                      )}
                      {mapping && mapping.includes('PENDING') && (
                        <span className="badge-verify">MAPPING PENDING</span>
                      )}
                      {unconnectedCount > 0 && (
                        <span className="badge-unconnected-count">
                          {unconnectedCount} Unlinked
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="drawer-card-title">
                    {node.data?.label || node.id}
                  </div>

                  {node.data?.note && (
                    <div className="drawer-card-note">
                      <strong>Note:</strong> {node.data.note}
                    </div>
                  )}

                  {node.data?.message && (
                    <div className="drawer-card-preview">
                      "{node.data.message.slice(0, 75)}..."
                    </div>
                  )}

                  <div className="drawer-card-action">
                    <span>Target Node ID: <code>{node.id}</code></span>
                    <span className="jump-link">Focus Node ➔</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
};

export default PendingItemsDrawer;
