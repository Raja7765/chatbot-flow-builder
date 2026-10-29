import React from 'react';

/**
 * NodeBadges Component
 * Renders global flags and status indicators for any node:
 * - note: Info icon (ℹ️) with tooltip
 * - mapping_status: Colored chip (PENDING = amber, VERIFY = orange, OK/MAPPED = green)
 * - branch: subtle branch pill
 */
export function NodeBadges({ note, mappingStatus, status, branch }) {
  if (!note && !mappingStatus && !status && !branch) return null;

  // Compute color for mapping_status
  const getStatusColor = (val) => {
    const s = String(val || '').toUpperCase();
    if (s.includes('PENDING')) return { bg: 'rgba(245, 158, 11, 0.2)', border: 'rgba(245, 158, 11, 0.4)', text: '#fbbf24' };
    if (s.includes('VERIFY') || s.includes('PARTIAL')) return { bg: 'rgba(249, 115, 22, 0.2)', border: 'rgba(249, 115, 22, 0.4)', text: '#fb923c' };
    if (s.includes('MAPPED') || s === 'OK' || s.includes('CONFIRMED')) return { bg: 'rgba(16, 185, 129, 0.2)', border: 'rgba(16, 185, 129, 0.4)', text: '#34d399' };
    return { bg: 'rgba(148, 163, 184, 0.2)', border: 'rgba(148, 163, 184, 0.3)', text: '#cbd5e1' };
  };

  const statusStyle = mappingStatus ? getStatusColor(mappingStatus) : null;

  return (
    <div className="node-global-badges-row">
      {/* mapping_status chip */}
      {mappingStatus && (
        <span
          className="node-status-chip"
          style={{
            backgroundColor: statusStyle.bg,
            borderColor: statusStyle.border,
            color: statusStyle.text,
          }}
          title={`Mapping Status: ${mappingStatus}`}
        >
          {mappingStatus.replace(/_/g, ' ')}
        </span>
      )}

      {/* note info tooltip */}
      {note && (
        <span className="node-note-badge" title={`Note: ${note}`}>
          <span className="node-note-icon" aria-hidden="true">ℹ️</span>
        </span>
      )}
    </div>
  );
}

export default NodeBadges;
