import React, { useState } from 'react';
import authService from '../service/authService';

const JoinProjectModal = ({ isOpen, onClose, onJoin }) => {
  const [projectId, setProjectId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

const handleSubmit = async (e) => {
  e.preventDefault();
  if (loading) return;

  const cleanId = projectId.trim();

  if (!cleanId) {
    setError('Project ID is required.');
    return;
  }

  setError('');
  setLoading(true);

  try {
    const result = await authService.joinProject({
      projectId: cleanId
    });

    if (result.error) {
      setError(result.error);
      return;
    }

    await onJoin({ id: cleanId });
    setProjectId('');
  } catch (err) {
    setError('Unable to join project: ' + err.message);
  } finally {
    setLoading(false);
  }
};

  const handleClose = () => {
    setProjectId('');
    setError('');
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleClose} id="join-project-modal-overlay">
      <div className="modal-container" onClick={(e) => e.stopPropagation()} id="join-project-modal">
        <div className="modal-header">
          <h3 className="modal-title" id="modal-title-join">Join a Project</h3>
          <button className="modal-close-btn" onClick={handleClose} id="modal-close-x" aria-label="Close modal">
            &times;
          </button>
        </div>
        <form onSubmit={handleSubmit} className="modal-form" id="join-project-form">
          {error && <div className="modal-error" id="modal-error-message">{error}</div>}
          
          <div className="form-group">
            <label htmlFor="project-id">Project ID</label>
            <input
              type="text"
              id="project-id"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder="e.g. PROJ-001"
              required
              autoFocus
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={handleClose} id="modal-btn-cancel">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" id="modal-btn-submit" disabled={loading}>
              {loading ? 'Joining...' : 'Join'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default JoinProjectModal;
