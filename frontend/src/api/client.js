/**
 * Reusable frontend API client for communicating with the FastAPI backend.
 * Provides unified error handling and typed response parsing for Chatbots and Flows.
 */

export const API_BASE_URL = 'http://127.0.0.1:8000';

/**
 * Helper to process HTTP responses and standardize network / server errors.
 */
async function handleResponse(response, contextDescription) {
  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string'
          ? errorJson.detail
          : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Response body wasn't JSON, fallback to status text
    }
    throw new Error(`${contextDescription} failed (HTTP ${response.status}: ${errorDetail})`);
  }

  try {
    return await response.json();
  } catch (err) {
    throw new Error(`Failed to parse JSON response: ${err.message}`);
  }
}

/**
 * Fetch all available chatbots.
 * GET /chatbots
 * @returns {Promise<Array<{id: string, name: string, description: string, status: string, created_at: string, updated_at: string}>>}
 */
export async function fetchChatbots() {
  try {
    const response = await fetch(`${API_BASE_URL}/chatbots`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    const data = await handleResponse(response, 'Fetching chatbots');
    return Array.isArray(data) ? data : [];
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Fetch a single chatbot by ID.
 * GET /chatbots/{chatbot_id}
 * @param {string} chatbotId
 */
export async function fetchChatbotById(chatbotId) {
  if (!chatbotId) throw new Error('Chatbot ID is required.');
  try {
    const response = await fetch(`${API_BASE_URL}/chatbots/${encodeURIComponent(chatbotId)}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return await handleResponse(response, `Fetching chatbot ${chatbotId}`);
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Fetch all flows associated with a specific chatbot.
 * GET /chatbots/{chatbot_id}/flows
 * @param {string} chatbotId
 * @returns {Promise<Array<Object>>}
 */
export async function fetchChatbotFlows(chatbotId) {
  if (!chatbotId) throw new Error('Chatbot ID is required to fetch flows.');
  try {
    const response = await fetch(`${API_BASE_URL}/chatbots/${encodeURIComponent(chatbotId)}/flows`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    const data = await handleResponse(response, `Fetching flows for chatbot ${chatbotId}`);
    return Array.isArray(data) ? data : [];
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Fetch a single flow by its unique ID.
 * GET /flows/{flow_id}
 * @param {string} flowId
 */
export async function fetchFlowById(flowId) {
  if (!flowId) throw new Error('Flow ID is required.');
  try {
    const response = await fetch(`${API_BASE_URL}/flows/${encodeURIComponent(flowId)}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return await handleResponse(response, `Fetching flow ${flowId}`);
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Fetch all flows across all chatbots (fallback/legacy).
 * GET /flows
 */
export async function fetchAllFlows() {
  try {
    const response = await fetch(`${API_BASE_URL}/flows`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    const data = await handleResponse(response, 'Fetching all flows');
    return Array.isArray(data) ? data : [];
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Create a new flow on the backend.
 * POST /flows
 * @param {Object} payload - { name: string, description?: string, chatbot_id?: string, flow_data: { nodes: Array, edges: Array } }
 * @returns {Promise<Object>} The created FlowResponse object with generated ID and timestamps.
 */
export async function createFlow(payload) {
  if (!payload) throw new Error('Flow payload is required to create a flow.');
  const nodeCount = payload.flow_data?.nodes?.length || 0;
  const edgeCount = payload.flow_data?.edges?.length || 0;
  console.log(`[API client] POST /flows - Saving new flow "${payload.name}" with ${nodeCount} nodes, ${edgeCount} edges`);
  try {
    const response = await fetch(`${API_BASE_URL}/flows`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
    console.log(`[API client] POST /flows response status: ${response.status}`);
    const result = await handleResponse(response, 'Creating flow');
    console.log(`[API client] POST /flows succeeded. Stored ID: ${result.id}, Node count in response: ${result.flow_data?.nodes?.length}`);
    return result;
  } catch (err) {
    console.error('[API client] POST /flows failed:', err);
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Update an existing flow on the backend.
 * PUT /flows/{flow_id}
 * @param {string} flowId - Unique identifier of the flow to update.
 * @param {Object} payload - { name: string, description?: string, chatbot_id?: string, flow_data: { nodes: Array, edges: Array } }
 * @returns {Promise<Object>} The updated FlowResponse object.
 */
export async function updateFlow(flowId, payload) {
  if (!flowId) throw new Error('Flow ID is required to update a flow.');
  if (!payload) throw new Error('Flow payload is required to update a flow.');
  const nodeCount = payload.flow_data?.nodes?.length || 0;
  const edgeCount = payload.flow_data?.edges?.length || 0;
  console.log(`[API client] PUT /flows/${flowId} - Outgoing payload: flowId=${flowId}, nodes=${nodeCount}, edges=${edgeCount}`);
  try {
    const response = await fetch(`${API_BASE_URL}/flows/${encodeURIComponent(flowId)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
    console.log(`[API client] PUT /flows/${flowId} HTTP status: ${response.status}`);
    const result = await handleResponse(response, `Updating flow ${flowId}`);
    const resNodeCount = result.flow_data?.nodes?.length || 0;
    const resEdgeCount = result.flow_data?.edges?.length || 0;
    console.log(`[API client] PUT /flows/${flowId} succeeded - Status: ${response.status}, Response nodes: ${resNodeCount}, Response edges: ${resEdgeCount}`);
    return result;
  } catch (err) {
    console.error(`[API client] PUT /flows/${flowId} failed:`, err);
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Fetch all node definitions from the backend with optional query filters.
 * GET /node-definitions
 * @param {Object} [filters] - { node_source?: string, category?: string, is_active?: boolean }
 * @returns {Promise<Array<Object>>}
 */
export async function fetchNodeDefinitions(filters = {}) {
  const queryParams = new URLSearchParams();
  if (filters.node_source) queryParams.append('node_source', filters.node_source);
  if (filters.category) queryParams.append('category', filters.category);
  if (filters.is_active !== undefined) queryParams.append('is_active', String(filters.is_active));

  const queryString = queryParams.toString();
  const url = `${API_BASE_URL}/node-definitions${queryString ? `?${queryString}` : ''}`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    const data = await handleResponse(response, 'Fetching node definitions');
    return Array.isArray(data) ? data : [];
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Fetch a single node definition by its ID or node_type.
 * GET /node-definitions/{id}
 * @param {string} id
 */
export async function fetchNodeDefinitionById(id) {
  if (!id) throw new Error('Node definition ID is required.');
  try {
    const response = await fetch(`${API_BASE_URL}/node-definitions/${encodeURIComponent(id)}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return await handleResponse(response, `Fetching node definition ${id}`);
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Create a new custom node definition.
 * POST /node-definitions
 * @param {Object} payload - { name: string, node_type: string, category: string, description?: string, input_schema?: object, output_schema?: object, config_schema?: object }
 */
export async function createNodeDefinition(payload) {
  if (!payload) throw new Error('Node definition payload is required.');
  try {
    const response = await fetch(`${API_BASE_URL}/node-definitions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return await handleResponse(response, 'Creating custom node definition');
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Update an existing custom node definition.
 * PUT /node-definitions/{id}
 * @param {string} id
 * @param {Object} payload
 */
export async function updateNodeDefinition(id, payload) {
  if (!id) throw new Error('Node definition ID is required.');
  if (!payload) throw new Error('Update payload is required.');
  try {
    const response = await fetch(`${API_BASE_URL}/node-definitions/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
    return await handleResponse(response, `Updating node definition ${id}`);
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}

/**
 * Delete or safely deactivate a node definition.
 * DELETE /node-definitions/{id}
 * @param {string} id
 */
export async function deleteNodeDefinition(id) {
  if (!id) throw new Error('Node definition ID is required.');
  try {
    const response = await fetch(`${API_BASE_URL}/node-definitions/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: { Accept: 'application/json' },
    });
    return await handleResponse(response, `Deleting node definition ${id}`);
  } catch (err) {
    if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
      throw new Error(`Could not connect to backend at ${API_BASE_URL}. Ensure the FastAPI server is running.`);
    }
    throw err;
  }
}


