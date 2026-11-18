import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  fetchNodeAnswer,
  saveNodeAnswer,
  deleteNodeAnswer,
  uploadMediaFile,
  getMediaUrl,
} from '../../api/client';

/**
 * Helper to render inline markdown like bold (**text**)
 */
function renderInlineMarkdown(text) {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

/**
 * Mini-preview for text blocks with headings (#, ##, ###) and bullets (*, -, •)
 */
function FormattedTextPreview({ content }) {
  if (!content) {
    return <span style={{ color: '#94A3B8', fontStyle: 'italic', fontSize: '11px' }}>Empty block preview</span>;
  }
  const lines = content.split('\n');
  const elements = [];
  let currentList = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="qmitra-answer-bullet-list">
          {currentList.map((item, idx) => (
            <li key={idx}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(<h4 key={`h4-${idx}`} className="qmitra-answer-h4">{renderInlineMarkdown(trimmed.slice(4))}</h4>);
    } else if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(<h3 key={`h3-${idx}`} className="qmitra-answer-h3">{renderInlineMarkdown(trimmed.slice(3))}</h3>);
    } else if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(<h2 key={`h2-${idx}`} className="qmitra-answer-h2">{renderInlineMarkdown(trimmed.slice(2))}</h2>);
    } else if (trimmed.startsWith('* ') || trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      currentList.push(trimmed.replace(/^(\*|-|•)\s*/, ''));
    } else {
      flushList();
      elements.push(<p key={`p-${idx}`} className="qmitra-answer-p">{renderInlineMarkdown(trimmed)}</p>);
    }
  });

  flushList();

  return <div className="qmitra-answer-text-block" style={{ padding: '8px 10px', background: '#F8FAFC', borderRadius: '6px', border: '1px solid #E2E8F0', marginTop: '6px' }}>{elements}</div>;
}

/**
 * AdminContentEditor Component
 * Allows admins to edit chatbot node answers directly from the frontend and persist
 * multi-block answers (text, image, pdf, video) to PostgreSQL via existing backend APIs.
 */
