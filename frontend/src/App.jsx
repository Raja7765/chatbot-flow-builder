import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow,
  Background,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react';

import FigmaTopBar from './components/figma/FigmaTopBar';
import FigmaLeftPanel from './components/figma/FigmaLeftPanel';
import FigmaPropertiesPanel from './components/figma/FigmaPropertiesPanel';
import FigmaCanvasControls from './components/figma/FigmaCanvasControls';
import FigmaDefaultNode from './components/figma/FigmaDefaultNode';

import {
  fetchChatbots,
  fetchChatbotFlows,
  fetchFlowById,
  createFlow,
  updateFlow,
} from './api/client';
import { applyDagreLayout } from './utils/autoLayout';

// Initial fallback nodes
const initialNodes = [
  {
    id: 'landing_page',
    type: 'landing_page',
    data: {
      label: 'Welcome to QMitra',
      heading: 'Welcome to QMitra',
      subtitle: 'Your Trusted Healthcare Virtual Assistant',
      card_title: 'Ready to assist you!',
      card_description: 'I can help you with healthcare information',
      button_label: 'Get Started',
      branch: 'welcome',
      buttons: [
        { id: 'landing_page__start__0', label: 'Get Started', next: 'welcome' },
      ],
    },
    position: { x: 80, y: 160 },
  },
  {
    id: 'welcome',
    type: 'start',
    data: {
      label: 'Welcome & Entry',
      message: 'Namaste! Welcome to NABH Quality Mitra.',
      branch: 'welcome',
      buttons: [
        { id: 'welcome__explore__0', label: 'Explore Programs', next: 'programs_menu' },
      ],
    },
    position: { x: 440, y: 160 },
  },
  {
    id: 'programs_menu',
    type: 'menu',
    data: {
      label: 'Explore All Programs',
      message: 'Please choose an accreditation program:',
      branch: 'programs',
      buttons: [
        { id: 'programs_menu__hosp__0', label: 'Hospital Accreditation', next: '' },
        { id: 'programs_menu__shco__1', label: 'Small Healthcare Org (SHCO)', next: '' },
      ],
    },
    position: { x: 800, y: 160 },
  },
];

const initialEdges = [
  {
    id: 'edge-landing-welcome',
    source: 'landing_page',
    sourceHandle: 'landing_page__start__0',
    target: 'welcome',
    type: 'smoothstep',
    style: { stroke: '#A3A3A3', strokeWidth: 1.5 },
  },
  {
    id: 'edge-welcome-programs',
    source: 'welcome',
    sourceHandle: 'welcome__explore__0',
    target: 'programs_menu',
    type: 'smoothstep',
    style: { stroke: '#A3A3A3', strokeWidth: 1.5 },
  },
];

// Defined OUTSIDE component: Base node types mapping
const baseNodeTypes = {
  default: FigmaDefaultNode,
  landing_page: FigmaDefaultNode,
  landing: FigmaDefaultNode,
  welcome_landing: FigmaDefaultNode,
  start: FigmaDefaultNode,
  menu: FigmaDefaultNode,
  rag: FigmaDefaultNode,
  answer: FigmaDefaultNode,
  message: FigmaDefaultNode,
  content: FigmaDefaultNode,
  form: FigmaDefaultNode,
  router: FigmaDefaultNode,
  employee_search: FigmaDefaultNode,
  response: FigmaDefaultNode,
  tts: FigmaDefaultNode,
  llm: FigmaDefaultNode,
  api_request: FigmaDefaultNode,
  condition: FigmaDefaultNode,
  database: FigmaDefaultNode,
};

// Defined OUTSIDE component: Safe Proxy ensuring unknown node types NEVER crash
const safeNodeTypes = new Proxy(baseNodeTypes, {
  get(target, prop) {
    if (typeof prop === 'string' && prop in target) {
      return target[prop];
    }
    return FigmaDefaultNode;
  },
});

// Defined OUTSIDE component: default edge options
const defaultEdgeOptions = {
  type: 'smoothstep',
  style: { stroke: '#A3A3A3', strokeWidth: 1.5 },
};

