/**
 * autoLayout.js
 * High-performance DAG auto-layout utility powered by Dagre.
 * Handles ~250+ nodes in Left-to-Right (LR) orientation, intelligently
 * filtering out cycle back-edges so ranks stay balanced, and computing
 * hierarchical branch depths for level-based expansion/collapsing.
 */

import dagre from 'dagre';

/**
 * Calculates estimated visual node dimensions for accurate Dagre layout spacing.
 */
function getNodeDimensions(node) {
  const buttonCount = Array.isArray(node.data?.buttons) ? node.data.buttons.length : 0;
  const fieldCount = Array.isArray(node.data?.fields) ? node.data.fields.length : 0;

  let width = 290;
  let height = 120;

  switch (node.type) {
    case 'start':
      width = 300;
      height = 90 + buttonCount * 36;
      break;
    case 'menu':
      width = 290;
      // Cap visual height if more than 8 buttons (due to internal scroll container)
      const visibleButtons = Math.min(buttonCount, 8);
      height = 100 + visibleButtons * 36 + (buttonCount > 8 ? 20 : 0);
      break;
    case 'rag':
      width = 280;
      height = 150;
      break;
    case 'content':
      width = 280;
      height = 130 + buttonCount * 36;
      break;
    case 'form':
      width = 310;
      height = 140 + fieldCount * 38 + buttonCount * 36;
      break;
    case 'answer':
      width = 280;
      height = 140;
      break;
    default:
      width = 280;
      height = 110 + buttonCount * 36;
      break;
  }

  return { width, height };
}

/**
 * Runs Dagre layout across nodes and edges in LR direction.
 *
 * @param {Array} nodes - React Flow nodes array
 * @param {Array} edges - React Flow edges array
 * @param {Object} options - Custom ranksep, nodesep, etc.
 * @returns {Object} { nodes: laidOutNodes, edges: laidOutEdges }
 */
export function applyDagreLayout(nodes, edges, options = {}) {
  if (!nodes || nodes.length === 0) {
    return { nodes: [], edges: [] };
  }

  const rankdir = options.rankdir || 'LR';
  const ranksep = options.ranksep || 220;
  const nodesep = options.nodesep || 40;

  const g = new dagre.graphlib.Graph({ multigraph: true });
  g.setGraph({
    rankdir,
    ranksep,
    nodesep,
    edgesep: 30,
    marginx: 80,
    marginy: 80,
  });
  g.setDefaultEdgeLabel(() => ({}));

  // 1. Add nodes with dynamic dimension estimates
  const dimensionsMap = new Map();
  nodes.forEach((node) => {
    const dims = getNodeDimensions(node);
    dimensionsMap.set(node.id, dims);
    g.setNode(node.id, { width: dims.width, height: dims.height });
  });

  // 2. Identify cycle back-edges to exclude from DAG rank construction
  // This prevents back-links like accounts_login -> welcome from ruining the horizontal layout
  const nonCycleEdges = [];
  const cycleEdgesSet = new Set();

  edges.forEach((edge) => {
    const isTargetStart = edge.target === 'welcome' || edge.target === 'start';
    const isSelfLoop = edge.source === edge.target;
    const isKnownCycle = edge.isBackEdge || isTargetStart || isSelfLoop;

    if (isKnownCycle) {
      cycleEdgesSet.add(edge.id);
    } else {
      nonCycleEdges.push(edge);
      // Only add forward edges to Dagre graph
      try {
        g.setEdge(edge.source, edge.target, {}, edge.id);
      } catch (e) {
        // Fallback for unexpected edge issues
      }
    }
  });

  // 3. Execute Dagre layout
  dagre.layout(g);

  // 4. Map computed positions back to React Flow coordinates (top-left)
  const laidOutNodes = nodes.map((node) => {
    const dagreNode = g.node(node.id);
    const dims = dimensionsMap.get(node.id) || { width: 280, height: 120 };

    if (!dagreNode) {
      return node;
    }

    const x = Math.round(dagreNode.x - dims.width / 2);
    const y = Math.round(dagreNode.y - dims.height / 2);

    return {
      ...node,
      position: { x, y },
      data: {
        ...node.data,
        layoutWidth: dims.width,
        layoutHeight: dims.height,
        rank: dagreNode.rank,
      },
    };
  });

  // 5. Ensure cycle edges are visually tagged with dashed purple styling
  const laidOutEdges = edges.map((edge) => {
    const isCycle = cycleEdgesSet.has(edge.id);
    return {
      ...edge,
      type: 'smoothstep',
      animated: isCycle,
      isBackEdge: isCycle,
      style: isCycle
        ? { stroke: '#7C3AED', strokeDasharray: '6,6', strokeWidth: 2 }
        : { stroke: '#7C3AED', strokeWidth: 2 },
    };
  });

  return { nodes: laidOutNodes, edges: laidOutEdges };
}

/**
 * Computes tree depth levels starting from root node (default: 'welcome' or 'start').
 * Used for scale/hierarchy collapsing (showing first 3 levels by default).
 */
export function computeNodeDepths(nodes, edges, rootId = 'welcome') {
  const depthMap = new Map();
  const childrenMap = new Map();

  nodes.forEach((n) => {
    childrenMap.set(n.id, []);
  });

  edges.forEach((e) => {
    if (!e.isBackEdge && childrenMap.has(e.source)) {
      childrenMap.get(e.source).push(e.target);
    }
  });

  // Determine actual root ID
  const effectiveRoot = nodes.find((n) => n.id === rootId)
    ? rootId
    : nodes.find((n) => n.type === 'start')?.id || nodes[0]?.id;

  if (!effectiveRoot) return depthMap;

  const queue = [{ id: effectiveRoot, depth: 1 }];
  depthMap.set(effectiveRoot, 1);
  const visited = new Set([effectiveRoot]);

  while (queue.length > 0) {
    const { id, depth } = queue.shift();
    const children = childrenMap.get(id) || [];

    children.forEach((childId) => {
      if (!visited.has(childId)) {
        visited.add(childId);
        depthMap.set(childId, depth + 1);
        queue.push({ id: childId, depth: depth + 1 });
      }
    });
  }

  // Any unreached nodes get depth 4
  nodes.forEach((n) => {
    if (!depthMap.has(n.id)) {
      depthMap.set(n.id, 4);
    }
  });

  return depthMap;
}
