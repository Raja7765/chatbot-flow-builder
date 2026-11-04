/**
 * exportTools.js
 * Wireframe export tools:
 * - PNG capture via html-to-image
 * - PDF document generation via jspdf
 * - Mermaid flowchart text export (.mmd)
 * - CSV matrix export (from, button, to, status, mapping_status)
 */

import { toPng } from 'html-to-image';
import { jsPDF } from 'jspdf';

/**
 * Trigger browser file download
 */
export function downloadFile(filename, content, mimeType = 'text/plain') {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Generate Mermaid Flowchart representation
 */
export function generateMermaidFlowchart(nodes, edges) {
  const lines = ['flowchart LR'];

  // Clean label for Mermaid syntax
  const sanitize = (str) =>
    String(str || '')
      .replace(/["\n\r\[\]\(\)\{\}]/g, ' ')
      .trim();

  // Add node shapes
  nodes.forEach((node) => {
    const label = sanitize(node.data?.label || node.id);
    const id = node.id.replace(/[^a-zA-Z0-9_]/g, '_');

    if (node.type === 'start') {
      lines.push(`  ${id}(["🟢 ${label}"])`);
    } else if (node.type === 'rag') {
      lines.push(`  ${id}[["🤖 ${label}"]]`);
    } else if (node.type === 'content') {
      lines.push(`  ${id}{{"🖼️ ${label}"}}`);
    } else if (node.type === 'form') {
      lines.push(`  ${id}[/"📝 ${label}"/]`);
    } else {
      lines.push(`  ${id}["${label}"]`);
    }
  });

  // Add connections
  edges.forEach((edge) => {
    const src = edge.source.replace(/[^a-zA-Z0-9_]/g, '_');
    const tgt = edge.target.replace(/[^a-zA-Z0-9_]/g, '_');
    const label = sanitize(edge.label);

    if (edge.isBackEdge) {
      if (label) {
        lines.push(`  ${src} -.->|"${label}"| ${tgt}`);
      } else {
        lines.push(`  ${src} -.-> ${tgt}`);
      }
    } else {
      if (label) {
        lines.push(`  ${src} -->|"${label}"| ${tgt}`);
      } else {
        lines.push(`  ${src} --> ${tgt}`);
      }
    }
  });

  return lines.join('\n');
}

/**
 * Generate CSV export: From_ID, From_Label, Button_Label, To_ID, To_Label, Status, Mapping_Status, Program, Topic
 */
export function generateCSVExport(nodes, edges) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const rows = [
    [
      'From_Node_ID',
      'From_Label',
      'Button_Label',
      'To_Node_ID',
      'To_Label',
      'Status',
      'Mapping_Status',
      'Program',
      'Topic',
      'Note',
    ],
  ];

  edges.forEach((edge) => {
    const srcNode = nodeMap.get(edge.source);
    const tgtNode = nodeMap.get(edge.target);

    rows.push([
      edge.source,
      srcNode?.data?.label || edge.source,
      edge.label || '',
      edge.target,
      tgtNode?.data?.label || edge.target,
      srcNode?.data?.status || 'OK',
      srcNode?.data?.mapping_status || '',
      srcNode?.data?.program || '',
      srcNode?.data?.topic || '',
      srcNode?.data?.note || '',
    ]);
  });

  // Also include terminal nodes with 0 outgoing edges
  nodes.forEach((node) => {
    const hasOutgoing = edges.some((e) => e.source === node.id);
    if (!hasOutgoing) {
      rows.push([
        node.id,
        node.data?.label || node.id,
        '[TERMINAL / NO_BUTTONS]',
        '',
        '',
        node.data?.status || 'OK',
        node.data?.mapping_status || '',
        node.data?.program || '',
        node.data?.topic || '',
        node.data?.note || '',
      ]);
    }
  });

  return rows
    .map((row) =>
      row
        .map((val) => `"${String(val || '').replace(/"/g, '""')}"`)
        .join(',')
    )
    .join('\n');
}

/**
 * Capture canvas as PNG image
 */
export async function exportCanvasAsPNG(element, filename = 'nabh_qmitra_flow.png') {
  if (!element) throw new Error('Canvas element not found for export.');

  const dataUrl = await toPng(element, {
    backgroundColor: '#0B1120',
    quality: 0.95,
    filter: (node) => {
      // Exclude floating controls and modals from capture
      if (node?.classList?.contains('react-flow__controls')) return false;
      if (node?.classList?.contains('react-flow__minimap')) return false;
      return true;
    },
  });

  const a = document.createElement('a');
  a.href = dataUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/**
 * Capture canvas and generate multi-page or fit-to-page PDF
 */
export async function exportCanvasAsPDF(element, filename = 'nabh_qmitra_flow.pdf') {
  if (!element) throw new Error('Canvas element not found for export.');

  const dataUrl = await toPng(element, {
    backgroundColor: '#0B1120',
    quality: 0.95,
  });

  const pdf = new jsPDF({
    orientation: 'landscape',
    unit: 'px',
    format: [element.offsetWidth || 1920, element.offsetHeight || 1080],
  });

  pdf.addImage(dataUrl, 'PNG', 0, 0, element.offsetWidth || 1920, element.offsetHeight || 1080);
  pdf.save(filename);
}
