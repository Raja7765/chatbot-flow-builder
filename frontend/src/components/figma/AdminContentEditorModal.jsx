import React from 'react';
import AdminContentEditor from './AdminContentEditor';

/**
 * AdminContentEditorModal Component
 * Full-screen / expansive modal dialog for comfortable multi-block rich answer editing.
 */
const AdminContentEditorModal = ({
  isOpen,
  node,
  flowId,
  onClose,
  onAnswerSaved,
}) => {
  if (!isOpen || !node) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-container editor-modal-container"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: '860px',
          width: '94%',
          height: '88vh',
          display: 'flex',
          flexDirection: 'column',
          padding: 0,
          overflow: 'hidden',
          borderRadius: '12px',
        }}
      >
        <AdminContentEditor
          node={node}
          flowId={flowId}
          onClose={onClose}
          onAnswerSaved={onAnswerSaved}
          isModal={true}
        />
      </div>
    </div>
  );
};

export default React.memo(AdminContentEditorModal);

