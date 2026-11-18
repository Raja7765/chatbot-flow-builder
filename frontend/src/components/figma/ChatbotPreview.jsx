import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { fetchNodeAnswer, getMediaUrl } from '../../api/client';

/**
 * QMitra Logo Component
 * High-fidelity vector rendition of the QMitra robot avatar with headphones, visor, and antenna,
 * paired optionally with the bold NABH branding.
 */
export const QMitraHeaderLogo = ({ size = 36, hideWordmark = false }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', lineHeight: 1 }}>
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Antenna */}
        <circle cx="24" cy="5" r="3" fill="#0284C7" />
        <path d="M24 8V13" stroke="#0284C7" strokeWidth="2.5" strokeLinecap="round" />

        {/* Headphone Band */}
        <path
          d="M11 23C11 16 16.5 10.5 24 10.5C31.5 10.5 37 16 37 23"
          stroke="#0369A1"
          strokeWidth="3.2"
          strokeLinecap="round"
        />

        {/* Robot Head Body */}
        <rect x="13.5" y="14" width="21" height="19" rx="8" fill="#0284C7" />

        {/* Face Visor Screen */}
        <rect x="16" y="16.5" width="16" height="12" rx="5" fill="#E0F2FE" />

        {/* Friendly Eyes */}
        <circle cx="20.5" cy="22" r="2" fill="#0284C7" />
        <circle cx="27.5" cy="22" r="2" fill="#0284C7" />

        {/* Smile */}
        <path d="M22 25C23 26 25 26 26 25" stroke="#0284C7" strokeWidth="1.2" strokeLinecap="round" />

        {/* Headphone Left Pad */}
        <rect x="8" y="19" width="5.5" height="11" rx="2.5" fill="#0369A1" />

        {/* Headphone Right Pad */}
        <rect x="34.5" y="19" width="5.5" height="11" rx="2.5" fill="#0369A1" />
      </svg>
      <span
        style={{
          fontSize: size > 48 ? '11px' : '8.5px',
          fontWeight: 800,
          color: '#0369A1',
          marginTop: size > 48 ? '-2px' : '-3px',
          letterSpacing: '-0.2px',
        }}
      >
        QMitra
      </span>
    </div>

    {/* NABH Wordmark */}
    {!hideWordmark && (
      <span
        style={{
          fontSize: '20px',
          fontWeight: 800,
          color: '#0F172A',
          letterSpacing: '-0.5px',
          fontFamily: 'Inter, system-ui, sans-serif',
        }}
      >
        NABH
      </span>
    )}
  </div>
);

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
 * Render formatted text supporting headers (#, ##, ###), bullet lists (*, -, •), and paragraphs.
 */
function RenderFormattedText({ content }) {
  if (!content) return null;
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
      elements.push(
        <h4 key={`h4-${idx}`} className="qmitra-answer-h4">
          {renderInlineMarkdown(trimmed.slice(4))}
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(
        <h3 key={`h3-${idx}`} className="qmitra-answer-h3">
          {renderInlineMarkdown(trimmed.slice(3))}
        </h3>
      );
    } else if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(
        <h2 key={`h2-${idx}`} className="qmitra-answer-h2">
          {renderInlineMarkdown(trimmed.slice(2))}
        </h2>
      );
    } else if (trimmed.startsWith('* ') || trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      const itemText = trimmed.replace(/^(\*|-|•)\s*/, '');
      currentList.push(itemText);
    } else {
      flushList();
      elements.push(
        <p key={`p-${idx}`} className="qmitra-answer-p">
          {renderInlineMarkdown(trimmed)}
        </p>
      );
    }
  });

  flushList();

  return <div className="qmitra-answer-text-block">{elements}</div>;
}

/**
 * Render single answer block based on block_type: text, image, pdf, video.
 */
