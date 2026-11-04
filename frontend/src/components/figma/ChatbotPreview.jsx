import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';

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
 * ChatbotPreview Component
 * Exact visual reproduction of the NABH QMitra chatbot interface (nabh.corover.ai).
 * Supports both:
 * 1. Initial Landing Page (Welcome to QMitra, Ready to assist you, Get Started button)
 * 2. Conversational Message Flow (fixed header, scrollable bubbles, option cards, fixed chat input)
 */
const ChatbotPreview = ({
  selectedNode,
  nodes = [],
  edges = [],
  onSelectNode,
  onSwitchToProperties,
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

  // Scroll area reference & scroll-to-bottom visibility
  const scrollAreaRef = useRef(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);

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

  // Effective message text
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
      const utterance = new SpeechSynthesisUtterance(displayMessage);
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      setIsPlayingAudio(true);
      window.speechSynthesis.speak(utterance);
    }
  }, [displayMessage, isPlayingAudio, showToast]);

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

          {typeof onSwitchToProperties === 'function' && (
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
          )}
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
              <span className="qmitra-node-id-chip" title={`Current Node: ${currentNode?.id}`}>
                {nodeType.toUpperCase()} • #{currentNode?.id || 'start'}
              </span>

              {history.length > 0 && (
                <span style={{ fontSize: '10.5px', color: '#94A3B8', fontWeight: 500 }}>
                  Step {history.length + 1}
                </span>
              )}
            </div>

            {/* Message Bubble (#EBF3FC rounded bubble) */}
            {displayMessage && (
              <div className="qmitra-message-bubble">
                <div className="qmitra-message-text">{displayMessage}</div>

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
            )}

            {/* RAG Scope Info Card (if present) */}
            {(chapter || program || topic) && (
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