// Inner canvas component having access to ReactFlowProvider instance
const FlowCanvas = () => {
  const { fitView, getZoom } = useReactFlow();

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(100);

  // Chatbots & Flows state
  const [chatbots, setChatbots] = useState([]);
  const [selectedChatbotId, setSelectedChatbotId] = useState(null);
  const [chatbotFlows, setChatbotFlows] = useState([]);
  const [isLoadingFlows, setIsLoadingFlows] = useState(false);

  // Active Flow Identity
  const [loadedFlowId, setLoadedFlowId] = useState(null);
  const [loadedChatbotId, setLoadedChatbotId] = useState(null);
  const [flowName, setFlowName] = useState('NABH QMitra Conversation Flow');
  const [flowDescription, setFlowDescription] = useState('Wireframe flow for NABH QMitra chatbot');
  const [isSaving, setIsSaving] = useState(false);

  // Error Banner State
  const [errorBanner, setErrorBanner] = useState(null);

  // Load available chatbots with safe try/catch
  const loadChatbots = useCallback(async () => {
    try {
      const bots = await fetchChatbots();
      setChatbots(Array.isArray(bots) ? bots : []);

      let storedBotId = null;
      try {
        storedBotId = localStorage.getItem('active_chatbot_id');
      } catch {}

      setSelectedChatbotId((currentSelected) => {
        if (storedBotId && bots.some((b) => b.id === storedBotId)) {
          return storedBotId;
        }
        if (currentSelected && bots.some((b) => b.id === currentSelected)) {
          return currentSelected;
        }
        return bots.length > 0 ? bots[0].id : null;
      });
    } catch (err) {
      console.warn('[Figma UI] Failed to fetch chatbots:', err);
      setChatbots([]);
      setErrorBanner(`Backend connection: ${err.message || 'FastAPI backend unreachable'}. Running in offline canvas mode.`);
    }
  }, []);

  // Load flows for active chatbot with safe try/catch
  const loadChatbotFlows = useCallback(async (botId) => {
    if (!botId) {
      setChatbotFlows([]);
      return;
    }
    setIsLoadingFlows(true);
    try {
      const flows = await fetchChatbotFlows(botId);
      setChatbotFlows(Array.isArray(flows) ? flows : []);
    } catch (err) {
      console.warn(`[Figma UI] Failed to fetch flows for chatbot ${botId}:`, err);
      setChatbotFlows([]);
      setErrorBanner(`Could not load saved flows for chatbot: ${err.message}`);
    } finally {
      setIsLoadingFlows(false);
    }
  }, []);

  useEffect(() => {
    loadChatbots();
  }, [loadChatbots]);

  useEffect(() => {
    if (selectedChatbotId) {
      loadChatbotFlows(selectedChatbotId);
    } else {
      setChatbotFlows([]);
    }
  }, [selectedChatbotId, loadChatbotFlows]);

  // Load saved flow from backend by ID with safe try/catch and error fallback
  const handleLoadFlow = useCallback(
    async (flowId) => {
      if (!flowId) return;
      try {
        const flow = await fetchFlowById(flowId);
        if (!flow || !flow.flow_data) {
          throw new Error('Flow data payload is missing or empty.');
        }

        setLoadedFlowId(flow.id);
        setLoadedChatbotId(flow.chatbot_id || selectedChatbotId);
        setFlowName(flow.name || 'Untitled Flow');
        setFlowDescription(flow.description || '');

        try {
          localStorage.setItem('active_flow_id', flow.id);
          if (flow.chatbot_id) {
            localStorage.setItem('active_chatbot_id', flow.chatbot_id);
          }
        } catch {}

        if (flow.chatbot_id && flow.chatbot_id !== selectedChatbotId) {
          setSelectedChatbotId(flow.chatbot_id);
        }

        const rawNodes = Array.isArray(flow.flow_data.nodes) ? flow.flow_data.nodes : [];
        const rawEdges = Array.isArray(flow.flow_data.edges) ? flow.flow_data.edges : [];

        // 1. Safely normalize nodes (support both legacy top-level fields and nested node.data)
        const sanitizedNodes = rawNodes.map((n, i) => {
          const id = String(n.id || `node_${i}`);
          const nodeType = n.type || n.data?.nodeType || 'message';

          // Merge top-level legacy fields with nested n.data without overwriting valid data
          const mergedData = {
            ...n,
            ...(n.data || {}),
            nodeType,
          };
          delete mergedData.position; // Keep position strictly at node.position

          // Ensure buttons have stable IDs for handle attachment
          if (Array.isArray(mergedData.buttons)) {
            mergedData.buttons = mergedData.buttons.map((btn, btnIdx) => {
              const label = btn.label || `Option ${btnIdx + 1}`;
              const slug = label.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 24);
              return {
                ...btn,
                id: btn.id || `${id}__${slug}__${btnIdx}`,
              };
            });
          }

          return {
            ...n,
            id,
            type: nodeType,
            data: mergedData,
            position: {
              x: Number.isFinite(n.position?.x) ? Math.round(n.position.x) : NaN,
              y: Number.isFinite(n.position?.y) ? Math.round(n.position.y) : NaN,
            },
          };
        });

        // Ensure the initial Landing Page exists as entry page for the flow
        const hasLandingNode = sanitizedNodes.some(
          (n) => n.type === 'landing_page' || n.type === 'landing' || n.id === 'landing_page'
        );

        if (!hasLandingNode && sanitizedNodes.length > 0) {
          const firstConversationNode =
            sanitizedNodes.find((n) => n.id === 'welcome') ||
            sanitizedNodes.find((n) => n.type === 'start') ||
            sanitizedNodes[0];

          if (firstConversationNode) {
            const landingNode = {
              id: 'landing_page',
              type: 'landing_page',
              data: {
                label: 'Welcome to QMitra',
                heading: 'Welcome to QMitra',
                subtitle: 'Your Trusted Healthcare Virtual Assistant',
                card_title: 'Ready to assist you!',
                card_description: 'I can help you with healthcare information',
                button_label: 'Get Started',
                branch: 'welcome',
                buttons: [
                  {
                    id: 'landing_page__start__0',
                    label: 'Get Started',
                    next: firstConversationNode.id,
                  },
                ],
              },
              position: {
                x: Number.isFinite(firstConversationNode.position?.x)
                  ? firstConversationNode.position.x - 340
                  : 80,
                y: Number.isFinite(firstConversationNode.position?.y)
                  ? firstConversationNode.position.y
                  : 160,
              },
            };

            sanitizedNodes.unshift(landingNode);

            // Add connecting edge from landing_page to firstConversationNode
            const landingEdgeExists = rawEdges.some(
              (e) => String(e.source) === 'landing_page' && String(e.target) === String(firstConversationNode.id)
            );
            if (!landingEdgeExists) {
              rawEdges.unshift({
                id: `edge-landing-${firstConversationNode.id}`,
                source: 'landing_page',
                sourceHandle: 'landing_page__start__0',
                target: firstConversationNode.id,
                type: 'smoothstep',
                style: { stroke: '#A3A3A3', strokeWidth: 1.5 },
              });
            }
          }
        }

        const nodeIdsSet = new Set(sanitizedNodes.map((n) => n.id));
        const nodeMap = new Map(sanitizedNodes.map((n) => [n.id, n]));

        // 2. Safely normalize edges and resolve button handles
        const validEdges = rawEdges
          .filter((e) => e && e.source && e.target && nodeIdsSet.has(String(e.source)) && nodeIdsSet.has(String(e.target)))
          .map((e, i) => {
            const edgeId = String(e.id || `edge_${i}`);
            const source = String(e.source);
            const target = String(e.target);
            let sourceHandle = e.sourceHandle || null;

            // If edge lacks sourceHandle, attempt to match it to a button on the source node
            if (!sourceHandle) {
              const sourceNode = nodeMap.get(source);
              if (sourceNode && Array.isArray(sourceNode.data?.buttons)) {
                const matchedBtn = sourceNode.data.buttons.find(
                  (btn) => String(btn.next) === target || String(btn.target) === target
                );
                if (matchedBtn) {
                  sourceHandle = matchedBtn.id;
                }
              }
            }

            return {
              ...e,
              id: edgeId,
              source,
              target,
              ...(sourceHandle ? { sourceHandle } : {}),
              type: 'smoothstep',
              style: { stroke: '#A3A3A3', strokeWidth: 1.5 },
            };
          });

        // 3. Inspect positions: Detect missing, collapsed, or garbage coordinates
        let hasInvalidPositions = false;
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

        for (const n of sanitizedNodes) {
          if (!Number.isFinite(n.position?.x) || !Number.isFinite(n.position?.y)) {
            hasInvalidPositions = true;
            break;
          }
          // Check for extreme coordinate garbage (e.g. y < -3000 or y > 5000)
          if (n.position.y < -3000 || n.position.y > 6000 || n.position.x < -2000 || n.position.x > 30000) {
            hasInvalidPositions = true;
            break;
          }
          minX = Math.min(minX, n.position.x);
          maxX = Math.max(maxX, n.position.x);
          minY = Math.min(minY, n.position.y);
          maxY = Math.max(maxY, n.position.y);
        }

        // Check if all nodes collapsed into an overlapping cluster
        if (!hasInvalidPositions && sanitizedNodes.length > 5 && maxX - minX < 200 && maxY - minY < 200) {
          hasInvalidPositions = true;
        }

        let finalNodes = sanitizedNodes;
        let finalEdges = validEdges;

        // Apply Dagre hierarchical auto-layout if positions are missing or invalid
        if (hasInvalidPositions && sanitizedNodes.length > 0) {
          try {
            const layoutResult = applyDagreLayout(sanitizedNodes, validEdges, {
              rankdir: 'LR',
              ranksep: 220,
              nodesep: 40,
            });
            finalNodes = layoutResult.nodes;
            // Keep edge styling consistent with Figma design (#A3A3A3)
            finalEdges = layoutResult.edges.map((e) => ({
              ...e,
              style: { stroke: '#A3A3A3', strokeWidth: 1.5 },
            }));
          } catch (layoutErr) {
            console.warn('[Figma UI] Auto-layout fallback error:', layoutErr);
            finalNodes = sanitizedNodes.map((n, i) => ({
              ...n,
              position: {
                x: Number.isFinite(n.position?.x) ? n.position.x : 100 + (i % 5) * 320,
                y: Number.isFinite(n.position?.y) ? n.position.y : 100 + Math.floor(i / 5) * 160,
              },
            }));
          }
        }

        setNodes(finalNodes);
        setEdges(finalEdges);
        setSelectedNodeId(null);
        setErrorBanner(null);

        setTimeout(() => {
          if (typeof fitView === 'function') {
            fitView({ padding: 0.15, duration: 400 });
          }
        }, 100);
      } catch (err) {
        console.warn(`[Figma UI] Failed to load flow ${flowId}:`, err);
        // Clear invalid active_flow_id from localStorage to prevent stuck reload loops
        try {
          localStorage.removeItem('active_flow_id');
        } catch {}
        setLoadedFlowId(null);
        setNodes([]);
        setEdges([]);
        setErrorBanner(`Failed to load flow (${flowId}): ${err.message}. Cleared cached flow session.`);
      }
    },
    [selectedChatbotId, setNodes, setEdges, fitView]
  );

  // Restore active flow from localStorage on mount safely
  const hasRestoredFlowRef = useRef(false);
  useEffect(() => {
    if (hasRestoredFlowRef.current) return;
    try {
      const storedFlowId = localStorage.getItem('active_flow_id');
      if (storedFlowId) {
        hasRestoredFlowRef.current = true;
        handleLoadFlow(storedFlowId);
      }
    } catch (err) {
      console.warn('[Figma UI] Stored flow restoration error:', err);
      try {
        localStorage.removeItem('active_flow_id');
      } catch {}
    }
  }, [handleLoadFlow]);

  // Save active flow to SQLite backend
  const handleSaveFlow = useCallback(async () => {
    setIsSaving(true);
    try {
      const payload = {
        name: flowName,
        description: flowDescription,
        chatbot_id: loadedChatbotId || selectedChatbotId,
        flow_data: {
          nodes: nodes.map((n) => {
            const dataToSave = { ...(n.data || {}) };
            delete dataToSave.position;

            return {
              id: String(n.id),
              type: n.type || dataToSave.nodeType || 'message',
              data: dataToSave,
              position: {
                x: Math.round(n.position?.x ?? 0),
                y: Math.round(n.position?.y ?? 0),
              },
            };
          }),
          edges: edges.map((e) => ({
            id: String(e.id),
            source: String(e.source),
            target: String(e.target),
            ...(e.sourceHandle ? { sourceHandle: e.sourceHandle } : {}),
            ...(e.targetHandle ? { targetHandle: e.targetHandle } : {}),
            ...(e.label ? { label: e.label } : {}),
          })),
        },
      };

      let savedFlow;
      if (loadedFlowId) {
        savedFlow = await updateFlow(loadedFlowId, payload);
      } else {
        savedFlow = await createFlow(payload);
        setLoadedFlowId(savedFlow.id);
      }

      // Verification fetch
      const verified = await fetchFlowById(savedFlow.id);
      setLoadedFlowId(verified.id);
      try {
        localStorage.setItem('active_flow_id', verified.id);
      } catch {}

      if (selectedChatbotId) {
        loadChatbotFlows(selectedChatbotId);
      }
      setErrorBanner(null);
    } catch (err) {
      console.error('[Figma UI] Save flow failed:', err);
      setErrorBanner(`Save failed: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  }, [flowName, flowDescription, loadedChatbotId, selectedChatbotId, loadedFlowId, nodes, edges, loadChatbotFlows]);

  // Create new blank flow
  const handleCreateNewFlow = useCallback(() => {
    try {
      localStorage.removeItem('active_flow_id');
    } catch {}
    setLoadedFlowId(null);
    setFlowName('New Flow');
    setFlowDescription('');
    setNodes(initialNodes);
    setEdges(initialEdges);
    setSelectedNodeId(null);
    setErrorBanner(null);

    setTimeout(() => {
      if (typeof fitView === 'function') {
        fitView({ padding: 0.2, duration: 400 });
      }
    }, 50);
  }, [fitView, setNodes, setEdges]);

  // Node selection handlers
  const onNodeClick = useCallback((_, node) => {
    setSelectedNodeId(node?.id || null);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  const handleSelectNodeFromLayer = useCallback(
    (nodeId) => {
      setSelectedNodeId(nodeId);
      if (typeof fitView === 'function') {
        fitView({
          nodes: [{ id: nodeId }],
          duration: 500,
          maxZoom: 1.2,
          padding: 0.3,
        });
      }
    },
    [fitView]
  );

  const handleUpdateNode = useCallback(
    (nodeId, newData) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, ...newData } } : n))
      );
    },
    [setNodes]
  );

  const handleDeleteNode = useCallback(
    (nodeId) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
      setSelectedNodeId((curr) => (curr === nodeId ? null : curr));
    },
    [setNodes, setEdges]
  );

  const onConnect = useCallback(
    (params) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: 'smoothstep',
            style: { stroke: '#A3A3A3', strokeWidth: 1.5 },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  // Selected node object
  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) || null,
    [nodes, selectedNodeId]
  );

  // Track zoom level for topbar indicator
  const handleViewportChange = useCallback(() => {
    if (typeof getZoom === 'function') {
      const currentZoom = getZoom();
      setZoomLevel(Math.round(currentZoom * 100));
    }
  }, [getZoom]);

  return (
    <div className="figma-app-shell">
      {/* 1. Top Bar (48px) */}
      <FigmaTopBar
        flowName={flowName}
        onUpdateFlowName={setFlowName}
        chatbots={chatbots}
        selectedChatbotId={selectedChatbotId}
        onSelectChatbot={setSelectedChatbotId}
        onImportClick={() => {}}
        onSaveClick={handleSaveFlow}
        onExportClick={() => {}}
        zoomLevel={zoomLevel}
        isSaving={isSaving}
      />

      {/* Visible Error Banner if any API / restore issue occurs */}
      {errorBanner && (
        <div className="figma-error-banner" role="alert">
          <div className="figma-error-content">
            <span className="figma-error-icon">⚠️</span>
            <span>{errorBanner}</span>
          </div>
          <button
            type="button"
            className="figma-error-dismiss"
            onClick={() => setErrorBanner(null)}
            aria-label="Dismiss banner"
          >
            ✕
          </button>
        </div>
      )}

      {/* 2. Main Workspace Layout */}
      <div className="figma-workspace">
        {/* Left Panel (240px) */}
        <FigmaLeftPanel
          nodes={nodes}
          selectedNodeId={selectedNodeId}
          onSelectNode={handleSelectNodeFromLayer}
          flows={chatbotFlows}
          isLoadingFlows={isLoadingFlows}
          loadedFlowId={loadedFlowId}
          onLoadFlow={handleLoadFlow}
          onCreateNewFlow={handleCreateNewFlow}
        />

        {/* Center Canvas Area with explicit flex container */}
        <main className="figma-canvas-area" style={{ width: '100%', height: '100%', position: 'relative' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onMoveEnd={handleViewportChange}
            nodeTypes={safeNodeTypes}
            defaultEdgeOptions={defaultEdgeOptions}
            fitView
          >
            {/* Canvas: #F5F5F5 with a light dot grid */}
            <Background color="#D4D4D4" gap={20} size={1} />

            {/* Bottom-left: minimal zoom / fit controls */}
            <FigmaCanvasControls />

            {/* Bottom-right: clean light minimap */}
            <MiniMap
              nodeColor="#E5E5E5"
              nodeStrokeColor="#A3A3A3"
              style={{
                background: '#FFFFFF',
                border: '1px solid #E5E5E5',
                borderRadius: '8px',
              }}
            />
          </ReactFlow>
        </main>

        {/* Right Panel: Chatbot Preview & Properties */}
        <FigmaPropertiesPanel
          selectedNode={selectedNode}
          nodes={nodes}
          edges={edges}
          onSelectNode={handleSelectNodeFromLayer}
          onUpdateNode={handleUpdateNode}
          onDeleteNode={handleDeleteNode}
        />
      </div>
    </div>
  );
};

export default function App() {
  return (
    <ReactFlowProvider>
      <FlowCanvas />
    </ReactFlowProvider>
  );
}