function AnswerBlockItem({ block }) {
  const meta = block.metadata || {};

  switch (block.block_type) {
    case 'text':
      return <RenderFormattedText content={block.content} />;

    case 'image': {
      const imgUrl = block.media_id ? getMediaUrl(block.media_id) : block.content;
      const caption = meta.caption || meta.description || (block.content && !block.content.startsWith('http') ? block.content : '');
      const altText = meta.title || meta.file_name || 'NABH illustration';
      if (!imgUrl) return null;
      return (
        <div className="qmitra-answer-media-block">
          <img
            src={imgUrl}
            alt={altText}
            className="qmitra-answer-img"
            onClick={() => window.open(imgUrl, '_blank')}
            title="Click to view full image in a new tab"
            loading="lazy"
          />
          {caption && <div className="qmitra-answer-caption">{caption}</div>}
        </div>
      );
    }

    case 'pdf': {
      const pdfUrl = block.media_id ? getMediaUrl(block.media_id) : block.content;
      const title = meta.title || meta.file_name || block.content || 'NABH Standards Document';
      const fileSize = meta.file_size ? `${Math.round(meta.file_size / 1024)} KB` : null;
      const subtitle = [fileSize, 'PDF Document'].filter(Boolean).join(' • ');
      return (
        <div className="qmitra-answer-doc-card">
          <div className="qmitra-doc-icon-wrap" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DC2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          </div>
          <div className="qmitra-doc-info">
            <div className="qmitra-doc-title" title={title}>{title}</div>
            <div className="qmitra-doc-subtitle">{subtitle}</div>
          </div>
          {pdfUrl && (
            <a
              href={pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="qmitra-doc-view-btn"
              title="Open document in a new tab"
            >
              View PDF
            </a>
          )}
        </div>
      );
    }

    case 'video': {
      const videoUrl = block.media_id ? getMediaUrl(block.media_id) : block.content;
      const caption = meta.caption || meta.description || (block.content && !block.content.startsWith('http') ? block.content : '');
      if (!videoUrl) return null;
      return (
        <div className="qmitra-answer-video-wrap">
          <video
            controls
            className="qmitra-answer-video"
            preload="metadata"
            src={videoUrl}
          >
            Your browser does not support HTML5 video streaming.
          </video>
          {caption && <div className="qmitra-answer-caption">{caption}</div>}
        </div>
      );
    }

    default:
      if (block.content) {
        return <div className="qmitra-answer-text-block">{block.content}</div>;
      }
      return null;
  }
}

/**
 * ChatbotPreview Component
 * Exact visual reproduction of the NABH QMitra chatbot interface (nabh.corover.ai).
 * Supports both:
 * 1. Initial Landing Page (Welcome to QMitra, Ready to assist you, Get Started button)
 * 2. Conversational Message Flow (fixed header, scrollable bubbles, option cards, fixed chat input)
 * 3. Dynamic PostgreSQL Node Answer blocks (text, image, pdf, video) with RAG fallback
 */
const ChatbotPreview = ({
  selectedNode,
  nodes = [],
  edges = [],
  flowId,
  onSelectNode,
  onSwitchToProperties,
  onSwitchToContentEditor,
  refreshTrigger,
}) => {
  // Determine root/entry node for initial or fallback view
  const rootNode = useMemo(() => {
    return (
      nodes.find((n) => n.id === 'landing_page' || n.type === 'landing_page') ||
      nodes.find((n) => n.id === 'welcome') ||
      nodes.find((n) => n.type === 'start') ||
      nodes[0] ||
      null
    );
  }, [nodes]);

  // Current active node being displayed in the preview
  const [activeNodeId, setActiveNodeId] = useState(null);

  // Preview navigation history stack: stores array of node IDs
  const [history, setHistory] = useState([]);

  // Audio / Speech Synthesis state
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  // Feedback states
  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);

  // Transient feedback toast
  const [toastMessage, setToastMessage] = useState(null);

  // Simulated user chat messages in preview
  const [chatMessages, setChatMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');

  // Selected option animation highlight
  const [selectedOptionId, setSelectedOptionId] = useState(null);

  // Dynamic PostgreSQL Answer states
  const [nodeAnswer, setNodeAnswer] = useState(null);
  const [isLoadingAnswer, setIsLoadingAnswer] = useState(false);
  const [refreshCounter, setRefreshCounter] = useState(0);
  const [selectedLanguage, setSelectedLanguage] = useState('en');

  // Scroll area reference & scroll-to-bottom visibility
  const scrollAreaRef = useRef(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  // Resolve effective flowId from props or localStorage
  const effectiveFlowId = useMemo(() => {
    if (flowId) return flowId;
    if (typeof window !== 'undefined') {
      return localStorage.getItem('active_flow_id') || null;
    }
    return null;
  }, [flowId]);

  // Sync active node when selectedNode prop changes from canvas
  useEffect(() => {
    if (selectedNode?.id) {
      setActiveNodeId(selectedNode.id);
    } else if (!activeNodeId && rootNode?.id) {
      setActiveNodeId(rootNode.id);
    }
  }, [selectedNode, rootNode, activeNodeId]);

  // Retrieve full object of current active node
  const currentNode = useMemo(() => {
    if (!activeNodeId) return rootNode;
    return nodes.find((n) => n.id === activeNodeId) || rootNode;
  }, [activeNodeId, nodes, rootNode]);

  // Node data normalization
  const nodeData = currentNode?.data || {};
  const nodeType = (currentNode?.type || nodeData.nodeType || 'message').toLowerCase();
  const label = nodeData.label || nodeData.name || currentNode?.id || '';
  const program = nodeData.program || '';
  const topic = nodeData.topic || '';
  const chapter = nodeData.chapter || '';
  const explicitMessage = nodeData.message || nodeData.content || nodeData.text || nodeData.description || '';

  // Check if current page is the initial landing page
  const isLandingPage =
    nodeType === 'landing_page' ||
    nodeType === 'landing' ||
    currentNode?.id === 'landing_page';

  // Effective message text fallback
  let displayMessage = explicitMessage;
  if (!displayMessage) {
    if (program || topic || chapter) {
      const parts = [chapter, program, topic].filter(Boolean);
      displayMessage = parts.join(' — ');
    } else if (Array.isArray(nodeData.fields) && nodeData.fields.length > 0) {
      displayMessage = 'Please fill out the form details below to proceed:';
    } else if (isLandingPage) {
      displayMessage = nodeData.heading || 'Welcome to QMitra';
    } else {
      displayMessage = label || 'Welcome to NABH QMitra.';
    }
  }

  const buttons = Array.isArray(nodeData.buttons) ? nodeData.buttons : [];
  const fields = Array.isArray(nodeData.fields) ? nodeData.fields : [];

  // Reset transient feedback when node changes
  useEffect(() => {
    setLiked(false);
    setDisliked(false);
    setSelectedOptionId(null);
    setToastMessage(null);
  }, [activeNodeId]);

  // Dynamic Answer Fetching from PostgreSQL with stale response prevention
  useEffect(() => {
    let isMounted = true;
    const currentNodeId = currentNode?.id;

    if (!effectiveFlowId || !currentNodeId || isLandingPage) {
      setNodeAnswer(null);
      setIsLoadingAnswer(false);
      return;
    }

    setIsLoadingAnswer(true);

    fetchNodeAnswer(effectiveFlowId, currentNodeId, selectedLanguage)
      .then((data) => {
        if (!isMounted) return;
        setNodeAnswer(data);
        setIsLoadingAnswer(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.warn(`[ChatbotPreview] Error fetching answer for node ${currentNodeId}:`, err);
        setNodeAnswer(null);
        setIsLoadingAnswer(false);
      });

    return () => {
      isMounted = false;
    };
  }, [effectiveFlowId, currentNode?.id, isLandingPage, refreshCounter, refreshTrigger, selectedLanguage]);

  // Check if a saved database answer with blocks exists
  const hasDynamicAnswer = Boolean(
    nodeAnswer && Array.isArray(nodeAnswer.blocks) && nodeAnswer.blocks.length > 0
  );

  // Sorted answer blocks in ascending position order
  const sortedBlocks = useMemo(() => {
    if (!hasDynamicAnswer) return [];
    return [...nodeAnswer.blocks].sort((a, b) => (Number(a.position) || 0) - (Number(b.position) || 0));
  }, [hasDynamicAnswer, nodeAnswer]);

  // Track scroll position to toggle the floating green scroll-to-bottom button
  const handleScroll = useCallback(() => {
    if (!scrollAreaRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollAreaRef.current;
    const isUp = scrollHeight - scrollTop - clientHeight > 60;
    setShowScrollBottom(isUp);
  }, []);

  const scrollToBottom = useCallback(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({
        top: scrollAreaRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, []);

  // Show transient toast
  const showToast = useCallback((msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 2500);
  }, []);

  // Manual refresh trigger
  const handleManualRefresh = useCallback(() => {
    if (!effectiveFlowId || !currentNode?.id) {
      showToast('No active flow or node to refresh.');
      return;
    }
    setIsLoadingAnswer(true);
    setRefreshCounter((c) => c + 1);
    fetchNodeAnswer(effectiveFlowId, currentNode.id, selectedLanguage)
      .then((data) => {
        setNodeAnswer(data);
        setIsLoadingAnswer(false);
        if (data && Array.isArray(data.blocks) && data.blocks.length > 0) {
          showToast(`Answer refreshed from PostgreSQL (${data.blocks.length} blocks).`);
        } else {
          showToast('No database answer found; showing default flow/RAG context.');
        }
      })
      .catch((err) => {
        setIsLoadingAnswer(false);
        showToast(`Refresh failed: ${err.message}`);
      });
  }, [effectiveFlowId, currentNode?.id, selectedLanguage, showToast]);

  // Handle option click with realistic radio button feedback and flow navigation
  const handleOptionClick = useCallback(
    (btn, idx) => {
      const optionKey = btn.id || `${btn.label}_${idx}`;
      setSelectedOptionId(optionKey);

      // Locate destination target node ID
      let targetId = btn.next || btn.target || null;

      if (!targetId && currentNode?.id) {
        // Look up corresponding edge in edges array
        const matchedEdge = edges.find((e) => {
          if (String(e.source) !== String(currentNode.id)) return false;
          if (btn.id && e.sourceHandle === btn.id) return true;
          return true;
        });
        if (matchedEdge?.target) {
          targetId = matchedEdge.target;
        }
      }

      // Check if target node exists in nodes
      const targetNode = targetId ? nodes.find((n) => String(n.id) === String(targetId)) : null;

      if (targetNode) {
        setTimeout(() => {
          setHistory((prev) => [...prev, currentNode.id]);
          setActiveNodeId(targetNode.id);
          if (typeof onSelectNode === 'function') {
            onSelectNode(targetNode.id);
          }
          if (scrollAreaRef.current) {
            scrollAreaRef.current.scrollTop = 0;
          }
        }, 180);
      } else {
        showToast(
          targetId
            ? `Destination node (${targetId}) not found in flow.`
            : `No destination connected for "${btn.label || 'this option'}".`
        );
      }
    },
    [currentNode, edges, nodes, onSelectNode, showToast]
  );

  // Handle back navigation
  const handleBack = useCallback(() => {
    if (history.length === 0) return;
    const previousNodeId = history[history.length - 1];
    setHistory((prev) => prev.slice(0, -1));
    setActiveNodeId(previousNodeId);
    if (typeof onSelectNode === 'function') {
      onSelectNode(previousNodeId);
    }
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = 0;
    }
  }, [history, onSelectNode]);

  // Handle reset to root/landing node
  const handleRestart = useCallback(() => {
    if (rootNode?.id) {
      setHistory([]);
      setActiveNodeId(rootNode.id);
      setChatMessages([]);
      if (typeof onSelectNode === 'function') {
        onSelectNode(rootNode.id);
      }
      if (scrollAreaRef.current) {
        scrollAreaRef.current.scrollTop = 0;
      }
    }
  }, [rootNode, onSelectNode]);

  // Audio speech synthesis text determination
  const answerSpeechText = useMemo(() => {
    if (hasDynamicAnswer) {
      const textParts = sortedBlocks
        .filter((b) => b.block_type === 'text' && b.content)
        .map((b) => b.content.replace(/[#*•-]/g, '').trim())
        .filter(Boolean);
      if (textParts.length > 0) {
        return textParts.join('. ');
      }
    }
    return displayMessage;
  }, [hasDynamicAnswer, sortedBlocks, displayMessage]);

  // Audio speech synthesis toggle
  const handleToggleAudio = useCallback(() => {
    if (!('speechSynthesis' in window)) {
      showToast('Text-to-speech not supported in this browser.');
      return;
    }

    if (isPlayingAudio) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
    } else {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(answerSpeechText);
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      setIsPlayingAudio(true);
      window.speechSynthesis.speak(utterance);
    }
  }, [answerSpeechText, isPlayingAudio, showToast]);

  // Handle simulated user message send in preview
  const handleSendMessage = useCallback(
    (e) => {
      if (e) e.preventDefault();
      const text = inputValue.trim();
      if (!text) return;

      const userMsg = { sender: 'user', text, timestamp: Date.now() };
      setChatMessages((prev) => [...prev, userMsg]);
      setInputValue('');

      // Auto-reply guidance message
      setTimeout(() => {
        setChatMessages((prev) => [
          ...prev,
          {
            sender: 'bot',
            text: 'Preview mode: Click on any menu option card above or select nodes on the canvas to navigate through the NABH QMitra flow.',
            timestamp: Date.now() + 1,
          },
        ]);
        scrollToBottom();
      }, 400);
    },
    [inputValue, scrollToBottom]
  );

  return (
    <div className="qmitra-preview-shell">
      {/* 1. Fixed Header: QMitra & NABH Branding + History Controls */}
      <header className="qmitra-preview-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {history.length > 0 && (
            <button
              type="button"
              className="qmitra-btn-icon"
              onClick={handleBack}
              title="Go back to previous page"
              aria-label="Back"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="19" y1="12" x2="5" y2="12"></line>
                <polyline points="12 19 5 12 12 5"></polyline>
              </svg>
            </button>
          )}

          <QMitraHeaderLogo size={36} />
        </div>

        {/* Right Header Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {/* Refresh Answer Button */}
          {!isLandingPage && (
            <button
              type="button"
              className={`qmitra-btn-icon ${isLoadingAnswer ? 'spin-animation' : ''}`}
              onClick={handleManualRefresh}
              title="Refresh answer from PostgreSQL database"
              aria-label="Refresh answer"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M23 4v6h-6"></path>
                <path d="M1 20v-6h6"></path>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
            </button>
          )}

          <button
            type="button"
            className="qmitra-btn-icon"
            onClick={handleRestart}
            title="Restart from Landing Page"
            aria-label="Restart"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
          </button>

          {typeof onSwitchToContentEditor === 'function' ? (
            <button
              type="button"
              className="qmitra-btn-pill-edit"
              onClick={onSwitchToContentEditor}
              title="Edit answer content in PostgreSQL"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 20h9"></path>
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
              </svg>
              <span>Edit Content</span>
            </button>
          ) : typeof onSwitchToProperties === 'function' ? (
            <button
              type="button"
              className="qmitra-btn-pill-edit"
              onClick={onSwitchToProperties}
              title="Edit node properties"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 20h9"></path>
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
              </svg>
              <span>Edit</span>
            </button>
          ) : null}
        </div>
      </header>

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="qmitra-toast-banner" role="status">
          {toastMessage}
        </div>
      )}

      {/* 2. Main Content View: Landing Page OR Conversational Flow */}
      {isLandingPage ? (
        /* ================= INITIAL WELCOME / LANDING PAGE ================= */
        <div className="qmitra-landing-container">
          {/* Top section: Avatar, Heading & Subtitle */}
          <div className="qmitra-landing-top">
            <div className="qmitra-landing-avatar-wrap">
              <QMitraHeaderLogo size={62} hideWordmark />
            </div>

            <h1 className="qmitra-landing-title">
              {nodeData.heading || 'Welcome to QMitra'}
            </h1>

            <p className="qmitra-landing-subtitle">
              {nodeData.subtitle || 'Your Trusted Healthcare Virtual Assistant'}
            </p>
          </div>

          {/* Center Card with Info Icon, Title, Description, and Get Started Button */}
          <div className="qmitra-landing-card">
            <div className="qmitra-landing-info-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0284C7" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
            </div>

            <h2 className="qmitra-landing-card-heading">
              {nodeData.card_title || 'Ready to assist you!'}
            </h2>

            <p className="qmitra-landing-card-desc">
              {nodeData.card_description || 'I can help you with healthcare information'}
            </p>

            <button
              type="button"
              className="qmitra-get-started-btn"
              onClick={() => {
                const targetBtn = buttons[0] || { label: 'Get Started', next: 'welcome' };
                handleOptionClick(targetBtn, 0);
              }}
            >
              <span>{nodeData.button_label || 'Get Started'}</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </button>
          </div>

          {/* Footer Branding */}
          <div className="qmitra-landing-footer">
            <span>Powered by </span>
            <span style={{ color: '#F97316', fontWeight: 700 }}>CoRover.ai</span>
            <sup style={{ color: '#F97316', fontSize: '8px' }}>®</sup>
            <span style={{ color: '#CBD5E1', margin: '0 5px' }}>|</span>
            <span style={{ color: '#0F172A', fontWeight: 700 }}>BharatGPT</span>
          </div>
        </div>
      ) : (
        /* ================= CONVERSATION FLOW VIEW ================= */
        <>
          <main className="qmitra-conversation-area" ref={scrollAreaRef} onScroll={handleScroll}>
            {/* Node Scope / Meta badge */}
            <div style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span
                className={`qmitra-node-id-chip ${hasDynamicAnswer ? 'db-synced' : ''}`}
                title={`Current Node: ${currentNode?.id}${hasDynamicAnswer ? ' (Live PostgreSQL Answer)' : ''}`}
              >
                {hasDynamicAnswer ? (
                  <>
                    <span
                      style={{
                        display: 'inline-block',
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        backgroundColor: '#059669',
                        marginRight: '6px',
                        verticalAlign: 'middle',
                      }}
                    />
                    DB SYNCED • #{currentNode?.id || 'start'}
                  </>
                ) : (
                  `${nodeType.toUpperCase()} • #${currentNode?.id || 'start'}`
                )}
              </span>

              {history.length > 0 && (
                <span style={{ fontSize: '10.5px', color: '#94A3B8', fontWeight: 500 }}>
                  Step {history.length + 1}
                </span>
              )}
            </div>

            {/* Message Bubble (#EBF3FC rounded bubble) */}
            <div className="qmitra-message-bubble">
              {isLoadingAnswer ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 0', color: '#64748B', fontSize: '12px' }}>
                  <svg className="spin-animation" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                  </svg>
                  <span>Loading answer from database...</span>
                </div>
              ) : hasDynamicAnswer ? (
                /* Dynamic PostgreSQL Answer Blocks */
                <div className="qmitra-answer-blocks-container">
                  {sortedBlocks.map((blk) => (
                    <AnswerBlockItem key={blk.id || `blk-${blk.position}`} block={blk} />
                  ))}
                </div>
              ) : (
                /* Fallback flow_data / RAG context message */
                <div className="qmitra-message-text">{displayMessage}</div>
              )}

              {/* Action Icons Row (Speaker, Thumbs Up, Thumbs Down) */}
              <div className="qmitra-action-icons-row">
                {/* Speaker / Read Aloud */}
                <button
                  type="button"
                  className={`qmitra-msg-action-btn ${isPlayingAudio ? 'active-audio' : ''}`}
                  onClick={handleToggleAudio}
                  title={isPlayingAudio ? 'Stop reading' : 'Read aloud'}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                  </svg>
                </button>

                {/* Thumbs Up */}
                <button
                  type="button"
                  className={`qmitra-msg-action-btn ${liked ? 'active-like' : ''}`}
                  onClick={() => {
                    setLiked(!liked);
                    setDisliked(false);
                  }}
                  title="Helpful"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                  </svg>
                </button>

                {/* Thumbs Down */}
                <button
                  type="button"
                  className={`qmitra-msg-action-btn ${disliked ? 'active-dislike' : ''}`}
                  onClick={() => {
                    setDisliked(!disliked);
                    setLiked(false);
                  }}
                  title="Not helpful"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path>
                  </svg>
                </button>
              </div>
            </div>

            {/* RAG Knowledge Context Card (only shown when no dynamic answer is present) */}
            {!hasDynamicAnswer && (chapter || program || topic) && (
              <div className="qmitra-rag-info-card">
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#0369A1', marginBottom: '4px' }}>
                  RAG Knowledge Context
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {chapter && <span className="qmitra-meta-tag">Chapter: {chapter}</span>}
                  {program && <span className="qmitra-meta-tag">Program: {program}</span>}
                  {topic && <span className="qmitra-meta-tag">Topic: {topic}</span>}
                </div>
              </div>
            )}

            {/* Form Fields Card (if form node) */}
            {fields.length > 0 && (
              <div className="qmitra-form-container">
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#1E293B', marginBottom: '8px' }}>
                  Required Information
                </div>
                {fields.map((f, fIdx) => {
                  const fName = typeof f === 'string' ? f : f.name || f.label || `Field ${fIdx + 1}`;
                  const fLabel = typeof f === 'object' ? f.label || f.name : f;
                  return (
                    <div key={fIdx} style={{ marginBottom: '10px' }}>
                      <label
                        style={{
                          display: 'block',
                          fontSize: '11.5px',
                          fontWeight: 600,
                          color: '#475569',
                          marginBottom: '4px',
                        }}
                      >
                        {fLabel}
                      </label>
                      <input
                        type="text"
                        className="qmitra-form-input"
                        placeholder={`Enter ${fName}...`}
                        disabled
                      />
                    </div>
                  );
                })}
              </div>
            )}

            {/* Menu Container & Stacked Option Cards */}
            {buttons.length > 0 && (
              <div className="qmitra-menu-container">
                {nodeData.prompt && (
                  <div
                    className="qmitra-options-prompt"
                    style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: '#334155',
                      marginBottom: '8px',
                      paddingLeft: '2px',
                    }}
                  >
                    {nodeData.prompt}
                  </div>
                )}
                <div className="qmitra-options-list">
                  {buttons.map((btn, idx) => {
                    const optKey = btn.id || `${btn.label}_${idx}`;
                    const isSelected = selectedOptionId === optKey;

                    return (
                      <button
                        key={optKey}
                        type="button"
                        className={`qmitra-option-card ${isSelected ? 'selected' : ''}`}
                        onClick={() => handleOptionClick(btn, idx)}
                        title={btn.next ? `Go to ${btn.next}` : btn.label}
                      >
                        {/* Radio-style selection circle on left */}
                        <span className={`qmitra-radio-circle ${isSelected ? 'checked' : ''}`}>
                          {isSelected && <span className="qmitra-radio-dot" />}
                        </span>

                        {/* Blue option label */}
                        <span className="qmitra-option-label">{btn.label || `Option ${idx + 1}`}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Navigation Actions Row (Previous Menu & Back to Main Menu) */}
            {history.length > 0 && (
              <div className="qmitra-nav-actions-container">
                <button
                  type="button"
                  className="qmitra-nav-btn"
                  onClick={handleBack}
                  title="Return to previous menu"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"></line>
                    <polyline points="12 19 5 12 12 5"></polyline>
                  </svg>
                  <span>Previous Menu</span>
                </button>

                <button
                  type="button"
                  className="qmitra-nav-btn primary"
                  onClick={handleRestart}
                  title="Return to main welcome menu"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                    <polyline points="9 22 9 12 15 12 15 22"></polyline>
                  </svg>
                  <span>Back to Main Menu</span>
                </button>
              </div>
            )}

            {/* Additional simulated conversation messages */}
            {chatMessages.length > 0 && (
              <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    style={{
                      alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '85%',
                      background: msg.sender === 'user' ? '#0D74CE' : '#EBF3FC',
                      color: msg.sender === 'user' ? '#FFFFFF' : '#1E293B',
                      borderRadius: msg.sender === 'user' ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                      padding: '9px 13px',
                      fontSize: '12.5px',
                      lineHeight: '1.45',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                    }}
                  >
                    {msg.text}
                  </div>
                ))}
              </div>
            )}

            {/* Floating Green Scroll-to-Bottom Button */}
            {showScrollBottom && (
              <button
                type="button"
                className="qmitra-scroll-down-btn"
                onClick={scrollToBottom}
                title="Scroll to bottom"
                aria-label="Scroll to bottom"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <polyline points="19 12 12 19 5 12"></polyline>
                </svg>
              </button>
            )}
          </main>

          {/* 3. Fixed Bottom Area: Chat Input & CoRover / BharatGPT Footer */}
          <footer className="qmitra-fixed-bottom">
            {/* Input Row */}
            <form className="qmitra-input-row" onSubmit={handleSendMessage}>
              {/* Three Dots Icon */}
              <button
                type="button"
                className="qmitra-more-options-btn"
                title="More options"
                onClick={() => showToast('Preview mode: Use canvas or menu options to navigate.')}
              >
                ···
              </button>

              {/* Pill Input Container */}
              <div className="qmitra-pill-input">
                <input
                  type="text"
                  className="qmitra-text-input"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="May I help you?"
                />

                {/* Microphone Icon */}
                <button
                  type="button"
                  className="qmitra-input-icon-btn"
                  title="Voice Input"
                  onClick={() => showToast('Voice input is simulated in preview mode.')}
                >
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#0D74CE" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"></path>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                    <line x1="12" y1="19" x2="12" y2="22"></line>
                  </svg>
                </button>

                {/* Send Paperplane Icon */}
                <button
                  type="submit"
                  className="qmitra-input-icon-btn"
                  title="Send Message"
                >
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#0D74CE" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                  </svg>
                </button>
              </div>
            </form>

            {/* Footer Branding */}
            <div className="qmitra-branding-footer">
              <span>Powered by </span>
              <span style={{ color: '#F97316', fontWeight: 700 }}>CoRover.ai</span>
              <sup style={{ color: '#F97316', fontSize: '8px' }}>®</sup>
              <span style={{ color: '#CBD5E1', margin: '0 5px' }}>|</span>
              <span style={{ color: '#0F172A', fontWeight: 700 }}>BharatGPT</span>
            </div>
          </footer>
        </>
      )}
    </div>
  );
};

export default React.memo(ChatbotPreview);