const AdminContentEditor = ({
  node,
  flowId,
  onClose,
  onAnswerSaved,
  isModal = false,
  onToggleModal,
}) => {
  const nodeId = node?.id;
  const nodeData = node?.data || {};
  const nodeLabel = nodeData.label || nodeData.name || nodeId || 'Node';

  const [language, setLanguage] = useState('en');
  const [blocks, setBlocks] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSavedInDb, setIsSavedInDb] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Per-block file upload state { [blockIndex]: boolean }
  const [uploadingState, setUploadingState] = useState({});

  // Preview toggles for text blocks { [blockIndex]: boolean }
  const [previewToggles, setPreviewToggles] = useState({});

  // File input refs map
  const fileInputRefs = useRef({});

  // Resolve effective flowId
  const effectiveFlowId = useMemo(() => {
    if (flowId) return flowId;
    if (typeof window !== 'undefined') {
      return localStorage.getItem('active_flow_id') || null;
    }
    return null;
  }, [flowId]);

  // Load existing answer for selected node and language
  const loadAnswer = useCallback(async () => {
    if (!effectiveFlowId || !nodeId) return;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const data = await fetchNodeAnswer(effectiveFlowId, nodeId, language);
      if (data && Array.isArray(data.blocks) && data.blocks.length > 0) {
        const sorted = [...data.blocks].sort(
          (a, b) => (Number(a.position) || 0) - (Number(b.position) || 0)
        );
        setBlocks(sorted);
        setIsSavedInDb(true);
      } else {
        // No saved answer in DB (404 fallback); initialize with default draft block
        setIsSavedInDb(false);
        const defaultText = nodeData.message || nodeData.content || nodeData.text || nodeData.description || nodeData.label || '';
        setBlocks([
          {
            id: `init_${Date.now()}`,
            block_type: 'text',
            content: defaultText,
            media_id: null,
            position: 1,
            metadata: {},
          },
        ]);
      }
    } catch (err) {
      console.warn(`[AdminContentEditor] Error loading answer:`, err);
      setErrorMessage(`Failed to load answer: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [effectiveFlowId, nodeId, language, nodeData]);

  useEffect(() => {
    loadAnswer();
  }, [loadAnswer]);

  // Auto-dismiss transient messages
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 3500);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Add new block to the answer
  const handleAddBlock = (type) => {
    const nextPos = blocks.length + 1;
    let initialMetadata = {};
    if (type === 'image') initialMetadata = { title: 'Image illustration', caption: '' };
    if (type === 'pdf') initialMetadata = { title: 'Standards Document' };
    if (type === 'video') initialMetadata = { caption: 'Video guide' };

    const newBlock = {
      id: `draft_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      block_type: type,
      content: type === 'text' ? '' : '',
      media_id: null,
      position: nextPos,
      metadata: initialMetadata,
    };
    setBlocks((prev) => [...prev, newBlock]);
  };

  // Delete a block and re-index positions
  const handleDeleteBlock = (idx) => {
    setBlocks((prev) => {
      const updated = prev.filter((_, i) => i !== idx);
      return updated.map((b, i) => ({ ...b, position: i + 1 }));
    });
  };

  // Reorder: Move Up
  const handleMoveUp = (idx) => {
    if (idx === 0) return;
    setBlocks((prev) => {
      const copy = [...prev];
      const temp = copy[idx - 1];
      copy[idx - 1] = copy[idx];
      copy[idx] = temp;
      return copy.map((b, i) => ({ ...b, position: i + 1 }));
    });
  };

  // Reorder: Move Down
  const handleMoveDown = (idx) => {
    if (idx >= blocks.length - 1) return;
    setBlocks((prev) => {
      const copy = [...prev];
      const temp = copy[idx + 1];
      copy[idx + 1] = copy[idx];
      copy[idx] = temp;
      return copy.map((b, i) => ({ ...b, position: i + 1 }));
    });
  };

  // Update block properties
  const handleBlockChange = (idx, field, value) => {
    setBlocks((prev) => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], [field]: value };
      return copy;
    });
  };

  // Update block metadata
  const handleMetadataChange = (idx, metaKey, metaVal) => {
    setBlocks((prev) => {
      const copy = [...prev];
      const existingMeta = copy[idx].metadata || {};
      copy[idx] = {
        ...copy[idx],
        metadata: {
          ...existingMeta,
          [metaKey]: metaVal,
        },
      };
      return copy;
    });
  };

  // Insert markdown snippet into text block
  const handleInsertSnippet = (idx, snippet) => {
    setBlocks((prev) => {
      const copy = [...prev];
      const curContent = copy[idx].content || '';
      copy[idx] = {
        ...copy[idx],
        content: curContent ? `${curContent}\n${snippet}` : snippet,
      };
      return copy;
    });
  };

  // Media File Upload handler
  const handleFileUpload = async (idx, file, blockType) => {
    if (!file) return;

    setUploadingState((prev) => ({ ...prev, [idx]: true }));
    setErrorMessage(null);

    try {
      const result = await uploadMediaFile(file, `Uploaded from Content Editor for ${nodeId}`, blockType);
      
      setBlocks((prev) => {
        const copy = [...prev];
        const existingMeta = copy[idx].metadata || {};
        copy[idx] = {
          ...copy[idx],
          media_id: result.id,
          content: copy[idx].content || result.file_name,
          metadata: {
            ...existingMeta,
            file_name: result.file_name,
            file_size: result.file_size,
            mime_type: result.mime_type,
            title: existingMeta.title || result.file_name,
          },
        };
        return copy;
      });

      setSuccessMessage(`Uploaded "${result.file_name}" (${Math.round(result.file_size / 1024)} KB) successfully!`);
    } catch (err) {
      console.error(`[AdminContentEditor] Upload failed:`, err);
      setErrorMessage(`Media upload failed: ${err.message}`);
    } finally {
      setUploadingState((prev) => ({ ...prev, [idx]: false }));
    }
  };

  // Save changes to PostgreSQL
  const handleSave = async () => {
    if (isSaving) return;

    if (!effectiveFlowId || !nodeId) {
      setErrorMessage('Missing Flow ID or Node ID.');
      return;
    }

    if (blocks.length === 0) {
      setErrorMessage('At least one answer block is required.');
      return;
    }

    // Validate text blocks
    const emptyText = blocks.some(
      (b) => b.block_type === 'text' && (!b.content || !b.content.trim())
    );
    if (emptyText) {
      setErrorMessage('All text blocks must contain non-empty content.');
      return;
    }

    // Validate media blocks
    const invalidMedia = blocks.some(
      (b) => ['image', 'pdf', 'video'].includes(b.block_type) && !b.media_id && !b.content
    );
    if (invalidMedia) {
      setErrorMessage('Please upload a media file or provide a valid Media ID for all media blocks.');
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);

    // Build payload ensuring sequential 1-based positions
    const payloadBlocks = blocks.map((b, idx) => ({
      block_type: b.block_type,
      content: b.content ? b.content.trim() : null,
      media_id: b.media_id || null,
      position: idx + 1,
      metadata: b.metadata && Object.keys(b.metadata).length > 0 ? b.metadata : null,
    }));

    const payload = {
      language,
      blocks: payloadBlocks,
    };

    try {
      const saved = await saveNodeAnswer(effectiveFlowId, nodeId, payload, true);
      setIsSavedInDb(true);
      if (saved && Array.isArray(saved.blocks)) {
        setBlocks(saved.blocks.sort((a, b) => a.position - b.position));
      }
      setSuccessMessage(`Saved ${payloadBlocks.length} blocks to PostgreSQL successfully!`);

      // Notify parent to refresh Chatbot Preview
      if (typeof onAnswerSaved === 'function') {
        onAnswerSaved(saved);
      }
    } catch (err) {
      console.error('[AdminContentEditor] Save failed:', err);
      setErrorMessage(`Save failed: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Delete answer from DB (reverts node to RAG fallback)
  const handleDeleteAnswer = async () => {
    if (!isSavedInDb || !effectiveFlowId || !nodeId) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete this answer from PostgreSQL?\n\nNode "${nodeId}" will revert to the default flow / RAG fallback context.`
    );
    if (!confirmed) return;

    setIsSaving(true);
    setErrorMessage(null);

    try {
      await deleteNodeAnswer(effectiveFlowId, nodeId, language);
      setIsSavedInDb(false);
      setSuccessMessage('Answer deleted from PostgreSQL. Node reverted to default RAG fallback.');
      
      // Initialize with single fallback block
      const defaultText = nodeData.message || nodeData.content || nodeData.text || '';
      setBlocks([
        {
          id: `draft_${Date.now()}`,
          block_type: 'text',
          content: defaultText,
          media_id: null,
          position: 1,
          metadata: {},
        },
      ]);

      if (typeof onAnswerSaved === 'function') {
        onAnswerSaved(null);
      }
    } catch (err) {
      setErrorMessage(`Delete failed: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className={`admin-content-editor ${isModal ? 'as-modal' : 'as-panel'}`}>
      {/* Editor Header */}
      <div className="editor-top-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
          <span className="editor-icon" aria-hidden="true">📝</span>
          <div style={{ minWidth: 0 }}>
            <div className="editor-node-title" title={nodeLabel}>
              {nodeLabel}
            </div>
            <div className="editor-node-id-sub">
              <code>#{nodeId}</code>
            </div>
          </div>
        </div>

        {/* Header Right Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {/* Status Badge */}
          <span
            className={`editor-status-badge ${isSavedInDb ? 'saved' : 'draft'}`}
            title={isSavedInDb ? 'Answer is stored in PostgreSQL' : 'Answer is currently a draft (using RAG fallback)'}
          >
            {isSavedInDb ? '● DB Synced' : '○ Draft'}
          </span>

          {/* Modal Expand / Collapse Toggle */}
          {typeof onToggleModal === 'function' && (
            <button
              type="button"
              className="editor-btn-icon"
              onClick={onToggleModal}
              title={isModal ? 'Collapse to side panel' : 'Expand to full dialog'}
              aria-label="Toggle modal expansion"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                {isModal ? (
                  <>
                    <polyline points="4 14 10 14 10 20"></polyline>
                    <polyline points="20 10 14 10 14 4"></polyline>
                    <line x1="14" y1="10" x2="21" y2="3"></line>
                    <line x1="3" y1="21" x2="10" y2="14"></line>
                  </>
                ) : (
                  <>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <polyline points="9 21 3 21 3 15"></polyline>
                    <line x1="21" y1="3" x2="14" y2="10"></line>
                    <line x1="3" y1="21" x2="10" y2="14"></line>
                  </>
                )}
              </svg>
            </button>
          )}

          {/* Close button */}
          {typeof onClose === 'function' && (
            <button
              type="button"
              className="editor-btn-icon"
              onClick={onClose}
              title="Close Content Editor"
              aria-label="Close"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Language Selector & Quick Bar */}
      <div className="editor-subbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <label htmlFor="editor-lang-select" style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>
            Language:
          </label>
          <select
            id="editor-lang-select"
            className="editor-select-sm"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="en">English (en)</option>
            <option value="hi">Hindi (hi)</option>
            <option value="es">Spanish (es)</option>
            <option value="fr">French (fr)</option>
            <option value="de">German (de)</option>
          </select>
        </div>

        <span style={{ fontSize: '11px', color: '#94A3B8' }}>
          {blocks.length} {blocks.length === 1 ? 'Block' : 'Blocks'}
        </span>
      </div>

      {/* Alert Banners */}
      {errorMessage && (
        <div className="editor-alert error">
          <span>{errorMessage}</span>
          <button type="button" onClick={() => setErrorMessage(null)} className="alert-close">✕</button>
        </div>
      )}
      {successMessage && (
        <div className="editor-alert success">
          <span>{successMessage}</span>
          <button type="button" onClick={() => setSuccessMessage(null)} className="alert-close">✕</button>
        </div>
      )}

      {/* Scrollable Block List Area */}
      <div className="editor-blocks-scroll">
        {isLoading ? (
          <div className="editor-loading-state">
            <svg className="spin-animation" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0284C7" strokeWidth="2.5">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
            </svg>
            <span>Loading answer from PostgreSQL...</span>
          </div>
        ) : blocks.length === 0 ? (
          <div className="editor-empty-state">
            <p>No content blocks defined for this node yet.</p>
            <p style={{ fontSize: '11px', color: '#94A3B8', marginTop: '4px' }}>
              Add a text, image, PDF, or video block to start building your answer:
            </p>
          </div>
        ) : (
          blocks.map((block, idx) => {
            const isFirst = idx === 0;
            const isLast = idx === blocks.length - 1;
            const isUploading = Boolean(uploadingState[idx]);
            const isPreviewOpen = Boolean(previewToggles[idx]);
            const blockMeta = block.metadata || {};

            return (
              <div key={block.id || idx} className="editor-block-card">
                {/* Block Header */}
                <div className="block-card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="block-position-badge">#{idx + 1}</span>
                    <span className={`block-type-tag ${block.block_type}`}>
                      {block.block_type.toUpperCase()}
                    </span>
                  </div>

                  {/* Actions: Move Up, Move Down, Delete */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <button
                      type="button"
                      className="block-action-btn"
                      disabled={isFirst}
                      onClick={() => handleMoveUp(idx)}
                      title="Move up"
                      aria-label="Move block up"
                    >
                      ▲
                    </button>
                    <button
                      type="button"
                      className="block-action-btn"
                      disabled={isLast}
                      onClick={() => handleMoveDown(idx)}
                      title="Move down"
                      aria-label="Move block down"
                    >
                      ▼
                    </button>
                    <button
                      type="button"
                      className="block-action-btn delete"
                      onClick={() => handleDeleteBlock(idx)}
                      title="Delete block"
                      aria-label="Delete block"
                    >
                      🗑
                    </button>
                  </div>
                </div>

                {/* Block Body: Type-Specific Inputs */}
                <div className="block-card-body">
                  {/* ================= 1. TEXT BLOCK ================= */}
                  {block.block_type === 'text' && (
                    <div className="block-input-group">
                      <div className="text-helpers-row">
                        <span style={{ fontSize: '10.5px', fontWeight: 600, color: '#64748B' }}>Insert:</span>
                        <button
                          type="button"
                          className="snippet-btn"
                          onClick={() => handleInsertSnippet(idx, '# Heading')}
                        >
                          # H1
                        </button>
                        <button
                          type="button"
                          className="snippet-btn"
                          onClick={() => handleInsertSnippet(idx, '## Subheading')}
                        >
                          ## H2
                        </button>
                        <button
                          type="button"
                          className="snippet-btn"
                          onClick={() => handleInsertSnippet(idx, '### Section')}
                        >
                          ### H3
                        </button>
                        <button
                          type="button"
                          className="snippet-btn"
                          onClick={() => handleInsertSnippet(idx, '* Bullet item\n* Bullet item 2')}
                        >
                          • Bullets
                        </button>
                        <button
                          type="button"
                          className="snippet-btn"
                          onClick={() => handleInsertSnippet(idx, '**Important bold text**')}
                        >
                          **Bold**
                        </button>

                        <button
                          type="button"
                          className={`snippet-btn ${isPreviewOpen ? 'active' : ''}`}
                          style={{ marginLeft: 'auto' }}
                          onClick={() =>
                            setPreviewToggles((prev) => ({ ...prev, [idx]: !prev[idx] }))
                          }
                          title="Toggle live markdown preview"
                        >
                          {isPreviewOpen ? 'Hide Preview' : 'Preview'}
                        </button>
                      </div>

                      <textarea
                        className="editor-textarea"
                        rows={isModal ? 4 : 3}
                        value={block.content || ''}
                        onChange={(e) => handleBlockChange(idx, 'content', e.target.value)}
                        placeholder="Write your text content here (supports markdown # headings, * bullets, **bold**)..."
                      />

                      {/* Live Markdown Preview */}
                      {isPreviewOpen && (
                        <FormattedTextPreview content={block.content} />
                      )}
                    </div>
                  )}

                  {/* ================= 2. IMAGE BLOCK ================= */}
                  {block.block_type === 'image' && (
                    <div className="block-input-group">
                      {/* Media preview if media_id is set */}
                      {block.media_id ? (
                        <div className="media-preview-container">
                          <img
                            src={getMediaUrl(block.media_id)}
                            alt={blockMeta.title || 'Uploaded image'}
                            className="editor-img-thumb"
                            onClick={() => window.open(getMediaUrl(block.media_id), '_blank')}
                            title="Click to view full image in a new tab"
                          />
                          <div className="media-preview-meta">
                            <div className="media-meta-title">{blockMeta.file_name || 'Image File'}</div>
                            <div className="media-meta-sub">
                              UUID: <code>{block.media_id}</code>
                            </div>
                            <button
                              type="button"
                              className="btn-replace-media"
                              onClick={() => fileInputRefs.current[`img_${idx}`]?.click()}
                            >
                              Replace Image
                            </button>
                          </div>
                        </div>
                      ) : (
                        /* Upload dropzone */
                        <div
                          className="media-upload-dropzone"
                          onClick={() => fileInputRefs.current[`img_${idx}`]?.click()}
                        >
                          {isUploading ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <svg className="spin-animation" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0284C7" strokeWidth="2.5">
                                <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                              </svg>
                              <span>Uploading image to server...</span>
                            </div>
                          ) : (
                            <>
                              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0284C7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                                <polyline points="21 15 16 10 5 21"></polyline>
                              </svg>
                              <span>Click to upload Image (.png, .jpg, .webp, .svg)</span>
                            </>
                          )}
                        </div>
                      )}

                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp,image/svg+xml"
                        style={{ display: 'none' }}
                        ref={(el) => (fileInputRefs.current[`img_${idx}`] = el)}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleFileUpload(idx, file, 'image');
                        }}
                      />

                      {/* Image Caption & Title inputs */}
                      <div className="meta-inputs-grid">
                        <div>
                          <label className="editor-input-label">Image Title / Alt Text</label>
                          <input
                            type="text"
                            className="editor-input-sm"
                            placeholder="e.g. NABH Accreditation Framework"
                            value={blockMeta.title || ''}
                            onChange={(e) => handleMetadataChange(idx, 'title', e.target.value)}
                          />
                        </div>
                        <div>
                          <label className="editor-input-label">Caption / Description</label>
                          <input
                            type="text"
                            className="editor-input-sm"
                            placeholder="e.g. Figure 1: Key quality assessment milestones"
                            value={block.content || blockMeta.caption || ''}
                            onChange={(e) => {
                              handleBlockChange(idx, 'content', e.target.value);
                              handleMetadataChange(idx, 'caption', e.target.value);
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ================= 3. PDF BLOCK ================= */}
                  {block.block_type === 'pdf' && (
                    <div className="block-input-group">
                      {block.media_id ? (
                        <div className="media-preview-container">
                          <div className="pdf-doc-icon-wrap" aria-hidden="true">
                            📄
                          </div>
                          <div className="media-preview-meta">
                            <div className="media-meta-title">
                              {blockMeta.title || blockMeta.file_name || 'PDF Document'}
                            </div>
                            <div className="media-meta-sub">
                              {blockMeta.file_size ? `${Math.round(blockMeta.file_size / 1024)} KB • ` : ''}
                              UUID: <code>{block.media_id}</code>
                            </div>
                            <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                              <a
                                href={getMediaUrl(block.media_id)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn-preview-link"
                              >
                                View PDF
                              </a>
                              <button
                                type="button"
                                className="btn-replace-media"
                                onClick={() => fileInputRefs.current[`pdf_${idx}`]?.click()}
                              >
                                Replace PDF
                              </button>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div
                          className="media-upload-dropzone"
                          onClick={() => fileInputRefs.current[`pdf_${idx}`]?.click()}
                        >
                          {isUploading ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <svg className="spin-animation" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#DC2626" strokeWidth="2.5">
                                <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                              </svg>
                              <span>Uploading PDF document...</span>
                            </div>
                          ) : (
                            <>
                              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#DC2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                              </svg>
                              <span>Click to upload PDF Document (.pdf)</span>
                            </>
                          )}
                        </div>
                      )}

                      <input
                        type="file"
                        accept="application/pdf"
                        style={{ display: 'none' }}
                        ref={(el) => (fileInputRefs.current[`pdf_${idx}`] = el)}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleFileUpload(idx, file, 'document');
                        }}
                      />

                      <div className="meta-inputs-grid">
                        <div style={{ gridColumn: 'span 2' }}>
                          <label className="editor-input-label">Document Display Title</label>
                          <input
                            type="text"
                            className="editor-input-sm"
                            placeholder="e.g. NABH Accreditation Standards 5th Edition"
                            value={blockMeta.title || block.content || ''}
                            onChange={(e) => {
                              handleBlockChange(idx, 'content', e.target.value);
                              handleMetadataChange(idx, 'title', e.target.value);
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ================= 4. VIDEO BLOCK ================= */}
                  {block.block_type === 'video' && (
                    <div className="block-input-group">
                      {block.media_id ? (
                        <div className="media-preview-container">
                          <video
                            controls
                            className="editor-video-thumb"
                            preload="metadata"
                            src={getMediaUrl(block.media_id)}
                          />
                          <div className="media-preview-meta">
                            <div className="media-meta-title">{blockMeta.file_name || 'Video Asset'}</div>
                            <div className="media-meta-sub">
                              UUID: <code>{block.media_id}</code>
                            </div>
                            <button
                              type="button"
                              className="btn-replace-media"
                              onClick={() => fileInputRefs.current[`vid_${idx}`]?.click()}
                            >
                              Replace Video
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div
                          className="media-upload-dropzone"
                          onClick={() => fileInputRefs.current[`vid_${idx}`]?.click()}
                        >
                          {isUploading ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <svg className="spin-animation" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#7C3AED" strokeWidth="2.5">
                                <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                              </svg>
                              <span>Uploading video asset...</span>
                            </div>
                          ) : (
                            <>
                              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7C3AED" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polygon points="23 7 16 12 23 17 23 7"></polygon>
                                <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
                              </svg>
                              <span>Click to upload Video (.mp4, .webm)</span>
                            </>
                          )}
                        </div>
                      )}

                      <input
                        type="file"
                        accept="video/mp4,video/webm"
                        style={{ display: 'none' }}
                        ref={(el) => (fileInputRefs.current[`vid_${idx}`] = el)}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleFileUpload(idx, file, 'video');
                        }}
                      />

                      <div className="meta-inputs-grid">
                        <div style={{ gridColumn: 'span 2' }}>
                          <label className="editor-input-label">Video Caption / Description</label>
                          <input
                            type="text"
                            className="editor-input-sm"
                            placeholder="e.g. Video Guide: Patient Safety and Healthcare Excellence Standards"
                            value={block.content || blockMeta.caption || ''}
                            onChange={(e) => {
                              handleBlockChange(idx, 'content', e.target.value);
                              handleMetadataChange(idx, 'caption', e.target.value);
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Add Block Action Bar */}
        <div className="editor-add-block-row">
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#64748B' }}>Add Block:</span>
          <button
            type="button"
            className="btn-add-block text-type"
            onClick={() => handleAddBlock('text')}
          >
            + Text
          </button>
          <button
            type="button"
            className="btn-add-block image-type"
            onClick={() => handleAddBlock('image')}
          >
            + Image
          </button>
          <button
            type="button"
            className="btn-add-block pdf-type"
            onClick={() => handleAddBlock('pdf')}
          >
            + PDF
          </button>
          <button
            type="button"
            className="btn-add-block video-type"
            onClick={() => handleAddBlock('video')}
          >
            + Video
          </button>
        </div>
      </div>

      {/* Editor Fixed Bottom Action Bar */}
      <div className="editor-bottom-bar">
        {/* Delete from DB if already persisted */}
        {isSavedInDb && (
          <button
            type="button"
            className="btn-editor-danger"
            onClick={handleDeleteAnswer}
            disabled={isSaving}
            title="Delete from PostgreSQL and revert to RAG fallback"
          >
            Revert to RAG
          </button>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: 'auto' }}>
          {typeof onClose === 'function' && (
            <button
              type="button"
              className="btn-editor-secondary"
              onClick={onClose}
              disabled={isSaving}
            >
              Cancel
            </button>
          )}

          <button
            type="button"
            className="btn-editor-primary"
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <svg className="spin-animation" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                </svg>
                <span>Saving to PostgreSQL...</span>
              </>
            ) : (
              <>
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default React.memo(AdminContentEditor);

