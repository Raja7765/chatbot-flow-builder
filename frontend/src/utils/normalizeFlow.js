/**
 * normalizeFlow.js
 * Normalizes input flow JSON (including NABH QMitra flow structures) into
 * clean React Flow nodes and edges, generating stable button handles,
 * reconstructing edges exclusively from button targets, and validating the graph.
 */

export function slug(str) {
  if (!str) return 'opt';
  return String(str)
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'opt';
}

/**
 * Normalizes a raw flow JSON payload into standard React Flow nodes and edges.
 * Ignores any pre-stored position values.
 *
 * @param {Object|string} rawInput - The parsed JSON object or raw JSON string.
 * @returns {Object} { nodes, edges, validation, metadata }
 */
export function normalizeFlow(rawInput) {
  let data = rawInput;
  if (typeof rawInput === 'string') {
    data = JSON.parse(rawInput);
  }

  // Handle both { nodes: [...], edges: [...] } and { flow_data: { nodes, edges } }
  let rawNodes = [];
  if (Array.isArray(data)) {
    rawNodes = data;
  } else if (Array.isArray(data?.nodes)) {
    rawNodes = data.nodes;
  } else if (Array.isArray(data?.flow_data?.nodes)) {
    rawNodes = data.flow_data.nodes;
  }

  const nodesMap = new Map();
  const duplicateIds = new Set();
  const missingTargetNodes = [];
  const buttonsWithoutNext = [];

  // Pass 1: Parse and normalize nodes
  rawNodes.forEach((rawNode, index) => {
    if (!rawNode) return;
    const rawId = String(rawNode.id || `node_${index + 1}`).trim();
    if (nodesMap.has(rawId)) {
      duplicateIds.add(rawId);
    }

    // Determine normalized node type
    let nodeType = (rawNode.type || '').toLowerCase();
    const hasButtons = Array.isArray(rawNode.buttons) && rawNode.buttons.length > 0;
    const hasFields = Array.isArray(rawNode.fields) && rawNode.fields.length > 0;
    const isWelcome = rawId === 'welcome' || rawId === 'start';

    if (!nodeType) {
      if (isWelcome) {
        nodeType = 'start';
      } else if (rawNode.status === 'CONTENT_DEPENDENCY') {
        nodeType = 'content';
      } else if (hasFields) {
        nodeType = 'form';
      } else if (hasButtons) {
        nodeType = 'menu';
      } else if (rawNode.program || rawNode.topic) {
        nodeType = 'rag';
      } else {
        nodeType = 'message';
      }
    } else if (nodeType === 'buttons' || nodeType === 'options') {
      nodeType = 'menu';
    }

    // Extract message/text content
    const messageContent =
      rawNode.message ||
      rawNode.text ||
      rawNode.data?.message ||
      rawNode.data?.text ||
      '';

    // Normalize buttons with stable unique IDs
    const rawButtons = Array.isArray(rawNode.buttons)
      ? rawNode.buttons
      : Array.isArray(rawNode.data?.buttons)
      ? rawNode.data.buttons
      : [];

    const normalizedButtons = rawButtons.map((btn, btnIdx) => {
      const btnLabel = String(btn?.label || btn?.text || `Option ${btnIdx + 1}`).trim();
      const stableBtnId = `${rawId}__${slug(btnLabel)}__${btnIdx}`;
      const targetId = btn?.next !== undefined ? String(btn.next).trim() : (btn?.target !== undefined ? String(btn.target).trim() : '');

      if (!targetId) {
        buttonsWithoutNext.push({
          nodeId: rawId,
          nodeLabel: rawNode.data?.label || rawId,
          buttonLabel: btnLabel,
          buttonId: stableBtnId,
        });
      }

      return {
        id: stableBtnId,
        label: btnLabel,
        next: targetId,
        target: targetId,
      };
    });

    // Detect branch category for swimlanes / grouping
    let branch = 'general';
    const lowerId = rawId.toLowerCase();
    const lowerTopic = String(rawNode.topic || '').toLowerCase();
    const lowerProgram = String(rawNode.program || '').toLowerCase();

    if (
      lowerId.includes('programs') ||
      lowerId.includes('accreditation') ||
      lowerId.includes('certification') ||
      lowerId.includes('empanelment') ||
      lowerId.includes('hospitals') ||
      lowerId.includes('shco') ||
      lowerId.includes('standards') ||
      lowerProgram.length > 0
    ) {
      branch = 'programs';
    } else if (
      lowerId.includes('fee') ||
      lowerId.includes('roi') ||
      lowerId.includes('calculator') ||
      lowerTopic.includes('fee')
    ) {
      branch = 'fee_roi';
    } else if (
      lowerId.includes('eligible') ||
      lowerId.includes('eligibility') ||
      lowerId.includes('facility') ||
      lowerId.includes('beds') ||
      lowerTopic.includes('eligibility')
    ) {
      branch = 'eligible_programs';
    } else if (
      lowerId.includes('account') ||
      lowerId.includes('login') ||
      lowerId.includes('otp') ||
      lowerId.includes('portal')
    ) {
      branch = 'accounts';
    }

    const nodeData = {
      label: rawNode.data?.label || rawNode.id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      message: messageContent,
      text: messageContent,
      buttons: normalizedButtons,
      program: rawNode.program || rawNode.data?.program || '',
      topic: rawNode.topic || rawNode.data?.topic || '',
      status: rawNode.status || rawNode.data?.status || 'OK',
      note: rawNode.note || rawNode.data?.note || '',
      mapping_status: rawNode.mapping_status || rawNode.data?.mapping_status || '',
      fields: Array.isArray(rawNode.fields)
        ? rawNode.fields
        : Array.isArray(rawNode.data?.fields)
        ? rawNode.data.fields
        : [],
      description: rawNode.description || rawNode.data?.description || '',
      progress_steps: rawNode.progress_steps || rawNode.data?.progress_steps || null,
      context: rawNode.context || rawNode.data?.context || null,
      branch: branch,
      expanded: true, // For scale collapse/expand hierarchy
    };

    nodesMap.set(rawId, {
      id: rawId,
      type: nodeType,
      position: { x: 0, y: 0 }, // Garbage positions discarded, auto-layout will compute clean coordinates
      data: nodeData,
    });
  });

  // Pass 2: Rebuild edges strictly from buttons
  const normalizedEdges = [];
  const edgeDeduplicationSet = new Set();
  const targetIncomingCounts = new Map();

  nodesMap.forEach((node, sourceId) => {
    const buttons = node.data.buttons || [];
    buttons.forEach((btn) => {
      const targetId = btn.next;
      if (!targetId) return;

      // Check if target node exists in graph
      if (!nodesMap.has(targetId)) {
        missingTargetNodes.push({
          sourceId,
          sourceLabel: node.data.label || sourceId,
          buttonLabel: btn.label,
          targetId,
        });
        return;
      }

      // Unique edge key by (source, sourceHandle, target)
      const edgeKey = `${sourceId}__${btn.id}__${targetId}`;
      if (edgeDeduplicationSet.has(edgeKey)) return;
      edgeDeduplicationSet.add(edgeKey);

      // Track incoming count for edge label decluttering
      targetIncomingCounts.set(targetId, (targetIncomingCounts.get(targetId) || 0) + 1);

      // Detect cycles/back-edges (e.g. target is welcome or parent)
      const isBackEdge =
        targetId === 'welcome' ||
        targetId === 'start' ||
        targetId === sourceId ||
        (sourceId.includes('login') && targetId === 'welcome');

      normalizedEdges.push({
        id: `edge_${sourceId}_${btn.id}_${targetId}`,
        source: sourceId,
        sourceHandle: btn.id,
        target: targetId,
        label: btn.label,
        type: 'smoothstep',
        animated: isBackEdge,
        isBackEdge,
        style: isBackEdge
          ? { stroke: '#7C3AED', strokeDasharray: '5,5', strokeWidth: 2 }
          : { stroke: '#7C3AED', strokeWidth: 2 },
      });
    });
  });

  // Pass 3: Edge label decluttering for high in-degree nodes (e.g. benefits_question, *_fee_structure)
  normalizedEdges.forEach((edge) => {
    const inCount = targetIncomingCounts.get(edge.target) || 0;
    if (inCount >= 4) {
      // Hide static label by default to prevent overlapping, reveal on hover
      edge.hideLabelByDefault = true;
    }
  });

  // Pass 4: Orphan and Dead-End Node Validation
  const orphanNodes = [];
  const deadEndNodes = [];

  nodesMap.forEach((node, nodeId) => {
    const inCount = targetIncomingCounts.get(nodeId) || 0;
    const isStart = nodeId === 'welcome' || nodeId === 'start' || node.type === 'start';
    if (inCount === 0 && !isStart) {
      orphanNodes.push({
        id: nodeId,
        label: node.data.label || nodeId,
        type: node.type,
      });
    }

    const hasOutgoing = (node.data.buttons || []).some((b) => Boolean(b.next));
    const isTerminalType = node.type === 'rag' || node.type === 'answer';
    if (!hasOutgoing && !isTerminalType && !isStart) {
      deadEndNodes.push({
        id: nodeId,
        label: node.data.label || nodeId,
        type: node.type,
        status: node.data.status,
      });
    }
  });

  const nodesList = Array.from(nodesMap.values());

  const validation = {
    totalNodes: nodesList.length,
    totalEdges: normalizedEdges.length,
    missingTargetNodes,
    orphanNodes,
    deadEndNodes,
    duplicateIds: Array.from(duplicateIds),
    buttonsWithoutNext,
    hasIssues:
      missingTargetNodes.length > 0 ||
      orphanNodes.length > 0 ||
      duplicateIds.size > 0 ||
      buttonsWithoutNext.length > 0,
  };

  return {
    nodes: nodesList,
    edges: normalizedEdges,
    validation,
    flowName: data.name || data.flowName || 'NABH QMitra Conversation Flow',
    description: data.description || 'Normalized conversation flow for NABH QMitra chatbot',
  };
}
