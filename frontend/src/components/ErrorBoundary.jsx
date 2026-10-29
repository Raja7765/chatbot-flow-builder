import React from 'react';

/**
 * Top-level React ErrorBoundary
 * Catches any JavaScript errors anywhere in their child component tree,
 * logs those errors, and displays a clean, user-friendly fallback UI
 * with the exact error message and stack trace instead of a blank white screen.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary caught error]:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleClearCacheAndReload = () => {
    try {
      localStorage.removeItem('active_flow_id');
      localStorage.removeItem('active_chatbot_id');
    } catch {}
    window.location.reload();
  };

  handleResetState = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100vw',
            height: '100vh',
            background: '#F5F5F5',
            color: '#1E1E1E',
            fontFamily: "'Inter', sans-serif",
            padding: '24px',
            boxSizing: 'border-box',
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '680px',
              background: '#FFFFFF',
              border: '1px solid #E5E5E5',
              borderRadius: '8px',
              padding: '28px',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span
                style={{
                  background: '#FEE2E2',
                  color: '#DC2626',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                Application Error
              </span>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, color: '#1E1E1E' }}>
                Something went wrong rendering the canvas
              </h2>
            </div>

            <p style={{ fontSize: '0.875rem', color: '#6B6B6B', margin: 0, lineHeight: 1.45 }}>
              The application encountered an unexpected runtime error. You can inspect the error details below
              or clear the cached flow data to restore the default canvas.
            </p>

            <div
              style={{
                background: '#F8F9FA',
                border: '1px solid #E5E5E5',
                borderRadius: '6px',
                padding: '12px 14px',
                fontFamily: 'monospace',
                fontSize: '0.8125rem',
                color: '#DC2626',
                wordBreak: 'break-word',
                maxHeight: '160px',
                overflowY: 'auto',
              }}
            >
              {this.state.error?.toString() || 'Unknown runtime error'}
            </div>

            {this.state.errorInfo?.componentStack && (
              <details style={{ fontSize: '0.75rem', color: '#6B6B6B' }}>
                <summary style={{ cursor: 'pointer', fontWeight: 500, marginBottom: '6px' }}>
                  Component Stack Trace
                </summary>
                <pre
                  style={{
                    background: '#F8F9FA',
                    border: '1px solid #E5E5E5',
                    borderRadius: '6px',
                    padding: '10px',
                    overflowX: 'auto',
                    fontSize: '0.72rem',
                    color: '#4B5563',
                    lineHeight: 1.4,
                  }}
                >
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
              <button
                type="button"
                onClick={this.handleClearCacheAndReload}
                style={{
                  background: '#0D99FF',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px 16px',
                  fontSize: '0.8125rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                Clear Cached Flow &amp; Reload
              </button>

              <button
                type="button"
                onClick={this.handleResetState}
                style={{
                  background: '#FFFFFF',
                  color: '#1E1E1E',
                  border: '1px solid #E5E5E5',
                  borderRadius: '6px',
                  padding: '8px 16px',
                  fontSize: '0.8125rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
